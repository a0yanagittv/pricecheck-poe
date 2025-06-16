from flask import Flask, request
import requests
from rapidfuzz import process, fuzz
import os
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

_item_cache = {"data": [], "timestamp": 0}
CACHE_DURATION = 60  # segundos

@app.route("/")
def home():
    return "✅ API online para !pricecheck"

def get_all_items(league="Mercenaries"):
    now = time.time()
    if now - _item_cache["timestamp"] < CACHE_DURATION:
        return _item_cache["data"]

    categories = ["UniqueWeapon", "UniqueArmour", "UniqueAccessory", "DivinationCard", "SkillGem", "BaseType",
                  "UniqueMap", "Map", "Oil", "Incubator", "Scarab", "Fossil", "Resonator", "Essence", "Currency",
                  "Vial", "DeliriumOrb", "Invitation", "ClusterJewel", "Beast", "Fragment"]

    items = []
    for category in categories:
        try:
            url = f"https://poe.ninja/api/data/itemoverview?league={league}&type={category}"
            data = requests.get(url).json()
            if "lines" not in data:
                logging.warning(f"Categoria {category} não possui 'lines', pulando.")
                continue
            for i in data["lines"]:
                items.append({
                    "name": i["name"],
                    "chaosValue": i["chaosValue"]
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
    return 180  # fallback

@app.route("/pricecheck")
def pricecheck():
    item_input = request.args.get("item", "").strip()
    if not item_input:
        return "❌ Especifique um item: !pricecheck Mageblood"

    league = request.args.get("league", "Mercenaries")
    divine_value = get_divine_value(league)
    items = get_all_items(league)

    choices = [i["name"] for i in items]
    match = process.extractOne(item_input, choices, scorer=fuzz.WRatio)
    if not match or match[1] < 70:
        return f"❌ Item '{item_input}' não encontrado. Verifique o nome e tente novamente."

    matched_name = match[0]
    item_data = next((i for i in items if i["name"] == matched_name), None)
    if not item_data:
        return f"❌ Item '{item_input}' não encontrado. Verifique o nome e tente novamente."

    chaos = round(item_data["chaosValue"], 1)
    div = round(chaos / divine_value, 1)

    return (f"💰 {matched_name} → ~{chaos}c | ~{div} Divine "
            f"(1 Divine ≈ {round(divine_value, 1)}c) [{league}]")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
