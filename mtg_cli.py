import sqlite3
import os
from datetime import date
from tabulate import tabulate
from mtg_scryfall import get_card_from_scryfall, insert_card
from moxfield_import import import_deck_from_list
from deck import deck_menu
from bacon import bacon_number_cli
from collection import import_collection_from_list, view_collection_ui
from bacon import bacon_number_cli



from db import conn, cur

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_card(name):
    card = get_card_from_scryfall(name)
    if not card:
        print("❌ Card not found.")
        return
    print(f"\n🔍 Name: {card['name']}")
    print(f"Mana Cost: {card.get('mana_cost')}")
    print(f"Type: {card['type_line']}")
    print(f"Oracle Text: {card.get('oracle_text')}")
    print(f"Power/Toughness: {card.get('power', '')}/{card.get('toughness', '')}")
    print(f"Colors: {', '.join(card.get('colors', []))}")
    print(f"Rarity: {card.get('rarity')}")
    print(f"Set: {card.get('set_name')}\n")

def print_deck(deck_id):
    cur.execute("""
        SELECT d.name, c.name
        FROM decks d JOIN cards c ON d.commander_id = c.card_id
        WHERE d.deck_id = ?
    """, (deck_id,))
    row = cur.fetchone()
    if not row:
        print("❌ Deck not found.")
        return

    print(f"\n🧩 Deck: {row[0]}\nCommander: {row[1]}\n")

    cur.execute("""
        SELECT c.name, dc.quantity, dc.is_commander
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.card_id
        WHERE dc.deck_id = ?
        ORDER BY dc.is_commander DESC, c.name ASC
    """, (deck_id,))
    cards = cur.fetchall()
    print(tabulate(cards, headers=["Card", "Qty", "Commander"]))

def import_manual_deck_ui():
    print("Paste your Moxfield-style decklist (end with a blank line):")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    import_deck_from_list("\n".join(lines))

def card_lookup_ui():
    name = input("Enter card name: ").strip()
    print_card(name)

def deck_lookup_ui():
    try:
        deck_id = int(input("Enter deck ID: ").strip())
        print_deck(deck_id)
    except ValueError:
        print("❌ Invalid ID.")

def search_decks_by_commander():
    name = input("Enter partial/full commander name: ").strip()
    cur.execute("""
        SELECT d.deck_id, d.name, c.name
        FROM decks d
        JOIN cards c ON d.commander_id = c.card_id
        WHERE c.name LIKE ?
        ORDER BY d.deck_id
    """, (f"%{name}%",))
    results = cur.fetchall()
    if not results:
        print("❌ No decks found.")
    else:
        print(tabulate(results, headers=["Deck ID", "Deck Name", "Commander"]))

def list_all_decks():
    cur.execute("""
        SELECT d.deck_id, d.name, c.name
        FROM decks d
        JOIN cards c ON d.commander_id = c.card_id
        ORDER BY d.deck_id
    """)
    decks = cur.fetchall()
    if not decks:
        print("❌ No decks in database.")
    else:
        print(tabulate(decks, headers=["Deck ID", "Deck Name", "Commander"]))

def import_collection_ui():
    print("Paste your card list (end with a blank line):")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    import_collection_from_list("\n".join(lines))


def main_loop():
    clear_screen()
    while True:
        print("\n====== MTG Commander Database CLI ======")
        print("1. Look up a card by name")
        print("2. Import deck from text list (Moxfield-style)")
        print("3. Import card collection from text list")
        print("4. View and filter your collection")
        print("5. Manage decks")
        print("6. Find bacon number between cards")
        print("7. Exit")

        choice = input("Choose an option (1–6): ").strip()

        clear_screen()

        if choice == "1":
            card_lookup_ui()
        elif choice == "2":
            import_manual_deck_ui()
        elif choice == "3":
            import_collection_ui()
        elif choice == "4":
            view_collection_ui()
        elif choice == "5":
            deck_menu()
        elif choice == "6":
            bacon_number_cli()
        elif choice == "7":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice.")


if __name__ == "__main__":
    main_loop()