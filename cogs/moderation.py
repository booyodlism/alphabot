import sys
import os
import json
import re
import discord
from discord.ext import commands
from helpers.db_helpers import increase_and_get_warnings, create_user_table

# Tambah folder parent ke path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Path ke fail JSON
PROFANITY_PATH = os.path.join("data", "profanity.json")

# Load perkataan lucah dari fail JSON
if os.path.exists(PROFANITY_PATH):
    with open(PROFANITY_PATH, "r", encoding="utf-8") as f:
        PROFANITY = json.load(f)
else:
    print("⚠️ 'profanity.json' not found. Using default words.")
    PROFANITY = ["default", "bad", "words"]

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        create_user_table()

        # Compile regex sekali sahaja
        pattern = r"\b(" + "|".join(map(re.escape, PROFANITY)) + r")\b"
        self.profanity_regex = re.compile(pattern, re.IGNORECASE)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.author == self.bot.user:
            return

        if not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        # Check untuk perkataan lucah
        if self.profanity_regex.search(message.content):
            warnings = increase_and_get_warnings(user_id, guild_id)

            if warnings >= 3:
                try:
                    await message.author.ban(reason="Exceeded 3 warnings for profanity.")
                    embed = discord.Embed(
                        title="User Banned",
                        description=f"🚫 {message.author.mention} has been banned for repeated use of profanity.",
                        color=discord.Color.red()
                    )
                    embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
                    await message.channel.send(embed=embed)
                except Exception as e:
                    await message.channel.send(f"⚠️ Failed to ban user: {e}")
            else:
                embed = discord.Embed(
                    title="Amaran",
                    description=f"⚠️ Warning {warnings}/3 to {message.author.mention}. If you reach 3 warnings, you will be banned.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
                await message.channel.send(embed=embed)

            try:
                await message.delete()
            except:
                pass
            return

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
