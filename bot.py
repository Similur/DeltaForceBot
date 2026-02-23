import discord
from discord import app_commands
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import re
from typing import List

# --- CONFIGURATION ---
TOKEN = 'MTQ3NTYxNzE0MjAyMjg2OTEwMw.GQiWCa.VykxyceyAy6kOH6eXoPTRYlSntFVSPCUH7rbjE'
MY_GUILD_ID = 1344509250918944841  # Replace with your Server ID for instant sync
BASE_URL = "https://codmunity.gg/weapon/deltaforce/"

# List for Autocomplete
WEAPONS = [
    "M4A1", "AKM", "AUG", "AS-VAL", "SCAR-H", "M16A4", "K416", "CI-19", "K437", 
    "SG552", "AKS-74", "ASH-12", "G3", "M7", "MCX-LT-Assault-Rifle", "QCQ171", "MP5", "MP7", 
    "P90", "Vector", "UZI", "SMG-45", "SR-3M", "Bizon", "Vityaz", "M249", "PKM", 
    "M250", "QJB201", "S12K", "M870", "725", "M1014", "AWM", "R93", "SV-98", 
    "M700", "SKS", "SVD", "VSS", "SR-25", "Mini-14", "M14", "G18", "93R"
]

class BuildBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=MY_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"✅ Slash commands synced to Guild ID: {MY_GUILD_ID}")

bot = BuildBot()

def get_weapon_data(weapon_name: str, category: str):
    slug = weapon_name.lower().replace(" ", "-")
    url = f"{BASE_URL}{slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Scrape Weapon Image
        img_tag = soup.find('meta', property="og:image")
        image_url = img_tag['content'] if img_tag else None

        # 2. Refined Scrape Logic for Budget vs Expensive
        build_cards = soup.find_all('div', class_=re.compile("card|loadout", re.IGNORECASE))
        if not build_cards: return None

        target_card = None
        user_wants_budget = category.lower() == "budget"

        if user_wants_budget:
            # Look for specific "Budget" or "Operations" identifiers
            budget_keys = ["budget", "cheap", "low cost", "operations", "starter", "turmoil"]
            for card in build_cards:
                card_text = card.get_text().lower()
                if any(key in card_text for key in budget_keys):
                    target_card = card
                    break
            
            # If no budget-specific card is found, grab the very last card (usually the alt/budget build)
            if not target_card and len(build_cards) > 1:
                target_card = build_cards[-1]
        else:
            # Expensive/Meta is almost always the very first card
            target_card = build_cards[0]

        if target_card:
            # 3. Scrape Price (Look for "K" values like 150k, 200k)
            price = "Price unknown"
            # Search for text matching the "150k" or "200.5k" pattern
            price_match = re.search(r'(\d+(?:\.\d+)?k)', target_card.get_text(), re.IGNORECASE)
            if price_match:
                price = price_match.group(1).upper()

            # 4. Scrape Attachments
            slots = ["Muzzle", "Barrel", "Foregrip", "Optic", "Stock", "Magazine", "Grip", "Ammo", "Laser", "Gas Block", "Handguard"]
            attachments = []
            for el in target_card.find_all(['div', 'span', 'p', 'li']):
                text = el.get_text(strip=True)
                if any(s in text for s in slots) and len(text) < 80:
                    if text not in attachments: attachments.append(text)

            # 5. Scrape Share Code
            code = "No code found."
            for txt in target_card.find_all(string=re.compile("-Warfare-|-Operations-")):
                if len(txt.strip()) > 15:
                    code = txt.strip()
                    break

            return {
                "name": weapon_name.upper(),
                "category": "Budget/Operations" if user_wants_budget else "Expensive/Meta",
                "attachments": attachments[:12],
                "code": code,
                "price": price,
                "image": image_url,
                "url": url
            }
    except Exception as e:
        print(f"Scrape Error: {e}")
    return None

# --- SLASH COMMAND ---
@bot.tree.command(name="build", description="Fetch a Delta Force build from CODMunity")
@app_commands.describe(weapon="Gun name", category="Expensive (Meta) or Budget (Operations)")
async def build(interaction: discord.Interaction, weapon: str, category: str = "Expensive"):
    await interaction.response.defer() 

    data = get_weapon_data(weapon, category)
    
    if data:
        is_budget = "budget" in data['category'].lower()
        color = discord.Color.green() if is_budget else discord.Color.gold()
        
        embed = discord.Embed(
            title=f"🎯 {data['name']} - {data['category']}", 
            url=data['url'], 
            color=color
        )
        
        if data['image']:
            embed.set_image(url=data['image'])
        
        # Display Price at the top
        embed.add_field(name="💰 Est. Build Cost", value=f"**{data['price']}**", inline=False)
        
        attachment_str = "\n".join([f"✅ {a}" for a in data['attachments']])
        embed.add_field(name="Recommended Attachments", value=attachment_str or "No attachments found.", inline=False)
        
        embed.add_field(name="Import Code", value=f"```\n{data['code']}\n```", inline=False)
        embed.set_footer(text="Data: CODMunity.gg | /build [gun] [category]")
        
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Could not find data for **{weapon}**.")

# --- AUTOCOMPLETE ---
@build.autocomplete('weapon')
async def weapon_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    return [app_commands.Choice(name=w, value=w) for w in WEAPONS if current.lower() in w.lower()][:25]

@build.autocomplete('category')
async def category_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    choices = ["Expensive", "Budget"]
    return [app_commands.Choice(name=c, value=c) for c in choices if current.lower() in c.lower()]

bot.run(TOKEN)
