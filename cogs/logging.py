import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import time

load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = discord.Object(id=GUILD_ID)

LOG_CHANNEL_ID = 1350580759496495236
UPDATES_CHANNEL_ID = 1348025689626120232

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._recent_logs = {}

    def _is_duplicate(self, key: str, window: float = 3.0) -> bool:
        now = time.monotonic()
        if key in self._recent_logs and now - self._recent_logs[key] < window:
            return True
        self._recent_logs[key] = now
        return False

    async def log(self, guild, embed):
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

    async def update(self, guild, embed):
        channel = guild.get_channel(UPDATES_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if self._is_duplicate(f"msg_delete:{message.id}"):
            return
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red())
        embed.add_field(name="Author", value=message.author.mention)
        embed.add_field(name="Channel", value=message.channel.mention)
        if message.content:
            embed.add_field(name="Content", value=message.content, inline=False)
        if message.attachments:
            attachment_list = "\n".join(f"[{a.filename}]({a.url})" for a in message.attachments)
            embed.add_field(name="Attachments", value=attachment_list, inline=False)
            image_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp")
            for a in message.attachments:
                if a.filename.lower().endswith(image_exts):
                    embed.set_image(url=a.url)
                    break
        if not message.content and not message.attachments:
            embed.add_field(name="Content", value="[no text or attachments]", inline=False)
        embed.set_footer(text=f"User ID: {message.author.id}")
        await self.log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content or not before.guild:
            return
        if self._is_duplicate(f"msg_edit:{before.id}:{before.content}"):
            return
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange())
        embed.add_field(name="Author", value=before.author.mention)
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.add_field(name="Before", value=before.content or "[empty]", inline=False)
        embed.add_field(name="After", value=after.content or "[empty]", inline=False)
        embed.set_footer(text=f"User ID: {before.author.id}")
        await self.log(before.guild, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        if self._is_duplicate(f"join:{member.id}"):
            return
        embed = discord.Embed(title="📥 Member Joined", color=discord.Color.green())
        embed.add_field(name="User", value=f"{member.mention} ({member.name})")
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style="R"))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        await self.log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        if self._is_duplicate(f"leave:{member.id}"):
            return

        await asyncio.sleep(1)

        kicked_by = None
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    kicked_by = entry.user
                    break
        except discord.Forbidden:
            pass

        roles = [r.mention for r in member.roles if r.name != "@everyone"]

        if kicked_by:
            log_embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.name})")
            log_embed.add_field(name="Kicked By", value=kicked_by.mention)
            log_embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
            log_embed.set_footer(text=f"User ID: {member.id}")
            await self.log(member.guild, log_embed)
            await self.update(member.guild, discord.Embed(
                title="👢 Member Kicked",
                description=f"**{member.name}** was kicked by {kicked_by.mention}.",
                color=discord.Color.orange()
            ))
        else:
            log_embed = discord.Embed(title="📤 Member Left", color=discord.Color.red())
            log_embed.add_field(name="User", value=f"{member.mention} ({member.name})")
            log_embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
            log_embed.set_footer(text=f"User ID: {member.id}")
            await self.log(member.guild, log_embed)
            await self.update(member.guild, discord.Embed(
                title="👋 Member Left",
                description=f"**{member.name}** has left the server.",
                color=discord.Color.red()
            ))

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if self._is_duplicate(f"ban:{user.id}"):
            return
        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.dark_red())
        embed.add_field(name="User", value=f"{user.mention} ({user.name})")
        embed.set_footer(text=f"User ID: {user.id}")
        await self.log(guild, embed)
        await self.update(guild, discord.Embed(
            title="🔨 Member Banned",
            description=f"**{user.name}** has been banned from the server.",
            color=discord.Color.dark_red()
        ))

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        if self._is_duplicate(f"unban:{user.id}"):
            return
        embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green())
        embed.add_field(name="User", value=f"{user.mention} ({user.name})")
        embed.set_footer(text=f"User ID: {user.id}")
        await self.log(guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added or removed:
            key = f"roles:{after.id}:{','.join(str(r.id) for r in added)}:{','.join(str(r.id) for r in removed)}"
            if not self._is_duplicate(key):
                embed = discord.Embed(title="🔄 Roles Updated", color=discord.Color.blurple())
                embed.add_field(name="Member", value=after.mention)
                if added:
                    embed.add_field(name="Roles Added", value=", ".join(r.mention for r in added), inline=False)
                if removed:
                    embed.add_field(name="Roles Removed", value=", ".join(r.mention for r in removed), inline=False)
                embed.set_footer(text=f"User ID: {after.id}")
                await self.log(after.guild, embed)

        if before.nick != after.nick:
            if not self._is_duplicate(f"nick:{after.id}:{after.nick}"):
                embed = discord.Embed(title="📝 Nickname Changed", color=discord.Color.blurple())
                embed.add_field(name="Member", value=after.mention)
                embed.add_field(name="Before", value=before.nick or before.name)
                embed.add_field(name="After", value=after.nick or after.name)
                embed.set_footer(text=f"User ID: {after.id}")
                await self.log(after.guild, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        if before.channel == after.channel:
            return
        before_id = before.channel.id if before.channel else None
        after_id = after.channel.id if after.channel else None
        if self._is_duplicate(f"voice:{member.id}:{before_id}:{after_id}"):
            return
        if after.channel and not before.channel:
            embed = discord.Embed(title="🔊 Joined Voice", color=discord.Color.green())
            embed.add_field(name="Member", value=member.mention)
            embed.add_field(name="Channel", value=after.channel.name)
        elif before.channel and not after.channel:
            embed = discord.Embed(title="🔇 Left Voice", color=discord.Color.red())
            embed.add_field(name="Member", value=member.mention)
            embed.add_field(name="Channel", value=before.channel.name)
        else:
            embed = discord.Embed(title="🔀 Switched Voice", color=discord.Color.orange())
            embed.add_field(name="Member", value=member.mention)
            embed.add_field(name="From", value=before.channel.name)
            embed.add_field(name="To", value=after.channel.name)
        embed.set_footer(text=f"User ID: {member.id}")
        await self.log(member.guild, embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
