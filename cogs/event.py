import discord
from discord.ext import commands
import os

WHITELIST_CHANNEL_ID = int(os.getenv("WHITELIST_CHANNEL_ID"))
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID"))
GOODBYE_CHANNEL_ID = int(os.getenv("GOODBYE_CHANNEL_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Restore persistent views (e.g., whitelist button)
        self.bot.add_view(WhitelistView())

        activity = discord.Activity(type=discord.ActivityType.watching, name="on the bot!")
        await self.bot.change_presence(activity=activity)
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))

        # Restore reaction controls and reconnect music playback
        from cogs.music import Music
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            for guild_id, current_song_data in music_cog.CURRENT_SONG.items():
                # Check current_song_data length for expected data including voice_channel_id
                if current_song_data and len(current_song_data) >= 9:
                    (
                        audio_url,
                        title,
                        video_id,
                        duration,
                        requester,
                        start_time,
                        message_id,
                        channel_id,
                        voice_channel_id,
                    ) = current_song_data

                    voice_channel = self.bot.get_channel(voice_channel_id)
                    text_channel = self.bot.get_channel(channel_id)

                    if voice_channel and text_channel:
                        voice_client = voice_channel.guild.voice_client

                        # Connect if not connected
                        if voice_client is None:
                            voice_client = await voice_channel.connect()
                        # Move if in different channel
                        elif voice_client.channel.id != voice_channel_id:
                            await voice_client.move_to(voice_channel)

                        try:
                            msg = await text_channel.fetch_message(message_id)
                            for emoji in ["⏸️", "▶️", "⏭️", "⏹️"]:
                                await msg.add_reaction(emoji)
                        except Exception as e:
                            print(f"Failed to restore reactions for guild {guild_id}: {e}")

                        # Resume playing the song
                        await music_cog.play_next_song(voice_client, guild_id, text_channel)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            return
        
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=(
                f"Terima kasih {member.mention} kerana sertai komuniti ALPHA™!\n"
                "Bersedia untuk bersama-sama menjelajah dunia roleplay penuh hiburan, perbincangan, dan peluang baru.\n"
                "Jangan malu untuk berinteraksi dan jadikan pengalaman ini lebih seronok!"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Powered by ALPHA™")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = member.guild.get_channel(GOODBYE_CHANNEL_ID)
        if channel is None:
            return
        
        embed = discord.Embed(
            title=f"Goodbye from {member.guild.name}!",
            description=(
                f"Berjumpa kita lagi di lain masa ya {member.mention}\n"
                "Maafkan kami jika kami ada kekurangan dan kesilapan.\n"
                "Kehadiran anda memberi kami seribu kemanisan,\n"
                "kepergianmu meninggalkan seribu kenangan bersama.\n"
                "Chalo betey ~"
            ),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Powered by ALPHA™")
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Events(bot))

# Import WhitelistView from admin cog for persistent button view
from cogs.admin import WhitelistView
