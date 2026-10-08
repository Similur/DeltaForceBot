"""Discord slash command for looking up Delta Force weapon builds."""

import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from requests import RequestException

from scraper import WEAPONS, get_weapon_data

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def required_config() -> tuple[str, int]:
    """Read secrets at startup instead of putting them in source control."""
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
    if not token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN. See .env.example.")
    if not guild_id.isdecimal():
        raise RuntimeError("DISCORD_GUILD_ID must be a numeric server ID.")
    return token, int(guild_id)


class BuildBot(commands.Bot):
    def __init__(self, guild_id: int):
        # Slash commands don't need access to the content of server messages.
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.guild_id = guild_id

    async def setup_hook(self):
        guild = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info("Slash commands synced to the configured server")


def make_embed(data):
    color = discord.Color.green() if data.category == "Budget" else discord.Color.gold()
    embed = discord.Embed(title=f"🎯 {data.weapon} — {data.category}", url=data.url, color=color)
    if data.image:
        embed.set_image(url=data.image)
    embed.add_field(name="Estimated cost", value=data.price or "Not listed", inline=False)
    attachments = "\n".join(f"• {a}" for a in data.attachments)
    embed.add_field(name="Attachments", value=(attachments or "Not found")[:1024], inline=False)
    # Discord has a 1024-character limit on embed field values.
    code = (data.code or "Not found").replace("`", "")
    embed.add_field(name="Import code", value=f"```{code[:950]}```", inline=False)
    embed.set_footer(text="Source: CODMunity.gg • External builds may change")
    return embed


def main():
    token, guild_id = required_config()
    bot = BuildBot(guild_id)

    @bot.tree.command(name="build", description="Look up a Delta Force loadout on CODMunity")
    @app_commands.describe(weapon="Choose a weapon", category="Warfare/meta or Operations build")
    @app_commands.choices(category=[
        app_commands.Choice(name="Expensive / Meta", value="Expensive"),
        app_commands.Choice(name="Budget / Operations", value="Budget"),
    ])
    async def build(interaction: discord.Interaction, weapon: str, category: str = "Expensive"):
        await interaction.response.defer(thinking=True)
        if weapon not in WEAPONS:
            await interaction.followup.send("Please select a weapon from autocomplete.", ephemeral=True)
            return
        try:
            # requests is blocking, so move the lookup off Discord's event loop.
            data = await asyncio.to_thread(get_weapon_data, weapon, category)
        except (RequestException, ValueError):
            logger.exception("Weapon lookup failed")
            await interaction.followup.send("The build site couldn't be reached right now.")
            return
        if data is None:
            await interaction.followup.send(f"I couldn't find a reliable {category.lower()} build for **{weapon}**.")
            return
        await interaction.followup.send(embed=make_embed(data))

    @build.autocomplete("weapon")
    async def weapon_autocomplete(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=w, value=w) for w in WEAPONS
                if current.casefold() in w.casefold()][:25]

    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
