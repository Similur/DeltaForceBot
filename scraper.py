"""Fetch public Delta Force loadouts from CODMunity weapon pages."""

import re
from dataclasses import dataclass
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://codmunity.gg/weapon/deltaforce/"
WEAPONS = (
    "M4A1", "AKM", "AUG", "AS-VAL", "SCAR-H", "M16A4", "K416", "CI-19",
    "K437", "SG552", "AKS-74", "ASH-12", "G3", "M7", "MCX-LT-Assault-Rifle",
    "QCQ171", "MP5", "MP7", "P90", "Vector", "UZI", "SMG-45", "SR-3M",
    "Bizon", "Vityaz", "M249", "PKM", "M250", "QJB201", "S12K", "M870",
    "725", "M1014", "AWM", "R93", "SV-98", "M700", "SKS", "SVD",
    "VSS", "SR-25", "Mini-14", "M14", "G18", "93R",
)

HEADERS = {"User-Agent": "DeltaForceBuildBot/1.0 (personal project; public page lookup)"}
CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .'-]{1,80}-(?:Warfare|Operations)-[A-Z0-9]{8,}", re.I)
PRICE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*[kK]\b")
SLOTS = ("Muzzle", "Barrel", "Foregrip", "Optic", "Stock", "Magazine",
         "Grip", "Ammo", "Laser", "Gas Block", "Handguard", "Rail", "Mag")


@dataclass(frozen=True)
class WeaponBuild:
    weapon: str
    category: str
    attachments: tuple[str, ...]
    code: str | None
    price: str | None
    image: str | None
    url: str


def weapon_url(weapon: str) -> str:
    """Only build URLs for weapons in our supported list."""
    if weapon not in WEAPONS:
        raise ValueError(f"Unsupported weapon: {weapon}")
    return BASE_URL + quote(weapon.lower().replace(" ", "-"), safe="-")


def parse_weapon_page(html: str, weapon: str, category: str, url: str) -> WeaponBuild | None:
    """Pull out a likely loadout. Site layout changes may require parser updates."""
    soup = BeautifulSoup(html, "html.parser")
    image_tag = soup.find("meta", property="og:image")
    image = image_tag.get("content") if image_tag else None
    if image and not image.startswith("https://"):
        image = None

    # Find the relevant game mode first, rather than assuming the final card is cheap.
    requested_mode = "Operations" if category == "Budget" else "Warfare"
    cards = soup.find_all(["article", "section", "div"], class_=re.compile(r"card|loadout", re.I))
    # Large parent containers can overlap individual cards; prefer the smallest matching node.
    candidates = [card for card in cards if not card.find(["article", "section", "div"], class_=re.compile(r"card|loadout", re.I))]
    if not candidates:
        candidates = cards
    matching = [card for card in candidates if requested_mode.lower() in card.get_text(" ", strip=True).lower()]
    if matching:
        target = matching[0]
    elif candidates and category == "Expensive":
        target = candidates[0]
    else:
        # No reliable budget/Operations build to show, so don't invent one.
        return None

    text = target.get_text(" ", strip=True)
    price_match = PRICE_PATTERN.search(text)
    code = None
    for string in target.stripped_strings:
        match = CODE_PATTERN.search(string)
        if match:
            code = match.group(0)
            break
    attachments = []
    for element in target.find_all(["li", "p", "span"]):
        value = element.get_text(" ", strip=True)
        if 3 <= len(value) <= 90 and any(re.search(rf"\b{re.escape(slot)}\b", value, re.I) for slot in SLOTS):
            if value not in attachments:
                attachments.append(value)

    return WeaponBuild(
        weapon=weapon, category=category, attachments=tuple(attachments[:12]),
        code=code,
        price=price_match.group(0).upper().replace(" ", "") if price_match else None,
        image=image, url=url,
    )


def get_weapon_data(weapon: str, category: str) -> WeaponBuild | None:
    """Request and parse one public weapon page with a network timeout."""
    url = weapon_url(weapon)
    response = requests.get(url, headers=HEADERS, timeout=12)
    response.raise_for_status()
    return parse_weapon_page(response.text, weapon, category, url)
