import discord
from discord.ext import commands
from discord import app_commands
import os
from helpers.permissions import has_role

WHITELIST_ROLE_ID = int(os.getenv("WHITELIST_ROLE_ID"))

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def whitelist_check():
        async def predicate(interaction: discord.Interaction):
            if not has_role(interaction.user, WHITELIST_ROLE_ID):
                await interaction.response.send_message("❌ You must have the whitelist role to use this command.", ephemeral=True)
                return False
            return True
        return app_commands.check(predicate)

    @whitelist_check()
    @app_commands.command(name="ping", description="Show bot processing and websocket latency.")
    async def ping(self, interaction: discord.Interaction):
        import time
        start = time.perf_counter()
        await interaction.response.defer()
        end = time.perf_counter()
        processing_latency_ms = round((end - start) * 1000, 2)
        websocket_latency_ms = round(self.bot.latency * 1000, 2)

        embed = discord.Embed(
            title="Discord Bot Ping!",
            description=(
                f"Discord Bot Processing : **{processing_latency_ms}ms**\n"
                f"Discord Websocket : **{websocket_latency_ms}ms**"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Misc(bot))
