import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import json
import random
import asyncio
import time
import logging

log = logging.getLogger("cogs.leveling")

load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = discord.Object(id=GUILD_ID)

DATA_FILE = "data/levels.json"

# Level up roles — add role IDs for each level milestone (optional)
# Example: {5: 123456789, 10: 987654321}
LEVEL_ROLES = {
    0: 1482937889708048396,  # Civilian
    1: 782655205752832030,   # Police Officer
    2: 782655087506882610,   # Sergeant
    3: 782654957107019826,   # Lieutenant
    4: 1348785712312352919,  # Captain
    5: 782654808195596308,   # Deputy Chief
    6: 933584296810278922,   # Deputy Inspector
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

LEVEL_THRESHOLDS = {
    1: 0,
    2: 300,
    3: 1000,
    4: 2500,
    5: 5000,
    6: 10000,
}

def xp_for_level(level):
    return LEVEL_THRESHOLDS.get(level, 10000)

def get_level(xp):
    level = 1
    for lvl, threshold in sorted(LEVEL_THRESHOLDS.items(), reverse=True):
        if xp >= threshold:
            level = lvl
            break
    return level

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs("data", exist_ok=True)
        self.bot.loop.create_task(self._inactivity_loop())

    async def _inactivity_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self._check_inactivity()
            except Exception as e:
                log.error(f"Error in inactivity check: {e}", exc_info=e)
            await asyncio.sleep(86400)  # run every 24 hours

    async def _check_inactivity(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        data = load_data()
        now = time.time()
        days_14 = 14 * 86400
        days_21 = 21 * 86400
        civilian_role = guild.get_role(LEVEL_ROLES[0])

        for user_id, stats in data.items():
            last_seen = stats.get("last_seen")
            if not last_seen:
                continue
            inactive_seconds = now - last_seen
            member = guild.get_member(int(user_id))
            if not member or member.bot:
                continue

            if inactive_seconds >= days_21:
                # Check if it's been 7 days since last demote
                last_demote = stats.get("last_demote", 0)
                if now - last_demote >= 7 * 86400:
                    # Find current level
                    current_level = None
                    for lvl, rid in sorted(LEVEL_ROLES.items(), reverse=True):
                        role = guild.get_role(rid)
                        if role and role in member.roles:
                            current_level = lvl
                            break
                    if current_level is not None and current_level > 0:
                        new_level = current_level - 1
                        old_role = guild.get_role(LEVEL_ROLES[current_level])
                        new_role = guild.get_role(LEVEL_ROLES[new_level])
                        if old_role:
                            await member.remove_roles(old_role)
                        if new_role:
                            await member.add_roles(new_role)
                        stats["level"] = new_level
                        stats["last_demote"] = now
                        rank_name = {0: "Civilian", 1: "Police Officer", 2: "Sergeant", 3: "Lieutenant", 4: "Captain", 5: "Deputy Chief", 6: "Deputy Inspector"}.get(new_level, "Unknown")
                        try:
                            await member.send(f"You've been inactive in **{guild.name}** and have been demoted to **{rank_name}**. Come back and chat to keep your rank!")
                        except discord.Forbidden:
                            pass

            elif inactive_seconds >= days_14 and not stats.get("warned_inactive"):
                # DM warning
                stats["warned_inactive"] = True
                try:
                    await member.send(f"Hey! You've been inactive for 14 days in **{guild.name}**. If you remain inactive for another 7 days, you'll be demoted to Civilian. Come say hi! 👋")
                except discord.Forbidden:
                    pass

            elif inactive_seconds < days_14:
                stats["warned_inactive"] = False

        save_data(data)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        pass  # Handled by welcome.py (Unverified role given there)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        data = load_data()
        user_id = str(message.author.id)

        if user_id not in data:
            data[user_id] = {"xp": 0, "level": 1}
            # On first message: remove Civilian, give Police Officer
            civilian_role = message.guild.get_role(LEVEL_ROLES[0])
            police_role = message.guild.get_role(LEVEL_ROLES[1])
            if civilian_role and civilian_role in message.author.roles:
                await message.author.remove_roles(civilian_role)
            if police_role and police_role not in message.author.roles:
                await message.author.add_roles(police_role)

        # Track last seen
        data[user_id]["last_seen"] = time.time()
        data[user_id].setdefault("warned_inactive", False)

        # Give 10-25 XP per message
        gained_xp = random.randint(10, 25)
        data[user_id]["xp"] += gained_xp

        old_level = data[user_id]["level"]
        new_level = get_level(data[user_id]["xp"])

        if new_level > old_level:
            data[user_id]["level"] = new_level
            save_data(data)

            # Announce level up (ephemeral-style via DM since on_message can't send ephemeral)
            embed = discord.Embed(
                title="Level Up! 🎉",
                description=f"You reached **Level {new_level}** ({['', 'Police Officer', 'Sergeant', 'Lieutenant', 'Captain', 'Deputy Chief', 'Deputy Inspector'][new_level] if new_level <= 6 else 'Max Rank'})!",
                color=discord.Color.gold()
            )
            try:
                await message.author.send(embed=embed)
            except discord.Forbidden:
                pass

            # Assign level role if configured, remove previous level roles
            if new_level in LEVEL_ROLES:
                new_role = message.guild.get_role(LEVEL_ROLES[new_level])
                old_roles = [
                    message.guild.get_role(rid)
                    for lvl, rid in LEVEL_ROLES.items()
                    if lvl != new_level
                ]
                old_roles = [r for r in old_roles if r and r in message.author.roles]
                if old_roles:
                    await message.author.remove_roles(*old_roles)
                if new_role:
                    await message.author.add_roles(new_role)
        else:
            save_data(data)

    @app_commands.command(name="rank", description="Check your rank or another member's rank")
    @app_commands.guilds(GUILD)
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        data = load_data()
        user_id = str(member.id)

        if user_id not in data:
            await interaction.response.send_message(f"{member.mention} has no XP yet.")
            return

        xp = data[user_id]["xp"]
        level = data[user_id]["level"]
        current_xp = xp - xp_for_level(level)
        needed_xp = xp_for_level(level + 1) - xp_for_level(level)

        # Rank position
        sorted_users = sorted(data.items(), key=lambda x: x[1]["xp"], reverse=True)
        rank_pos = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), "?")

        embed = discord.Embed(title=f"{member.display_name}'s Rank", color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=str(level))
        embed.add_field(name="XP", value=f"{current_xp} / {needed_xp}")
        embed.add_field(name="Total XP", value=str(xp))
        embed.add_field(name="Server Rank", value=f"#{rank_pos}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Show the top 10 members by XP")
    @app_commands.guilds(GUILD)
    async def leaderboard(self, interaction: discord.Interaction):
        data = load_data()
        if not data:
            await interaction.response.send_message("No XP data yet.")
            return

        sorted_users = sorted(data.items(), key=lambda x: x[1]["xp"], reverse=True)[:10]

        embed = discord.Embed(title="XP Leaderboard", color=discord.Color.gold())
        description = ""
        for i, (user_id, stats) in enumerate(sorted_users):
            member = interaction.guild.get_member(int(user_id))
            name = member.display_name if member else f"User {user_id}"
            description += f"**#{i+1}** {name} — Level {stats['level']} ({stats['xp']} XP)\n"

        embed.description = description
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addxp", description="Add XP to a member (admin only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def addxp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        data = load_data()
        user_id = str(member.id)
        if user_id not in data:
            data[user_id] = {"xp": 0, "level": 1}
        data[user_id]["xp"] += amount
        data[user_id]["level"] = get_level(data[user_id]["xp"])
        save_data(data)
        await interaction.response.send_message(f"Added {amount} XP to {member.mention}. They are now Level {data[user_id]['level']}.")

    @app_commands.command(name="removexp", description="Remove XP from a member (admin only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def removexp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        data = load_data()
        user_id = str(member.id)
        if user_id not in data:
            await interaction.response.send_message(f"{member.mention} has no XP.")
            return
        data[user_id]["xp"] = max(0, data[user_id]["xp"] - amount)
        data[user_id]["level"] = get_level(data[user_id]["xp"])
        save_data(data)
        await interaction.response.send_message(f"Removed {amount} XP from {member.mention}. They are now Level {data[user_id]['level']}.")

    @app_commands.command(name="initroles", description="Give Police Officer to all members without a rank (owner only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def initroles(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        civilian_role = interaction.guild.get_role(LEVEL_ROLES[0])
        if not civilian_role:
            await interaction.followup.send("Civilian role not found.", ephemeral=True)
            return

        all_rank_roles = [interaction.guild.get_role(rid) for rid in LEVEL_ROLES.values()]
        all_rank_roles = [r for r in all_rank_roles if r and r != civilian_role]
        count = 0
        for member in interaction.guild.members:
            if member.bot:
                continue
            roles_to_remove = [r for r in all_rank_roles if r in member.roles]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            if civilian_role not in member.roles:
                await member.add_roles(civilian_role)
            count += 1

        # Reset XP data
        save_data({})

        await interaction.followup.send(f"Done! Reset {count} members to Civilian.", ephemeral=True)

    @app_commands.command(name="promote", description="Promote a member to the next rank (General+ only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def promote(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this.", ephemeral=True)
            return
        all_rank_role_ids = [LEVEL_ROLES[i] for i in sorted(LEVEL_ROLES) if i >= 0]
        current_level = None
        for lvl, rid in sorted(LEVEL_ROLES.items()):
            role = interaction.guild.get_role(rid)
            if role and role in member.roles:
                current_level = lvl
        if current_level is None or current_level >= 6:
            await interaction.response.send_message(f"{member.mention} is already at max rank.", ephemeral=True)
            return
        new_level = current_level + 1
        old_role = interaction.guild.get_role(LEVEL_ROLES[current_level])
        new_role = interaction.guild.get_role(LEVEL_ROLES[new_level])
        if old_role:
            await member.remove_roles(old_role)
        if new_role:
            await member.add_roles(new_role)
        # Update XP data
        data = load_data()
        user_id = str(member.id)
        if user_id not in data:
            data[user_id] = {"xp": 0, "level": new_level}
        data[user_id]["level"] = new_level
        data[user_id]["xp"] = max(data[user_id].get("xp", 0), LEVEL_THRESHOLDS.get(new_level, 0))
        save_data(data)
        await interaction.response.send_message(f"Promoted {member.mention} to **{new_role.name}**. ⬆️")

    @app_commands.command(name="demote", description="Demote a member to the previous rank (owner only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def demote(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this.", ephemeral=True)
            return
        current_level = None
        for lvl, rid in sorted(LEVEL_ROLES.items()):
            role = interaction.guild.get_role(rid)
            if role and role in member.roles:
                current_level = lvl
        if current_level is None or current_level <= 0:
            await interaction.response.send_message(f"{member.mention} is already at the lowest rank.", ephemeral=True)
            return
        new_level = current_level - 1
        old_role = interaction.guild.get_role(LEVEL_ROLES[current_level])
        new_role = interaction.guild.get_role(LEVEL_ROLES[new_level])
        if old_role:
            await member.remove_roles(old_role)
        if new_role:
            await member.add_roles(new_role)
        # Update XP data
        data = load_data()
        user_id = str(member.id)
        if user_id not in data:
            data[user_id] = {"xp": 0, "level": new_level}
        data[user_id]["level"] = new_level
        data[user_id]["xp"] = LEVEL_THRESHOLDS.get(new_level, 0)
        save_data(data)
        await interaction.response.send_message(f"Demoted {member.mention} to **{new_role.name}**. ⬇️")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Boost reward — 500 XP when someone starts boosting
        if not before.premium_since and after.premium_since:
            data = load_data()
            user_id = str(after.id)
            if user_id not in data:
                data[user_id] = {"xp": 0, "level": 1}
            data[user_id]["xp"] += 500
            new_level = get_level(data[user_id]["xp"])
            old_level = data[user_id]["level"]
            if new_level > old_level:
                data[user_id]["level"] = new_level
                new_role = after.guild.get_role(LEVEL_ROLES.get(new_level))
                old_roles = [after.guild.get_role(rid) for lvl, rid in LEVEL_ROLES.items() if lvl != new_level]
                old_roles = [r for r in old_roles if r and r in after.roles]
                if old_roles:
                    await after.remove_roles(*old_roles)
                if new_role:
                    await after.add_roles(new_role)
            save_data(data)
            try:
                embed = discord.Embed(
                    title="💎 Boost Reward!",
                    description=f"Thanks for boosting! You've been given **500 bonus XP**. 🚀",
                    color=discord.Color.purple()
                )
                await after.send(embed=embed)
            except discord.Forbidden:
                pass

async def setup(bot):
    await bot.add_cog(Leveling(bot))
