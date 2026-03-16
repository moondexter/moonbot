import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import random
import json

load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = discord.Object(id=GUILD_ID)

WELCOME_CHANNEL_ID = 1348065395717701642
RULES_CHANNEL_ID = 933579713757204570
ROLES_CHANNEL_ID = 1482948738929524888
HANDBOOK_CHANNEL_ID = 1482975031993696426
CIVILIAN_ROLE_ID = 1482937889708048396
UNVERIFIED_ROLE_ID = 1482974856411877506
LANDING_CATEGORY_ID = 1348042236449001603

# Categories to lock (Civilian+ only)
LOCKED_CATEGORY_IDS = [
    1348188638982438963,  # Server
    782651230073389137,   # Community
    782651230513528832,   # Voice
    1348036631843704932,  # Private VC
    933585134727340093,   # Gaming
]

VERIFY_CATEGORY_ID = 1482979319822155856  # Visible to all, unverified read-only

CONFIG_FILE = "data/config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

class AgreementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ I Agree to the Rules", style=discord.ButtonStyle.green, custom_id="agree_rules")
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        civilian_role = interaction.guild.get_role(CIVILIAN_ROLE_ID)
        unverified_role = interaction.guild.get_role(UNVERIFIED_ROLE_ID)

        if civilian_role and civilian_role in interaction.user.roles:
            await interaction.response.send_message("You've already agreed to the rules!", ephemeral=True)
            return

        if unverified_role and unverified_role in interaction.user.roles:
            await interaction.user.remove_roles(unverified_role)
        if civilian_role:
            await interaction.user.add_roles(civilian_role)

        await interaction.response.send_message("Welcome to Four$tar! You now have access to the server. 🚔", ephemeral=True)

WELCOME_MESSAGES = [
    "{} just pulled up. 🚨",
    "{} has entered the precinct.",
    "{} started existing in Four$tar.",
    "{} just clocked in. Welcome to the force. 🫡",
    "{} has arrived. Stand at attention.",
    "{} just walked through the gates.",
    "{} is now on the radar. 👀",
    "{} just spawned into existence.",
    "{} has reported for duty.",
    "{} just touched down. Welcome. ✈️",
    "{} has joined the ranks.",
    "{} just appeared out of nowhere. 👁️",
    "{} is in the building. 🏢",
    "{} just broke into the server. Arrest them. 🚔",
    "{} has been detected in the area.",
    "{} just loaded in. Lag or not, you're here now.",
    "{} pulled up uninvited but we'll allow it.",
    "{} just made their entrance. 🎭",
    "{} was airdropped into Four$tar.",
    "{} is now a real person. Welcome to the world. 🌍",
]

HANDBOOK_MESSAGE = """📖 𝙁𝙤𝙪𝙧$𝙩𝙖𝙧 𝙃𝙖𝙣𝙙𝙗𝙤𝙤𝙠
📜 A reminder of the rules you agreed to. These apply at all times. Breaking them may result in a warning, mute, kick, or ban.

⚠️ Warn / Mute

Spamming (Sending the same message repeatedly)
Flooding (7+ messages in a row with no context)
Inappropriate Username/Profile Picture
Ghost Pinging (Pinging someone and deleting it)
Playing Loud Audio (In voice channels)
Self-Promotion (Advertising other servers/games)
Off-Topic Messages (Not relevant to the channel)
Excessive Tagging (Tagging staff/members repeatedly)

🔇 Mute / Kick

Harassment (Bullying or targeting others)
Toxicity (Being disrespectful or hostile)
Mass Pinging (Tagging people excessively)
Starting Drama (Causing unnecessary conflict)
Being Annoying (Disrupting the server)
Suggestive Topics (Sexual or inappropriate talk)
Impersonation (Pretending to be someone else)

🚫 Kick / Temp Ban

Racism / Hate Speech
Terrorism Discussions
Animal Abuse Topics
Shocking / Disturbing Media

⛔ Permanent Ban

NSFW Content (Sexual or gore material)
Scamming (Attempting to scam members)
Doxxing (Sharing private info)
Raiding (Organizing a server attack)
Framing Users (Falsely accusing someone)
Child Endangerment (Sexualizing minors)
Malicious Links (IP grabbers, viruses, etc.)
Pornographic Links

🚨 Breaking these rules will result in immediate action. Respect the server and its members!"""

