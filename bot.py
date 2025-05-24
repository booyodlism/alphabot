import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import sys
import subprocess
import pkg_resources

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Status list untuk loop
status_list = [
    discord.Game("Alpha Roleplay"),
    discord.Activity(type=discord.ActivityType.watching, name="the server"),
    discord.Activity(type=discord.ActivityType.listening, name="music"),
]

@tasks.loop(seconds=15)
async def change_status():
    for status in status_list:
        await bot.change_presence(activity=status)
        await asyncio.sleep(15)

@bot.event
async def on_ready():
    try:
        print(f"{bot.user} is ready!")
        await bot.tree.sync()
        
        if not change_status.is_running():
            change_status.start()
        
        print("Cogs loaded:")
        for cog in bot.cogs:
            print(f"  - {cog}")

        debug_channel_id = int(os.getenv("DEBUG_CHANNEL_ID", 0))
        if debug_channel_id:
            channel = bot.get_channel(debug_channel_id)
            if channel:
                cogs_loaded = "\n".join(f"✅ `{name}`" for name in bot.cogs)
                embed = discord.Embed(
                    title="Bot Online ✅",
                    description=f"Bot `{bot.user.name}` is now online and running.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Loaded Cogs", value=cogs_loaded or "❌ No cogs loaded", inline=False)
                embed.set_footer(text="ALPHA™ System Status")
                await channel.send(embed=embed)
    except Exception as e:
        print(f"Error in on_ready event: {e}")


def get_installed_version(pkg_name):
    try:
        return pkg_resources.get_distribution(pkg_name).version
    except pkg_resources.DistributionNotFound:
        return None

def update_package(pkg_name):
    try:
        print(f"Updating {pkg_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", pkg_name])
    except Exception as e:
        print(f"Failed to update {pkg_name}: {e}")

def check_and_update_packages():
    packages = ["discord.py", "python-dotenv", "yt-dlp", "PyNaCl"]
    for pkg in packages:
        try:
            installed_ver = get_installed_version(pkg)
            if installed_ver is None:
                print(f"{pkg} not installed. Installing now...")
                update_package(pkg)
            else:
                print(f"{pkg} installed, version {installed_ver}. Checking for updates...")
                update_package(pkg)
        except Exception as e:
            print(f"Error checking/updating {pkg}: {e}")
    print("All packages checked and updated if needed.")


async def main():
    # Check and update packages before starting bot
    print("Checking and updating packages...")
    # Run in thread so main event loop not blocked, or run as sync here before asyncio.run
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, check_and_update_packages)
    
    async with bot:
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await bot.load_extension(f"cogs.{filename[:-3]}")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
