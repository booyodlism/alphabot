import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import os
import io
import asyncio
import json

ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))
TICKET_UI_CHANNEL_ID = int(os.getenv("TICKET_UI_CHANNEL_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))
TICKET_CATEGORY_NAME = "TICKETS"
TICKET_LOG_CHANNEL_NAME = "ticket-logs"

DATA_FOLDER = "data"
COUNTER_FILE = os.path.join(DATA_FOLDER, "ticket_counter.json")
COUNTER_LOCK = asyncio.Lock()

async def load_counters():
    if not os.path.exists(COUNTER_FILE):
        return {}
    with open(COUNTER_FILE, "r") as f:
        return json.load(f)

async def save_counters(counters):
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    with open(COUNTER_FILE, "w") as f:
        json.dump(counters, f, indent=4)

async def get_next_ticket_number_json(ticket_type):
    async with COUNTER_LOCK:
        counters = await load_counters()
        number = counters.get(ticket_type, 0) + 1
        counters[ticket_type] = number
        await save_counters(counters)
        return number

class TicketTypeSelect(discord.ui.Select):
    def __init__(self, bot, author):
        options = [
            discord.SelectOption(label="REPORT", description="Report an issue", value="report"),
            discord.SelectOption(label="DONATION", description="Donation related", value="donation"),
            discord.SelectOption(label="SUGGESTION", description="Make a suggestion", value="suggestion"),
        ]
        super().__init__(placeholder="Select type of ticket...", min_values=1, max_values=1, options=options)
        self.bot = bot
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ This selection isn't for you.", ephemeral=True)
            return

        ticket_type = self.values[0]
        guild = interaction.guild
        author = self.author

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        number = await get_next_ticket_number_json(ticket_type)
        channel_name = f"{ticket_type}-{number}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)

        embed = discord.Embed(
            title=f"{ticket_type.capitalize()} Ticket Created",
            description=f"Hello {author.mention}! This is your {ticket_type} ticket channel. Please describe your issue here.",
            color=discord.Color.green()
        )

        view = TicketControlsView(self.bot, ticket_owner_id=author.id)

        await channel.send(embed=embed, view=view)
        self.bot.add_view(view)

        await interaction.response.send_message(f"✅ Your {ticket_type} ticket has been created: {channel.mention}", ephemeral=True)

class MentionAdminButton(Button):
    def __init__(self):
        super().__init__(label="Mention Admin", style=discord.ButtonStyle.primary, custom_id="mention_admin_button")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        if admin_role is None:
            await interaction.response.send_message("⚠️ Admin role not found.", ephemeral=True)
            return
        await interaction.response.send_message(f"{admin_role.mention} You have been mentioned for assistance.", allowed_mentions=discord.AllowedMentions(roles=True), ephemeral=False)

class CloseTicketButton(Button):
    def __init__(self, bot, ticket_owner_id):
        super().__init__(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
        self.bot = bot
        self.ticket_owner_id = ticket_owner_id

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        author = interaction.user

        if author.id != self.ticket_owner_id and ADMIN_ROLE_ID not in [role.id for role in author.roles]:
            await interaction.response.send_message("❌ You don't have permission to close this ticket.", ephemeral=True)
            return

        await interaction.response.send_message("Closing ticket and preparing transcript...", ephemeral=True)

        messages = []
        async for msg in channel.history(limit=100, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author_name = msg.author.name
            content = msg.content or ""
            attachments = ", ".join(att.url for att in msg.attachments) if msg.attachments else ""
            messages.append(f"[{timestamp}] {author_name}: {content} {attachments}")

        transcript_text = "\n".join(messages)
        transcript_file = discord.File(io.StringIO(transcript_text), filename=f"transcript-{channel.name}.txt")

        guild = interaction.guild
        log_channel = discord.utils.get(guild.text_channels, name=TICKET_LOG_CHANNEL_NAME)
        if log_channel is None:
            log_channel = await guild.create_text_channel(TICKET_LOG_CHANNEL_NAME)

        embed = discord.Embed(
            title=f"Ticket Closed: {channel.name}",
            description=f"Ticket closed by {author.mention}",
            color=discord.Color.red()
        )
        await log_channel.send(embed=embed)
        await log_channel.send(file=transcript_file)

        await asyncio.sleep(5)
        await channel.delete()

class TicketControlsView(View):
    def __init__(self, bot, ticket_owner_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_owner_id = ticket_owner_id

        self.add_item(CloseTicketButton(bot, ticket_owner_id))
        self.add_item(MentionAdminButton())

class TicketTypeSelectView(View):
    def __init__(self, bot, author):
        super().__init__(timeout=60)
        self.add_item(TicketTypeSelect(bot, author))

class TicketUI(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TicketTypeSelectView(self.bot, interaction.user)
        await interaction.response.send_message("Please select the type of ticket you want to create:", view=view, ephemeral=True)

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ui_message_id = None

    async def ensure_ticket_ui(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            print("[Ticket] Guild not found")
            return

        channel = guild.get_channel(TICKET_UI_CHANNEL_ID)
        if channel is None:
            print("[Ticket] Ticket UI channel not found")
            return

        async for message in channel.history(limit=50):
            if message.author == self.bot.user and message.components:
                self.ui_message_id = message.id
                print(f"[Ticket] Found existing ticket UI message ID {self.ui_message_id}")
                self.bot.add_view(TicketUI(self.bot))
                return

        view = TicketUI(self.bot)
        embed = discord.Embed(
            title="✉️ Support Ticket Panel",
            description=(
                "Anda wajib open ticket jika:\n\n"
                "- Memerlukan bantuan teknikal atau sokongan., \n"
                "- Menghadapi masalah dengan akaun atau akses server., \n"
                "- Perlu laporkan sebarang isu atau gangguan dalam server., \n"
                "- Bantuan untuk donation atau claim donation"
            ),
            color=discord.Color.green()
        )
        msg = await channel.send(embed=embed, view=view)
        self.ui_message_id = msg.id
        self.bot.add_view(view)
        print(f"[Ticket] Created new ticket UI message ID {self.ui_message_id}")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_ticket_ui()
        print("[Ticket] Cog ready")

    @app_commands.command(name="ticketsetup", description="Setup the ticket UI (Admin only)")
    async def ticketsetup(self, interaction: discord.Interaction):
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(TICKET_UI_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("❌ Ticket UI channel not found.", ephemeral=True)
            return

        async for message in channel.history(limit=50):
            if message.author == self.bot.user and message.components:
                await interaction.response.send_message("⚠️ Ticket UI message already exists. Delete it first to recreate.", ephemeral=True)
                return

        view = TicketUI(self.bot)
        embed = discord.Embed(
            title="✉️ Support Ticket Panel",
            description=(
                "Anda wajib open ticket jika:\n\n"
                "- Memerlukan bantuan teknikal atau sokongan., \n"
                "- Menghadapi masalah dengan akaun atau akses server., \n"
                "- Perlu laporkan sebarang isu atau gangguan dalam server., \n"
                "- Bantuan untuk donation atau claim donation"
            ),
            color=discord.Color.green()
        )
        msg = await channel.send(embed=embed, view=view)
        self.ui_message_id = msg.id
        self.bot.add_view(view)
        await interaction.response.send_message("✅ Ticket UI created!", ephemeral=True)
        print(f"[Ticket] UI message created by {interaction.user}")

async def setup(bot):
    await bot.add_cog(Ticket(bot))