RULES_MESSAGE = """𝙒𝙚𝙡𝙘𝙤𝙢𝙚 𝙩𝙤 𝙁𝙤𝙪𝙧$𝙩𝙖𝙧 ❗
📜 Before typing in the server, make sure to read and follow these rules. Breaking them may result in a warning, mute, kick, or ban.

⚠️ Warn / Mute

Spamming (Sending the same message repeatedly)
Flooding (7+ messages in a row with no context)
Inappropriate Username/Profile Picture
Ghost Pinging (Pinging someone and deleting it)
Playing Loud Audio (In voice channels)
Self-Promotion (Advertising other servers/games)
Off-Topic Messages (Not relevant to the channel)
Excessive Tagging (Tagging staff/members repeatedly)

🔇 Mute / Kick

Harassment (Bullying or targeting others)
Toxicity (Being disrespectful or hostile)
Mass Pinging (Tagging people excessively)
Starting Drama (Causing unnecessary conflict)
Being Annoying (Disrupting the server)
Suggestive Topics (Sexual or inappropriate talk)
Impersonation (Pretending to be someone else)

🚫 Kick / Temp Ban

Racism / Hate Speech
Terrorism Discussions
Animal Abuse Topics
Shocking / Disturbing Media

⛔ Permanent Ban

NSFW Content (Sexual or gore material)
Scamming (Attempting to scam members)
Doxxing (Sharing private info)
Raiding (Organizing a server attack)
Framing Users (Falsely accusing someone)
Child Endangerment (Sexualizing minors)
Malicious Links (IP grabbers, viruses, etc.)
Pornographic Links

🚨 Breaking these rules will result in immediate action. Respect the server and its members!"""

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        # Give Unverified role
        unverified_role = member.guild.get_role(UNVERIFIED_ROLE_ID)
        if unverified_role:
            await member.add_roles(unverified_role)
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            msg = random.choice(WELCOME_MESSAGES).format(member.mention)
            embed = discord.Embed(
                description=msg,
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{member.guild.member_count} • Read <#{RULES_CHANNEL_ID}>")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass

    @app_commands.command(name="setupverification", description="Set up the verification system (owner only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def setupverification(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        unverified_role = interaction.guild.get_role(UNVERIFIED_ROLE_ID)
        civilian_role = interaction.guild.get_role(CIVILIAN_ROLE_ID)
        sergeant_role = interaction.guild.get_role(782655087506882610)  # Sergeant
        everyone = interaction.guild.default_role

        # Locked to Civilian+ (Server, Community, Voice, Gaming)
        civilian_overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=False),
            unverified_role: discord.PermissionOverwrite(view_channel=False),
        }
        if civilian_role:
            civilian_overwrites[civilian_role] = discord.PermissionOverwrite(view_channel=True)

        # Locked to Sergeant+ (Private VC)
        sergeant_overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=False),
            unverified_role: discord.PermissionOverwrite(view_channel=False),
        }
        if civilian_role:
            sergeant_overwrites[civilian_role] = discord.PermissionOverwrite(view_channel=False)
        if sergeant_role:
            sergeant_overwrites[sergeant_role] = discord.PermissionOverwrite(view_channel=True)

        SERGEANT_ONLY_CATEGORIES = [1348036631843704932]  # Private VC
        CIVILIAN_CATEGORIES = [c for c in LOCKED_CATEGORY_IDS if c not in SERGEANT_ONLY_CATEGORIES]

        for category_id in CIVILIAN_CATEGORIES:
            category = interaction.guild.get_channel(category_id)
            if category:
                await category.edit(overwrites=civilian_overwrites)

        for category_id in SERGEANT_ONLY_CATEGORIES:
            category = interaction.guild.get_channel(category_id)
            if category:
                await category.edit(overwrites=sergeant_overwrites)

        # Landing — fully visible to everyone including unverified, no sending
        landing = interaction.guild.get_channel(LANDING_CATEGORY_ID)
        if landing:
            await landing.edit(overwrites={
                everyone: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            })
            # Sync all channels in Landing to category
            import asyncio
            for ch in landing.channels:
                try:
                    await ch.edit(sync_permissions=True)
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

        # Verify category — visible to everyone, unverified can read but not send
        verify_category = interaction.guild.get_channel(VERIFY_CATEGORY_ID)
        if verify_category:
            verify_overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            }
            if civilian_role:
                verify_overwrites[civilian_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
            if unverified_role:
                verify_overwrites[unverified_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
            await verify_category.edit(overwrites=verify_overwrites)
            for ch in verify_category.channels:
                try:
                    await ch.edit(sync_permissions=True)
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

        # Post rules + agreement button to verification channel
        verify_channel = interaction.guild.get_channel(HANDBOOK_CHANNEL_ID)
        if verify_channel:
            await verify_channel.purge(limit=100)
            embed = discord.Embed(
                title="📋 Agree to the Rules",
                description="Click the button below to agree to the rules and gain full access to the server.",
                color=discord.Color.green()
            )
            await verify_channel.send(embed=embed, view=AgreementView())

        await interaction.followup.send("✅ Done! Syncing channel permissions in the background...", ephemeral=True)

        # Sync all channels in background
        import asyncio
        async def sync_channels():
            all_category_ids = LOCKED_CATEGORY_IDS
            for category_id in all_category_ids:
                category = interaction.guild.get_channel(category_id)
                if not category:
                    continue
                for channel in category.channels:
                    try:
                        await channel.edit(sync_permissions=True)
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass

        asyncio.create_task(sync_channels())

    @app_commands.command(name="fixlanding", description="Force Landing and Verify channels visible to everyone (owner only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def fixlanding(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        everyone = interaction.guild.default_role
        unverified_role = interaction.guild.get_role(UNVERIFIED_ROLE_ID)
        civilian_role = interaction.guild.get_role(CIVILIAN_ROLE_ID)

        open_overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=True, send_messages=False),
        }

        # Force each Landing channel visible directly
        landing_channel_ids = [WELCOME_CHANNEL_ID, RULES_CHANNEL_ID, ROLES_CHANNEL_ID]
        for ch_id in landing_channel_ids:
            ch = interaction.guild.get_channel(ch_id)
            if ch:
                await ch.edit(overwrites=open_overwrites)

        # Force each Verify channel visible directly
        verify_category = interaction.guild.get_channel(VERIFY_CATEGORY_ID)
        if verify_category:
            for ch in verify_category.channels:
                await ch.edit(overwrites=open_overwrites)

        await interaction.followup.send("✅ Landing and Verify channels are now visible to everyone.", ephemeral=True)

    @app_commands.command(name="testwelcome", description="Test the welcome message for yourself")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def testwelcome(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("Welcome channel not found.", ephemeral=True)
            return
        member = interaction.user
        msg = random.choice(WELCOME_MESSAGES).format(member.mention)
        embed = discord.Embed(description=msg, color=discord.Color.gold())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{interaction.guild.member_count} • Read <#{RULES_CHANNEL_ID}>")
        await channel.send(embed=embed)
        await interaction.response.send_message("Done.", ephemeral=True)

    @app_commands.command(name="sendroles", description="Post the roles info to the roles channel (owner only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def sendroles(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(ROLES_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("Roles channel not found.", ephemeral=True)
            return
        embed = discord.Embed(title="🏅 Server Ranks", color=discord.Color.gold())
        embed.description = (
            "Ranks are earned by chatting. Every message gives you XP.\n\n"
            "👤 **Civilian** — Default rank. Just joined or inactive.\n"
            "🪖 **Police Officer** — Send your first message.\n"
            "⭐ **Sergeant** — 300 XP\n"
            "⭐⭐ **Lieutenant** — 1,000 XP\n"
            "⭐⭐⭐ **Captain** — 2,500 XP\n"
            "💎 **Deputy Chief** — 5,000 XP\n"
            "👑 **Deputy Inspector** — 10,000 XP\n\n"
            "🔱 **General** — Manually given by the owner.\n"
            "🤖 **Commissioner** — The bot. Top of the chain.\n\n"
            "Use `/rank` to check your XP and `/leaderboard` to see the top members."
        )
        await channel.send(embed=embed)
        await interaction.response.send_message(f"Roles posted to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="sendrules", description="Post the rules message to the handbook channel (owner only)")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def sendrules(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(RULES_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("Handbook channel not found.", ephemeral=True)
            return
        await channel.send(HANDBOOK_MESSAGE)
        await interaction.response.send_message(f"Rules posted to {channel.mention}.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
