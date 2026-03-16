import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import json
import asyncio
import time

load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = discord.Object(id=GUILD_ID)
PRISONER_ROLE_ID = 822114879292964895

LEVEL_ROLES = {
    0: 1482937889708048396,  # Civilian
    1: 782655205752832030,   # Police Officer
    2: 782655087506882610,   # Sergeant
    3: 782654957107019826,   # Lieutenant
    4: 1348785712312352919,  # Captain
    5: 782654808195596308,   # Deputy Chief
    6: 933584296810278922,   # Deputy Inspector
}

ARREST_FILE = "data/arrests.json"
UPDATES_CHANNEL_ID = 1348025689626120232
WARNS_FILE = "data/warns.json"

# Roles allowed to arrest (Captain and above)
CAPTAIN_PLUS = {
    1348785712312352919,  # Captain
    782654808195596308,   # Deputy Chief
    933584296810278922,   # Deputy Inspector
}

# Escalating mute durations (in minutes) starting at 3rd warn
WARN_MUTE_DURATIONS = {3: 1, 4: 3, 5: 5, 6: 10, 7: 30, 8: 60}

def load_warns():
    if not os.path.exists(WARNS_FILE):
        return {}
    with open(WARNS_FILE, "r") as f:
        return json.load(f)

def save_warns(data):
    os.makedirs("data", exist_ok=True)
    with open(WARNS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_arrests():
    if not os.path.exists(ARREST_FILE):
        return {}
    with open(ARREST_FILE, "r") as f:
        return json.load(f)

def save_arrests(data):
    os.makedirs("data", exist_ok=True)
    with open(ARREST_FILE, "w") as f:
        json.dump(data, f, indent=2)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self._resume_pending_releases())

    async def _resume_pending_releases(self):
        await self.bot.wait_until_ready()
        arrests = load_arrests()
        for user_id, data in list(arrests.items()):
            if isinstance(data, dict) and data.get("release_at"):
                delay = data["release_at"] - time.time()
                guild = self.bot.get_guild(GUILD_ID)
                if guild:
                    member = guild.get_member(int(user_id))
                    if member:
                        asyncio.create_task(self._auto_release(guild, member, delay_seconds=max(delay, 0)))

    async def post_update(self, guild, embed):
        channel = guild.get_channel(UPDATES_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.send_message("Done.", ephemeral=True)
        await member.kick(reason=reason)
        embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})")
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await self.post_update(interaction.guild, embed)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.send_message("Done.", ephemeral=True)
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.dark_red())
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})")
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await self.post_update(interaction.guild, embed)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        user = await self.bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message("Done.", ephemeral=True)
        embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green())
        embed.add_field(name="User", value=str(user))
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await self.post_update(interaction.guild, embed)

    @app_commands.command(name="mute", description="Timeout a member (in minutes)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        from datetime import timedelta
        await interaction.response.send_message("Done.", ephemeral=True)
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.red())
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Duration", value=f"{minutes} minute(s)")
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await self.post_update(interaction.guild, embed)

    @app_commands.command(name="unmute", description="Remove timeout from a member")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message("Done.", ephemeral=True)
        embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention)
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await self.post_update(interaction.guild, embed)

    @app_commands.command(name="purge", description="Delete messages in bulk")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await interaction.response.send_message("Done.", ephemeral=True)
        warns = load_warns()
        user_id = str(member.id)
        if user_id not in warns:
            warns[user_id] = 0
        warns[user_id] += 1
        warn_count = warns[user_id]
        save_warns(warns)

        # Escalating mute
        mute_duration = WARN_MUTE_DURATIONS.get(warn_count)
        if mute_duration:
            from datetime import timedelta
            await member.timeout(timedelta(minutes=mute_duration), reason=f"Warn #{warn_count}: {reason}")

        try:
            dm = f"You have been warned in **{interaction.guild.name}**.\n**Reason:** {reason}\n**Total Warns:** {warn_count}"
            if mute_duration:
                dm += f"\n**Auto-muted for:** {mute_duration} minute(s)"
            await member.send(dm)
        except discord.Forbidden:
            pass

        embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.yellow())
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Total Warns", value=str(warn_count))
        if mute_duration:
            embed.add_field(name="Auto-muted", value=f"{mute_duration} minute(s)")
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await self.post_update(interaction.guild, embed)

    @app_commands.command(name="clearwarns", description="Clear all warns for a member")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        warns = load_warns()
        warns.pop(str(member.id), None)
        save_warns(warns)
        await interaction.response.send_message(f"Cleared all warns for {member.mention}.", ephemeral=True)

    @app_commands.command(name="warns", description="Check how many warns a member has")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(manage_messages=True)
    async def checkwarns(self, interaction: discord.Interaction, member: discord.Member):
        warns = load_warns()
        count = warns.get(str(member.id), 0)
        await interaction.response.send_message(f"{member.mention} has **{count}** warn(s).", ephemeral=True)

    async def _auto_release(self, guild: discord.Guild, member: discord.Member, delay_seconds: float = 0):
        await asyncio.sleep(delay_seconds)
        prisoner_role = guild.get_role(PRISONER_ROLE_ID)

        # Try cache first, then fetch
        member_id = member.id
        member = guild.get_member(member_id)
        if not member:
            try:
                member = await guild.fetch_member(member_id)
            except discord.NotFound:
                return

        if not prisoner_role or prisoner_role not in member.roles:
            return

        await member.remove_roles(prisoner_role)
        arrests = load_arrests()
        data = arrests.pop(str(member.id), None)
        save_arrests(arrests)

        saved_role_id = data.get("role_id") if isinstance(data, dict) else data
        restore_id = saved_role_id if saved_role_id else LEVEL_ROLES[1]
        rank_role = guild.get_role(restore_id)
        if rank_role:
            await member.add_roles(rank_role)

        # Post release announcement
        channel = guild.get_channel(UPDATES_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="Released",
                description=f"{member.mention} has been released from prison. Their sentence is up. 🔓",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)

        try:
            await member.send(f"You have been automatically released from prison in **{guild.name}**.")
        except discord.Forbidden:
            pass

    @app_commands.command(name="arrest", description="Arrest a member and remove their rank")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(manage_roles=True)
    async def arrest(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", duration: int = 0):
        is_owner = interaction.user.id == interaction.guild.owner_id
        has_rank = any(r.id in CAPTAIN_PLUS for r in interaction.user.roles)
        if not is_owner and not has_rank:
            await interaction.response.send_message("Only Captains and above can arrest members.", ephemeral=True)
            return
        prisoner_role = interaction.guild.get_role(PRISONER_ROLE_ID)
        if not prisoner_role:
            await interaction.response.send_message("Prisoner role not found.", ephemeral=True)
            return

        if prisoner_role in member.roles:
            await interaction.response.send_message(f"{member.mention} is already a prisoner.", ephemeral=True)
            return

        # Find and save their highest rank role
        arrests = load_arrests()
        saved_role_id = None
        for lvl, rid in sorted(LEVEL_ROLES.items(), reverse=True):
            role = interaction.guild.get_role(rid)
            if role and role in member.roles:
                saved_role_id = rid
                await member.remove_roles(role)
                break

        arrests[str(member.id)] = {
            "role_id": saved_role_id,
            "release_at": (time.time() + duration * 60) if duration > 0 else None
        }
        save_arrests(arrests)

        await member.add_roles(prisoner_role)

        duration_text = f"{duration} minute(s)" if duration > 0 else "Permanent"
        embed = discord.Embed(
            title="🔒 Locked Up",
            description=f"{member.mention} has been locked up. 🚔\n**Reason:** {reason}\n**Duration:** {duration_text}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Arrested by {interaction.user.display_name}")
        await interaction.response.send_message("Done.", ephemeral=True)
        updates_channel = interaction.guild.get_channel(UPDATES_CHANNEL_ID)
        if not updates_channel:
            updates_channel = await interaction.guild.fetch_channel(UPDATES_CHANNEL_ID)
        if updates_channel:
            await updates_channel.send(embed=embed)

        try:
            await member.send(f"You have been arrested in **{interaction.guild.name}**.\n**Reason:** {reason}\n**Duration:** {duration_text}")
        except discord.Forbidden:
            pass

        if duration > 0:
            asyncio.create_task(self._auto_release(interaction.guild, member, delay_seconds=duration * 60))

    @app_commands.command(name="release", description="Release a prisoner and restore their rank")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(manage_roles=True)
    async def release(self, interaction: discord.Interaction, member: discord.Member):
        prisoner_role = interaction.guild.get_role(PRISONER_ROLE_ID)
        if not prisoner_role:
            await interaction.response.send_message("Prisoner role not found.", ephemeral=True)
            return

        if prisoner_role not in member.roles:
            await interaction.response.send_message(f"{member.mention} is not a prisoner.", ephemeral=True)
            return

        await member.remove_roles(prisoner_role)

        # Restore their rank role
        arrests = load_arrests()
        data = arrests.pop(str(member.id), None)
        save_arrests(arrests)

        saved_role_id = data.get("role_id") if isinstance(data, dict) else data
        restore_id = saved_role_id if saved_role_id else LEVEL_ROLES[1]
        rank_role = interaction.guild.get_role(restore_id)
        if rank_role:
            await member.add_roles(rank_role)

        embed = discord.Embed(
            title="🔓 Released",
            description=f"{member.mention} has been released from prison.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Released by {interaction.user.display_name}")
        await interaction.response.send_message(f"Released {member.mention}.", ephemeral=True)
        await self.post_update(interaction.guild, embed)

        try:
            await member.send(f"You have been released from prison in **{interaction.guild.name}**.")
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(Moderation(bot))
