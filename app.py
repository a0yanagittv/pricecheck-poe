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

    categories = [
        "UniqueWeapon", "UniqueArmour", "UniqueAccessory", "Flask",
        "DivinationCard", "SkillGem", "BaseType", "UniqueMap",
        "Map", "Oil", "Incubator", "Scarab", "Fossil", "Resonator",
        "Essence", "Currency", "Vial", "DeliriumOrb", "Invitation",
        "ClusterJewel", "Beast", "Fragment"
    ]
    items = []
    for category in categories:
        try:
            url = f"https://poe.ninja/api/data/itemoverview?league={league}&type={category}"
            data = requests.get(url).json()
            if "lines" in data:
                for i in data["lines"]:
                    items.append({
                        "name": i["name"],
                        "chaosValue": i["chaosValue"]
                    })
            else:
                logging.warning(f"Categoria sem 'lines': {category}")
        except Excepti
