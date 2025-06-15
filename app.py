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

    # 🔎 Busca exata primeiro
    exact_match = next((i for i in items if i["normalized_name"] == normalized_input), None)

    if exact_match:
        item_data = exact_match
    else:
        # ⚠️ Se o input for muito curto, evita fuzzy para prevenir falsos positivos
        if len(item_input) < 15 and len(item_input.split()) <= 2:
            return f"❌ Item '{item_input}' não encontrado. Verifique o nome e tente novamente."

        choices = [i["normalized_name"] for i in items]
        match = process.extractOne(normalized_input, choices, scorer=fuzz.WRatio)
        if not match or match[1] < 85:
            return f"❌ Item '{item_input}' não encontrado. Verifique o nome e tente novamente."

        matched_index = choices.index(match[0])
        item_data = items[matched_index]

    chaos = round(item_data["chaosValue"], 1)
    div = round(chaos / divine_value, 1)

    return (f"💰 {item_data['name']} → ~{chaos}c | ~{div} Divine "
            f"(1 Divine ≈ {round(divine_value, 1)}c) [Mercenaries]")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
