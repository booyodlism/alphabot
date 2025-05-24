import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import os
from helpers.permissions import has_role  # import centralized checker

ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))
WHITELIST_ROLE_ID = int(os.getenv("WHITELIST_ROLE_ID"))
WHITELIST_CHANNEL_ID = int(os.getenv("WHITELIST_CHANNEL_ID"))

class WhitelistView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Whitelist", style=discord.ButtonStyle.success, custom_id="whitelist_button")
    async def whitelist_button(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(WHITELIST_ROLE_ID)
        if role is None:
            await interaction.response.send_message("Whitelist role not found.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("You already have the whitelist role!", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role, reason="User clicked whitelist button")
            await interaction.response.send_message("🎉 You have been given the whitelist role!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to assign this role.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ralat berlaku: {str(e)}", ephemeral=True)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_start_time = discord.utils.utcnow()

    def has_admin_role(self, interaction: discord.Interaction):
        return has_role(interaction.user, ADMIN_ROLE_ID)

    @app_commands.command(name="postwhitelist", description="Post embed Whitelist ALPHA™ with button")
    async def postwhitelist(self, interaction: discord.Interaction):
        if not self.has_admin_role(interaction):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        if interaction.channel.id != WHITELIST_CHANNEL_ID:
            await interaction.response.send_message("Please use this command in the correct whitelist channel.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Daftar Whitelist ALPHA™",
            description="Bagi memastikan anda bukan robot, anda perlu click button whitelist di bawah untuk dapat role whitelist.",
            color=discord.Color.blue()
        )
        embed.set_image(url="https://r2.fivemanage.com/4ykd8rbpiicrG4wObRR8U/whitelist.gif")
        embed.set_footer(text="Powered by ALPHA™")

        view = WhitelistView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="uptime", description="Show how long the bot has been online.")
    async def uptime(self, interaction: discord.Interaction):
        if not self.has_admin_role(interaction):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        now = discord.utils.utcnow()
        delta = now - self.bot_start_time

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title="Bot Uptime",
            description=f"🕒 I've been online for: **{uptime_str}**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
