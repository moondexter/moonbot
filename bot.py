import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import traceback
from keep_alive import keep_alive

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("bot")

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    from cogs.welcome import AgreementView
    bot.add_view(AgreementView())
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    log.info(f"Logged in as {bot.user} | Synced slash commands")

@bot.event
async def on_error(event, *args, **kwargs):
    log.error(f"Unhandled error in event '{event}':\n{traceback.format_exc()}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    log.error(f"App command error in '{interaction.command}': {error}", exc_info=error)
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)
        else:
            await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)
    except Exception:
        pass

async def main():
    async with bot:
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await bot.load_extension(f"cogs.{filename[:-3]}")
                    log.info(f"Loaded cog: {filename[:-3]}")
                except Exception as e:
                    log.error(f"Failed to load cog {filename}: {e}", exc_info=e)
        await bot.start(TOKEN)

import asyncio
keep_alive()
try:
    asyncio.run(main())
except KeyboardInterrupt:
    log.info("Bot stopped by user.")
except Exception as e:
    log.critical(f"Fatal error: {e}", exc_info=e)
