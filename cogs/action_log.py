import discord
from discord.ext import commands
import os

ACTION_LOG_CHANNEL_ID = int(os.getenv("ACTION_LOG_CHANNEL_ID"))

class ActionLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild):
        return guild.get_channel(ACTION_LOG_CHANNEL_ID)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
        channel = self.get_log_channel(before.guild)
        if channel is None:
            return

        embed = discord.Embed(
            title="📝 Message Edited",
            description=(
                f"**Author:** {before.author.mention}\n"
                f"**Channel:** {before.channel.mention}\n\n"
                f"**Before:** {before.content}\n"
                f"**After:** {after.content}"
            ),
            color=discord.Color.orange(),
            timestamp=after.created_at
        )
        embed.set_footer(text="ALPHA™ Action Log")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        channel = self.get_log_channel(message.guild)
        if channel is None:
            return

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=(
                f"**Author:** {message.author.mention}\n"
                f"**Channel:** {message.channel.mention}\n"
                f"**Content:** {message.content if message.content else '[Embed/Attachment]'}"
            ),
            color=discord.Color.red(),
            timestamp=message.created_at
        )

        images = [att.url for att in message.attachments if att.content_type and att.content_type.startswith("image")]
        if images:
            embed.add_field(name="🖼️ Images Deleted", value="\n".join(images), inline=False)

        embed.set_footer(text="ALPHA™ Action Log")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        channel = self.get_log_channel(before.guild)
        if channel is None:
            return

        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(
                title="✏️ Nickname Changed",
                description=(
                    f"**User:** {before.mention}\n"
                    f"**Before:** {before.nick or before.name}\n"
                    f"**After:** {after.nick or after.name}"
                ),
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="ALPHA™ Action Log")
            await channel.send(embed=embed)

        # Role changes
        removed_roles = set(before.roles) - set(after.roles)
        added_roles = set(after.roles) - set(before.roles)

        for role in added_roles:
            embed = discord.Embed(
                title="✅ Role Added",
                description=f"**User:** {before.mention}\n**Role:** {role.name}",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="ALPHA™ Action Log")
            await channel.send(embed=embed)

        for role in removed_roles:
            embed = discord.Embed(
                title="❎ Role Removed",
                description=f"**User:** {before.mention}\n**Role:** {role.name}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="ALPHA™ Action Log")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        channel = guild.get_channel(ACTION_LOG_CHANNEL_ID)
        if channel is None:
            return

        embed = discord.Embed(
            title="⛔ Member Banned",
            description=f"User {user} was banned.",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="ALPHA™ Action Log")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        channel = guild.get_channel(ACTION_LOG_CHANNEL_ID)
        if channel is None:
            return

        embed = discord.Embed(
            title="✅ Member Unbanned",
            description=f"User {user} was unbanned.",
            color=discord.Color.dark_green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="ALPHA™ Action Log")
        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ActionLog(bot))
