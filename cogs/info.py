import discord
from discord.ext import commands
from discord import app_commands

class HelpView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.page = 0

    @discord.ui.button(label="⏪ Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next ⏩", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.embeds) - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
        else:
            await interaction.response.defer()

class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="info", description="List of commands in the ALPHA™ bot")
    async def help(self, interaction: discord.Interaction):
        embeds = []

        # Page 1
        embed1 = discord.Embed(
            title="📖 ALPHA™ Slash Command Help - Page 1",
            description="List of commands by category. Use `/command` to activate.",
            color=discord.Color.blurple()
        )
        embed1.add_field(
            name="🎧 Muzik (Whitelist Only)",
            value=(
                "`/play` - Play song\n"
                "`/pause` - Pause song\n"
                "`/resume` - Resume song\n"
                "`/skip` - Skip song\n"
                "`/stop` - Stop and disconnect\n"
                "`/queue` - Song queue\n"
                "`/nowplaying` - Current song info"
            ),
            inline=False
        )
        embeds.append(embed1)

        # Page 2
        embed2 = discord.Embed(
            title="📖 ALPHA™ Slash Command Help - Page 2",
            description="List of commands by category. Use `/command` to activate.",
            color=discord.Color.blurple()
        )
        embed2.add_field(
            name="🛠️ Admin Only",
            value=(
                "`/postwhitelist` - Post Whitelist embed\n"
                "`/uptime` - Show bot uptime\n"
                "`/embedbuilder` - Build interactive embed"
            ),
            inline=False
        )
        embeds.append(embed2)

        # Page 3
        embed3 = discord.Embed(
            title="📖 ALPHA™ Slash Command Help - Page 3",
            description="List of commands by category. Use `/command` to activate.",
            color=discord.Color.blurple()
        )
        embed3.add_field(
            name="🧾 General / Misc",
            value="`/ping` - Test bot responsiveness",
            inline=False
        )
        embed3.add_field(
            name="🛡️ Auto Mode",
            value="Automatic warning for using profanity. Ban after 3 warnings.",
            inline=False
        )
        embeds.append(embed3)

        view = HelpView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(InfoCog(bot))