import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import datetime
import json

load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = discord.Object(id=GUILD_ID)
ANNOUNCEMENTS_CHANNEL_ID = 933580388234829845
BOOSTS_CHANNEL_ID = 1348111587466281044
RANKING_ANNOUNCEMENT_FLAG = "data/ranking_announced.flag"

RANKING_ANNOUNCEMENT = """📢 **New Ranking System is Live!**

All ranks have been reset. Everyone starts as a **Civilian**.

**How to rank up:** Just chat! Every message earns you XP.

📊 **Rank Milestones:**
🪖 **Police Officer** — First message
⬆️ **Sergeant** — 300 XP
⬆️ **Lieutenant** — 1,000 XP
⬆️ **Captain** — 2,500 XP
⬆️ **Deputy Chief** — 5,000 XP
⬆️ **Deputy Inspector** — 10,000 XP

Use `/rank` to check your XP and rank at any time.
Good luck out there. 🚔"""

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self._post_ranking_announcement())

    async def _post_ranking_announcement(self):
        await self.bot.wait_until_ready()
        if os.path.exists(RANKING_ANNOUNCEMENT_FLAG):
            return
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        channel = guild.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(description=RANKING_ANNOUNCEMENT, color=discord.Color.gold())
            embed.set_footer(text="Four$tar — Commissioner")
            await channel.send(content="@everyone", embed=embed)
            os.makedirs("data", exist_ok=True)
            open(RANKING_ANNOUNCEMENT_FLAG, "w").close()

    @app_commands.command(name="whois", description="Full profile of a member")
    @app_commands.guilds(GUILD)
    async def whois(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        # Load XP data
        levels_data = {}
        if os.path.exists("data/levels.json"):
            with open("data/levels.json") as f:
                levels_data = json.load(f)

        # Load warns
        warns_data = {}
        if os.path.exists("data/warns.json"):
            with open("data/warns.json") as f:
                warns_data = json.load(f)

        # Load arrests
        arrests_data = {}
        if os.path.exists("data/arrests.json"):
            with open("data/arrests.json") as f:
                arrests_data = json.load(f)

        user_id = str(member.id)
        stats = levels_data.get(user_id, {})
        xp = stats.get("xp", 0)
        level = stats.get("level", 0)
        warns = warns_data.get(user_id, 0)
        is_arrested = user_id in arrests_data

        rank_names = {0: "Civilian", 1: "Police Officer", 2: "Sergeant", 3: "Lieutenant", 4: "Captain", 5: "Deputy Chief", 6: "Deputy Inspector"}
        rank_name = rank_names.get(level, "Unknown")

        embed = discord.Embed(title=f"🔍 {member.display_name}", color=member.color or discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Rank", value=rank_name)
        embed.add_field(name="Level", value=str(level))
        embed.add_field(name="XP", value=str(xp))
        embed.add_field(name="Warns", value=str(warns))
        embed.add_field(name="In Prison", value="Yes 🔒" if is_arrested else "No")
        embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "Unknown")
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style="R"))
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        embed.add_field(name="Roles", value=", ".join(roles[:5]) + ("..." if len(roles) > 5 else "") or "None", inline=False)
        embed.set_footer(text=f"ID: {member.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Get info about a user")
    @app_commands.guilds(GUILD)
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(title=str(member), color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"))
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"))
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed.add_field(name="Roles", value=", ".join(roles) or "None", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Get info about the server")
    @app_commands.guilds(GUILD)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown")
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Channels", value=len(guild.channels))
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Post a yes/no poll to announcements")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def poll(self, interaction: discord.Interaction, question: str):
        channel = interaction.guild.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("Announcements channel not found.", ephemeral=True)
            return
        embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blurple())
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")
        await interaction.response.send_message("Poll posted!", ephemeral=True)
        msg = await channel.send(content="@everyone", embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

    @app_commands.command(name="announce", description="Send an announcement to a channel")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        embed = discord.Embed(description=message, color=discord.Color.gold())
        embed.set_footer(text=f"Announcement by {interaction.user.display_name}")
        everyone = "@everyone" if channel.id == ANNOUNCEMENTS_CHANNEL_ID else ""
        await channel.send(content=everyone if everyone else None, embed=embed)
        await interaction.response.send_message(f"Announcement sent to {channel.mention}", ephemeral=True)

    @app_commands.command(name="stats", description="Show server stats")
    @app_commands.guilds(GUILD)
    async def stats(self, interaction: discord.Interaction):
        guild = interaction.guild
        bots = sum(1 for m in guild.members if m.bot)
        humans = guild.member_count - bots
        online = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
        embed = discord.Embed(title=f"📊 {guild.name} Stats", color=discord.Color.blurple())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Total Members", value=str(guild.member_count))
        embed.add_field(name="Humans", value=str(humans))
        embed.add_field(name="Bots", value=str(bots))
        embed.add_field(name="Online", value=str(online))
        embed.add_field(name="Channels", value=str(len(guild.channels)))
        embed.add_field(name="Roles", value=str(len(guild.roles)))
        embed.add_field(name="Server Created", value=discord.utils.format_dt(guild.created_at, style="R"))
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="Check bot latency")
    @app_commands.guilds(GUILD)
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! `{round(self.bot.latency * 1000)}ms`")

    @app_commands.command(name="addrole", description="Add a role to a member")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(manage_roles=True)
    async def addrole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await member.add_roles(role)
        await interaction.response.send_message(f"Added {role.mention} to {member.mention}")

    @app_commands.command(name="removerole", description="Remove a role from a member")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(manage_roles=True)
    async def removerole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await member.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.mention} from {member.mention}")

async def setup(bot):
    await bot.add_cog(Utilities(bot))
