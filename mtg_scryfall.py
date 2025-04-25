import requests
import sqlite3
from db import conn, cur
import httpx

def get_card_from_scryfall(name):
    """Fetch card info from Scryfall."""
    url = f"https://api.scryfall.com/cards/named?exact={name}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None


def get_cards_from_scryfall(names: list[str]) -> dict[str, dict]:
    if not names:
        return {}

    unique_names = list(set(names))  # Remove duplicates
    payload = {
        "identifiers": [{"name": name} for name in unique_names]
    }


    try:
        response = httpx.post("https://api.scryfall.com/cards/collection", json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        card_map = {card["name"]: card for card in data["data"]}
        return card_map

    except httpx.HTTPError as e:
        print(f"❌ Scryfall batch lookup failed: {e}")
        return {}
    

def insert_card(card):
    """Insert card into the database and return card_id."""
    cur.execute("""
        INSERT OR IGNORE INTO cards (name, mana_cost, cmc, type_line, power, toughness, oracle_text, is_legendary, set_code, rarity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        card['name'],
        card.get('mana_cost'),
        card['cmc'],
        card['type_line'],
        card.get('power'),
        card.get('toughness'),
        card.get('oracle_text', ''),
        'legendary' in card.get('type_line', '').lower(),
        card['set'],
        card['rarity']
    ))

    cur.execute("SELECT card_id FROM cards WHERE name = ?", (card['name'],))
    card_id = cur.fetchone()[0]

    for color in card.get('colors', []):
        cur.execute("INSERT OR IGNORE INTO card_colors (card_id, color) VALUES (?, ?)", (card_id, color))

    type_part = card['type_line'].split("—")[0]
    for t in type_part.strip().split():
        cur.execute("INSERT OR IGNORE INTO card_types (card_id, type) VALUES (?, ?)", (card_id, t))

    conn.commit()
    return card_id


