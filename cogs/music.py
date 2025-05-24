import discord
from discord.ext import commands
from discord import app_commands
from collections import deque
import asyncio
import datetime
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError
import os

WHITELIST_ROLE_ID = int(os.getenv("WHITELIST_ROLE_ID"))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.SONG_QUEUES = {}   # guild_id -> deque of songs
        self.CURRENT_SONG = {}  # guild_id -> tuple(song info + msg ids + voice_channel_id)
        self.QUEUE_MESSAGES = {}

    def create_progress_bar(self, current, total, length=20):
        if total == 0:
            return "No duration info"
        filled_length = int(length * current // total)
        bar = "▮" * filled_length + "▯" * (length - filled_length)
        return bar

    async def search_ytdlp_async(self, query, ydl_opts):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._extract(query, ydl_opts))

    def _extract(self, query, ydl_opts):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(query, download=False)

    def check_whitelist():
        async def predicate(interaction: discord.Interaction):
            if not any(role.id == WHITELIST_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("❌ You must have the whitelist role to use this command.", ephemeral=True)
                return False
            return True
        return app_commands.check(predicate)

    @check_whitelist()
    @app_commands.command(name="play", description="Play a song or add it to the queue.")
    @app_commands.describe(song_query="Search query")
    async def play(self, interaction: discord.Interaction, song_query: str):
        await interaction.response.defer()
        voice_state = interaction.user.voice
        if voice_state is None or voice_state.channel is None:
            embed = discord.Embed(
                title="Voice Channel Required",
                description="❌ You must be in a voice channel to use this command.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.followup.send(embed=embed)
            return

        voice_channel = voice_state.channel
        voice_client = interaction.guild.voice_client
        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)

        ydl_options = {
            "format": "bestaudio[abr<=96]/bestaudio",
            "noplaylist": True,
            "youtube_include_dash_manifest": False,
            "youtube_include_hls_manifest": False,
        }

        query = "ytsearch1:" + song_query

        try:
            results = await self.search_ytdlp_async(query, ydl_options)
        except (DownloadError, ExtractorError) as e:
            embed = discord.Embed(
                title="Cannot Play Song",
                description=f"⚠️ The requested song cannot be played.\n\nDetails: {str(e)}",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.followup.send(embed=embed)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"❌ An unexpected error occurred: {str(e)}",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.followup.send(embed=embed)
            return

        tracks = results.get("entries", [])
        if not tracks:
            embed = discord.Embed(
                title="No Results",
                description="❌ No results found.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.followup.send(embed=embed)
            return

        first_track = tracks[0]
        audio_url = first_track["url"]
        title = first_track.get("title", "Untitled")
        video_id = first_track.get("id")
        duration = first_track.get("duration", 0)
        requester = interaction.user.mention

        guild_id = str(interaction.guild_id)
        if guild_id not in self.SONG_QUEUES:
            self.SONG_QUEUES[guild_id] = deque()

        self.SONG_QUEUES[guild_id].append((audio_url, title, video_id, duration, requester))

        if voice_client.is_playing() or voice_client.is_paused():
            embed = discord.Embed(
                title="Added to Queue",
                description=f"🎵 **{title}** has been added to the queue.",
                color=discord.Color.green()
            )
            if video_id:
                embed.set_thumbnail(url=f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg")
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Starting playback...")
            await self.play_next_song(voice_client, guild_id, interaction.channel)

    async def play_next_song(self, voice_client, guild_id, channel):
        if self.SONG_QUEUES.get(guild_id):
            audio_url, title, video_id, duration, requester = self.SONG_QUEUES[guild_id].popleft()

            start_time = datetime.datetime.now(datetime.timezone.utc)

            # Simpan voice_channel_id untuk reconnect nanti
            voice_channel_id = voice_client.channel.id if voice_client.channel else None

            # Simpan current song info + message ids + voice channel id
            self.CURRENT_SONG[guild_id] = (audio_url, title, video_id, duration, requester, start_time, None, channel.id, voice_channel_id)

            ffmpeg_options = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2",
                "options": "-vn -c:a libopus -b:a 96k",
            }

            source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")

            def after_play(error):
                if error:
                    print(f"Error playing {title}: {error}")
                fut = asyncio.run_coroutine_threadsafe(self.play_next_song(voice_client, guild_id, channel), self.bot.loop)
                try:
                    fut.result()
                except Exception as e:
                    print(f"Error in after_play future: {e}")

            voice_client.play(source, after=after_play)

            embed = discord.Embed(
                title="Now Playing",
                description=f"🎶 {title}",
                color=discord.Color.blue()
            )
            if video_id:
                embed.set_thumbnail(url=f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg")
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

            msg = await channel.send(embed=embed)
            # Update message id for reaction control
            self.CURRENT_SONG[guild_id] = (audio_url, title, video_id, duration, requester, start_time, msg.id, channel.id, voice_channel_id)

            for emoji in ["⏸️", "▶️", "⏭️", "⏹️"]:
                await msg.add_reaction(emoji)

            await self.update_queue_message(guild_id)
        else:
            # No songs left: cleanup
            if guild_id in self.CURRENT_SONG:
                del self.CURRENT_SONG[guild_id]
            await voice_client.disconnect()
            self.SONG_QUEUES[guild_id] = deque()

    async def update_queue_message(self, guild_id):
        queue = self.SONG_QUEUES.get(guild_id)
        if not queue:
            return

        description = ""
        for i, (_, title, _, _, _) in enumerate(queue, start=1):
            description += f"{i}. {title}\n"

        embed = discord.Embed(
            title="Current Song Queue",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

        msg = self.QUEUE_MESSAGES.get(guild_id)
        if msg:
            try:
                await msg.edit(embed=embed)
            except Exception as e:
                print(f"Failed to edit queue message for guild {guild_id}: {e}")

    @check_whitelist()
    @app_commands.command(name="skip", description="Skips the current playing song")
    async def skip(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            embed = discord.Embed(
                title="Skipped",
                description="⏭️ Skipped the current song.",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="Nothing to Skip",
                description="❌ Not playing anything to skip.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.response.send_message(embed=embed)

    @check_whitelist()
    @app_commands.command(name="pause", description="Pause the currently playing song.")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            embed = discord.Embed(
                title="Not Connected",
                description="❌ I'm not in a voice channel.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            return await interaction.response.send_message(embed=embed)

        if not voice_client.is_playing():
            embed = discord.Embed(
                title="Nothing Playing",
                description="❌ Nothing is currently playing.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            return await interaction.response.send_message(embed=embed)

        voice_client.pause()
        embed = discord.Embed(
            title="Paused",
            description="⏸️ Playback paused!",
            color=discord.Color.yellow()
        )
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
        await interaction.response.send_message(embed=embed)

    @check_whitelist()
    @app_commands.command(name="resume", description="Resume the currently paused song.")
    async def resume(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            embed = discord.Embed(
                title="Not Connected",
                description="❌ I'm not in a voice channel.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            return await interaction.response.send_message(embed=embed)

        if not voice_client.is_paused():
            embed = discord.Embed(
                title="Not Paused",
                description="❌ I'm not paused right now.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            return await interaction.response.send_message(embed=embed)

        voice_client.resume()
        embed = discord.Embed(
            title="Playback Resumed",
            description="▶️ Playback has been resumed!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

        await interaction.response.send_message(embed=embed)

    @check_whitelist()
    @app_commands.command(name="stop", description="Stop playback and clear the queue.")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()

        voice_client = interaction.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="Not Connected",
                description="❌ I'm not connected to any voice channel.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.followup.send(embed=embed)
            return

        guild_id_str = str(interaction.guild_id)
        if guild_id_str in self.SONG_QUEUES:
            self.SONG_QUEUES[guild_id_str].clear()

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        await asyncio.sleep(1)
        await voice_client.disconnect()

        embed = discord.Embed(
            title="Playback Stopped",
            description="⛔️ Stopped playback and disconnected from the voice channel.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

        await interaction.followup.send(embed=embed)

    @check_whitelist()
    @app_commands.command(name="queue", description="Show the current song queue.")
    async def queue(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        queue = self.SONG_QUEUES.get(guild_id)

        if not queue or len(queue) == 0:
            embed = discord.Embed(
                title="Queue Status",
                description="🚫 The queue is empty.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.response.send_message(embed=embed)
            return

        description = ""
        for i, (_, title, _, _, _) in enumerate(queue, start=1):
            description += f"{i}. {title}\n"

        embed = discord.Embed(
            title="Current Song Queue",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        self.QUEUE_MESSAGES[guild_id] = msg

    @check_whitelist()
    @app_commands.command(name="nowplaying", description="Show the currently playing song with details.")
    async def nowplaying(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            embed = discord.Embed(
                title="Nothing Playing",
                description="❌ Nothing is currently playing.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.response.send_message(embed=embed)
            return

        guild_id = str(interaction.guild_id)
        current = self.CURRENT_SONG.get(guild_id)

        if not current:
            embed = discord.Embed(
                title="No Song Info",
                description="❌ No song information available.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")
            await interaction.response.send_message(embed=embed)
            return

        audio_url, title, video_id, duration, requester, start_time, _, _ , _ = current

        now = datetime.datetime.now(datetime.timezone.utc)
        elapsed = (now - start_time).total_seconds()
        if elapsed > duration:
            elapsed = duration

        progress_bar = self.create_progress_bar(elapsed, duration)

        embed = discord.Embed(
            title="Now Playing",
            description=(
                f"🎶 **{title}**\n\n"
                f"Requested by: {requester}\n"
                f"Duration: `{int(elapsed)//60}:{int(elapsed)%60:02d}` / `{duration//60}:{duration%60:02d}`\n"
                f"{progress_bar}"
            ),
            color=discord.Color.blue()
        )
        if video_id:
            embed.set_thumbnail(url=f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg")
        embed.set_footer(text="Powered by ALPHA™ • Use /info for commands")

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        message = reaction.message
        guild = message.guild
        if guild is None:
            return
        voice_client = guild.voice_client
        if voice_client is None:
            return

        guild_id = str(guild.id)
        current_song_data = self.CURRENT_SONG.get(guild_id)
        if not current_song_data:
            return
        if len(current_song_data) < 9:
            return

        message_id = current_song_data[6]
        if message.id != message_id:
            return

        if not user.voice or user.voice.channel != voice_client.channel:
            return

        emoji = str(reaction.emoji)

        try:
            await message.remove_reaction(emoji, user)
        except:
            pass

        if emoji == "⏸️":
            if voice_client.is_playing():
                voice_client.pause()
                await message.channel.send(f"{user.mention} paused the music.")
        elif emoji == "▶️":
            if voice_client.is_paused():
                voice_client.resume()
                await message.channel.send(f"{user.mention} resumed the music.")
        elif emoji == "⏭️":
            voice_client.stop()
            await message.channel.send(f"{user.mention} skipped the music.")
        elif emoji == "⏹️":
            await voice_client.disconnect()
            self.SONG_QUEUES[guild_id].clear()
            await message.channel.send(f"{user.mention} stopped playback and disconnected.")

async def setup(bot):
    await bot.add_cog(Music(bot))
