import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
from collections import defaultdict
import time

load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD = discord.Object(id=GUILD_ID)

# Customize your bad words list
BAD_WORDS = ["badword1", "badword2"]  # Add your words here

# Spam detection: max messages per window
SPAM_LIMIT = 5
SPAM_WINDOW = 5  # seconds

message_timestamps = defaultdict(list)

BOT_ROLE_ID = 823935026214731836
GENERAL_CHANNEL_ID = 782651230073389138
EXTRA_CHANNEL_ID = 782651230073389140

# Read-only channels — no one should be able to send messages here
READ_ONLY_CHANNELS = {
    933579713757204570,   # handbook
    1482948738929524888,  # roles
    1482975031993696426,  # verification
    1348065395717701642,  # welcome
}
MEDIA_CHANNEL_ID = 1348113613717766174
MUSIC_CHANNEL_ID = 782651230073389139

MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
MUSIC_PREFIXES = ("!", "m!", "/", "?", "-", ">>", "+")

URL_REGEX = re.compile(r"https?://\S+|discord\.gg/\S+|www\.\S+", re.IGNORECASE)

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Delete messages in read-only channels
        if message.channel.id in READ_ONLY_CHANNELS:
            await message.delete()
            return

        # Music channel — only bot commands allowed
        if message.channel.id == MUSIC_CHANNEL_ID:
            if not message.content.startswith(MUSIC_PREFIXES):
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Only music bot commands here. 🎵",
                    delete_after=5
                )
                return

        # Media channel — only photos and videos allowed
        if message.channel.id == MEDIA_CHANNEL_ID:
            has_media = any(
                any(a.filename.lower().endswith(ext) for ext in MEDIA_EXTENSIONS)
                for a in message.attachments
            )
            if not has_media:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Only photos and videos allowed here. 📸",
                    delete_after=5
                )
                return

        # Block links in general channel
        if message.channel.id == GENERAL_CHANNEL_ID and URL_REGEX.search(message.content):
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} No links in general. Send it in <#{EXTRA_CHANNEL_ID}>! 🔗",
                delete_after=6
            )
            return

        # Bad word filter
        content_lower = message.content.lower()
        if any(word in content_lower for word in BAD_WORDS):
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} Watch your language!", delete_after=5
            )
            return

        # Spam detection
        user_id = message.author.id
        now = time.time()
        message_timestamps[user_id] = [
            t for t in message_timestamps[user_id] if now - t < SPAM_WINDOW
        ]
        message_timestamps[user_id].append(now)

        if len(message_timestamps[user_id]) >= SPAM_LIMIT:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} Stop spamming!", delete_after=5
            )
            from datetime import timedelta
            await message.author.timeout(timedelta(minutes=1), reason="Spam detected")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        bot_role = after.guild.get_role(BOT_ROLE_ID)
        if not bot_role:
            return
        if bot_role not in before.roles and bot_role in after.roles and not after.bot:
            await after.remove_roles(bot_role, reason="BOT role is restricted to bots only")
            try:
                await after.send(f"The **BOT** role in **{after.guild.name}** is restricted to bots only and has been removed from you.")
            except discord.Forbidden:
                pass

    @app_commands.command(name="addbadword", description="Add a word to the filter")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def addbadword(self, interaction: discord.Interaction, word: str):
        BAD_WORDS.append(word.lower())
        await interaction.response.send_message(f"Added `{word}` to the filter.", ephemeral=True)

    @app_commands.command(name="removebadword", description="Remove a word from the filter")
    @app_commands.guilds(GUILD)
    @app_commands.default_permissions(administrator=True)
    async def removebadword(self, interaction: discord.Interaction, word: str):
        if word.lower() in BAD_WORDS:
            BAD_WORDS.remove(word.lower())
            await interaction.response.send_message(f"Removed `{word}` from the filter.", ephemeral=True)
        else:
            await interaction.response.send_message(f"`{word}` is not in the filter.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
