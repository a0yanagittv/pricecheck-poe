from flask import Flask, request
import requests
from rapidfuzz import process, fuzz
import unicodedata
import os

app = Flask(__name__)


@app.route("/")
def home():
    return "API online para !pricecheck"


def normalize(text):
    """Remove acentos e converte para minúsculas"""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    ).lower()


def get_all_items():
    categories = [
        "UniqueWeapon", "UniqueArmour", "UniqueAccessory", "Flask",
        "DivinationCard", "SkillGem", "BaseType", "HelmetEnchant", "UniqueMap",
        "Map", "Oil", "Incubator", "Scarab", "Fossil", "Resonator", "Essence",
        "Currency", "Vial", "DeliriumOrb", "Invitation",
        "ClusterJewel", "Beast", "Fragment"
    ]
    items = []
    for category in categories:
        try:
            url = f"https://poe.ninja/api/data/itemoverview?league=Mercenaries&type={category}"
            data = requests.get(url).json()
            for i in data.get("lines", []):
                items.append({
                    "name": i["name"],
                    "chaosValue": i["chaosValue"],
                    "normalized_name": normalize(i["name"])
                })
        except Exception:
            continue
    return items


@app.route("/pricecheck")
def pricecheck():
    item_input = request.args.get("item", "").strip()
    if not item_input:
        return "❌ Especifique um item: !pricecheck Mageblood"

    divine_value = 180
    try:
        currency_data = requests.get(
            "https://poe.ninja/api/data/currencyoverview?league=Mercenaries&type=Currency"
        ).json()
        for c in currency_data["lines"]:
            if c["currencyTypeName"].lower() == "divine orb":
                divine_value = c["chaosEquivalent"]
                break
    except:
        pass

    items = get_all_items()
    normalized_input = normalize(item_input)

    # 🟢 Tenta correspondência exata primeiro
    exact_match = next((i for i in items if_
