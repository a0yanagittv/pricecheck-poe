from flask import Flask, request
import requests
from rapidfuzz import process, fuzz
import os
import time
import logging
import unicodedata
import re

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

_item_cache = {"data": [], "timestamp": 0}
CACHE_DURATION = 60  # cache em segundos

def normalize(text):
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")  # remove acentos
    text = re.sub(r"[^a-z0-9\s]", "", text)  # remove pontuação
    text = text.strip()
    return text

@app.route("/")
def home():
    return "✅ API online para !pricecheck"

def get_all_items(league="Mercenaries"):
    now = time.time()
    if now - _item_cache["timestamp"] < CACHE_DURATION:
        return _item_cache["data"]

    categories = [
        "UniqueWeapon", "UniqueArmour", "UniqueAccessory", "Flask",
        "DivinationCard", "SkillGem", "BaseType", "HelmetEnchant", "UniqueMap",
        "Map", "Oil", "Incubator", "Scarab", "Fossil", "Resonator", "Essence",
        "Currency", "Vial", "DeliriumOrb", "Invitation", "Watchstone",
        "Contract", "Blueprint", "Component", "ClusterJewel", "Beast",
        "MemoryLine", "KiracMod", "Sentinel", "Relic", "Fragment"
    ]
    items = []
    for category in categories:
        try:
            url = f"https://poe.ninja/api/data/itemoverview?league={league}&type={category}"
            data = requests.get(url).json()
            for i in data["lines"]:
                items.append({
                    "name": i["name"],
                    "chaosValue": i["chaosValue"],
                    "normalized": normalize(i["name"])
                })
        except Exception as e:
            logging.warning(f"Erro ao buscar categoria {category}: {e}")
            continue

    _item_cache["data"] = items
    _item_cache["timestamp"] = now
    return items

def get_divine_value(league="Mercenaries"):
    try:
        url = f"https://poe.ninja/api/data/currencyoverview?league={league}&type=Currency"
        data = requests.get(url).json()
        for c in data["lines"]:
            if c["currencyTypeName"].lower() == "divine orb":
                return c["chaosEquivalent"]
    except Exception as e:
        logging.warning(f"Erro ao buscar valor do Divine Orb: {e}")
    return 180  # fallback padrão

@app.route("/pricecheck")
def pricecheck():
    item_input = request.args.get("item", "").strip()
    if not item_input:
        return "❌ Especifique um item: !pricecheck Mageblood"

    league = request.args.get("league", "Mercenaries")

    divine_value = get_divine_value(league)
    items = get_all_items(league)

    normalized_input = normalize(item_input)

    # Primeiro tentamos match exato com normalize
    item_data = next((i for i in items if i["normalized"] == normalized_input), None)

    # Se não achou exato, tenta fuzzy match na lista normalizada
    if not item_data:
        choices = [i["normalized"] for i in items]
        match = process.extractOne(normalized_input, choices, scorer=fuzz.WRatio)
        if not match or match[1] < 70:
            return f"❌ Item '{item_input}' não encontrado. Verifique o nome e tente novamente."
        matched_norm = match[0]
        item_data = next(i for i in items if i["normalized"] == matched_norm)

    chaos = round(item_data["chaosValue"], 1)
    div = round(chaos / divine_value, 1)

    return (f"💰 {item_data['name']} → ~{chaos}c | ~{div} Divine "
            f"(1 Divine ≈ {round(divine_value, 1)}c) [{league}]")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
