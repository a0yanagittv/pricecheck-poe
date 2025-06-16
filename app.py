from flask import Flask, request, jsonify
import requests
from rapidfuzz import process, fuzz
import os
import time
import logging
import json
import unicodedata

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

CACHE_DURATION = 60  # segundos
CACHE_FILE = "item_cache.json"

VALID_LEAGUES = [
    "Mercenaries", "Standard", "Hardcore", "SSF Standard", "SSF Hardcore"
]

_item_cache = {
    "timestamp": 0,
    "data": []
}

def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_item_cache, f)
        logging.info("Cache salvo no disco.")
    except Exception as e:
        logging.error(f"Falha ao salvar cache: {e}")

def load_cache():
    global _item_cache
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _item_cache = json.load(f)
            logging.info("Cache carregado do disco.")
        except Exception as e:
            logging.warning(f"Falha ao carregar cache: {e}")

def normalize_text(text):
    # Remove acentos e deixa tudo lowercase para comparação fuzzy
    nfkd = unicodedata.normalize('NFKD', text)
    only_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return only_ascii.lower()

@app.route("/")
def home():
    return "✅ API online para !pricecheck"

@app.route("/leagues")
def leagues():
    return jsonify({"valid_leagues": VALID_LEAGUES})

def fetch_items(league):
    categories = [
        "UniqueWeapon", "UniqueArmour", "UniqueAccessory",
        "DivinationCard", "SkillGem", "BaseType", "UniqueMap",
        "Map", "Oil", "Incubator", "Scarab", "Fossil", "Resonator", "Essence",
        "Currency", "Vial", "DeliriumOrb", "Invitation",
        "ClusterJewel", "Beast", "Fragment"
    ]
    items = []
    for category in categories:
        url = f"https://poe.ninja/api/data/itemoverview?league={league}&type={category}"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            lines = data.get("lines")
            if not lines:
                logging.warning(f"Categoria {category} não possui 'lines', pulando.")
                continue
            for i in lines:
                name = i.get("name")
                chaos = i.get("chaosValue")
                if name and chaos is not None:
                    items.append({"name": name, "chaosValue": chaos})
        except Exception as e:
            logging.warning(f"Erro ao buscar categoria {category}: {e}")
    return items

def get_all_items(league="Mercenaries"):
    now = time.time()
    if now - _item_cache["timestamp"] < CACHE_DURATION and _item_cache["data"]:
        return _item_cache["data"]

    logging.info(f"Atualizando cache de itens para liga {league}...")
    items = fetch_items(league)
    _item_cache["data"] = items
    _item_cache["timestamp"] = now
    save_cache()
    return items

def get_divine_value(league="Mercenaries"):
    url = f"https://poe.ninja/api/data/currencyoverview?league={league}&type=Currency"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        for c in data.get("lines", []):
            if c.get("currencyTypeName", "").lower() == "divine orb":
                return c.get("chaosEquivalent", 180)
    except Exception as e:
        logging.warning(f"Erro ao buscar valor do Divine Orb: {e}")
    return 180  # fallback

@app.route("/pricecheck")
def pricecheck():
    item_input = request.args.get("item", "").strip()
    if not item_input:
        return jsonify({"error": "❌ Especifique um item: !pricecheck Mageblood"}), 400
    if len(item_input) > 100:
        return jsonify({"error": "❌ Nome do item muito longo."}), 400

    league = request.args.get("league", "Mercenaries")
    if league not in VALID_LEAGUES:
        return jsonify({"error": f"Liga inválida. Use uma dessas: {', '.join(VALID_LEAGUES)}"}), 400

    divine_value = get_divine_value(league)
    items = get_all_items(league)

    # Normalizar nomes para melhorar busca fuzzy
    choices = [i["name"] for i in items]
    norm_choices = [normalize_text(c) for c in choices]
    norm_input = normalize_text(item_input)

    match = process.extractOne(norm_input, norm_choices, scorer=fuzz.WRatio, score_cutoff=70)
    if not match:
        return jsonify({"error": f"❌ Item '{item_input}' não encontrado. Verifique o nome e tente novamente."}), 404

    matched_index = norm_choices.index(match[0])
    matched_name = choices[matched_index]
    item_data = items[matched_index]

    chaos = round(item_data["chaosValue"], 1)
    div = round(chaos / divine_value, 1)

    result = {
        "item": matched_name,
        "chaosValue": chaos,
        "divineValue": div,
        "divineChaosEquivalent": round(divine_value, 1),
        "league": league,
        "message": f"💰 {matched_name} → ~{chaos}c | ~{div} Divine "
                   f"(1 Divine ≈ {round(divine_value, 1)}c) [{league}]"
    }
    return jsonify(result)

if __name__ == "__main__":
    load_cache()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
