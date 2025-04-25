import re
from mtg_scryfall import get_card_from_scryfall, insert_card
import sqlite3
from datetime import date
from db import conn, cur

line_regex = re.compile(r"(?P<qty>\d+)\s+(?P<name>.+?)\s+\([A-Z0-9]+\)\s+\d+[a-zA-Z]*")

def parse_decklist(text: str):
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    deck = []

    for line in lines:
        match = line_regex.match(line)
        if not match:
            print(f"⚠️ Skipping line: {line}")
            continue
        name = match.group("name")
        qty = int(match.group("qty"))
        deck.append((name, qty))
    
    return deck

def import_deck_from_list(decklist_text):
    deck = parse_decklist(decklist_text)
    if not deck:
        print("❌ No valid cards found.")
        return

    commander_name = deck[0][0]
    print(f"🔹 Commander: {commander_name}")

    commander_info = get_card_from_scryfall(commander_name)
    if not commander_info:
        print(f"❌ Could not find commander: {commander_name}")
        return

    commander_id = insert_card(commander_info)
    
    cur.execute("INSERT INTO deck_sources (website, url, date_scraped) VALUES (?, ?, ?)",
                ("Manual", "N/A", date.today()))
    source_id = cur.lastrowid

    deck_name = input("Enter a name for this deck: ")
    cur.execute("INSERT INTO decks (name, commander_id, source_id, date_created) VALUES (?, ?, ?, ?)",
                (deck_name, commander_id, source_id, date.today()))
    deck_id = cur.lastrowid

    for name, qty in deck:
        card_info = get_card_from_scryfall(name)
        if not card_info:
            print(f"⚠️ Skipping: {name}")
            continue
        card_id = insert_card(card_info)
        is_commander = name == commander_name
        cur.execute("INSERT INTO deck_cards (deck_id, card_id, quantity, is_commander) VALUES (?, ?, ?, ?)",
                    (deck_id, card_id, qty, is_commander))

    conn.commit()
    print(f"✅ Deck '{deck_name}' imported with {len(deck)} cards.")
