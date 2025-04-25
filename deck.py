from tabulate import tabulate
from moxfield_import import import_deck_from_list
from mtg_scryfall import get_card_from_scryfall, insert_card
from db import conn, cur

def deck_menu():
    while True:
        print("\n🧾 Deck Manager")
        print("1. View all decks")
        print("2. Search decks by commander name")
        print("3. View a deck by ID")
        print("4. Add a new deck (paste list)")
        print("5. Remove a deck")
        print("6. Back to main menu")

        choice = input("Choose an option (1–6): ").strip()

        if choice == "1":
            list_all_decks()
        elif choice == "2":
            search_decks_by_commander()
        elif choice == "3":
            deck_lookup_ui()
        elif choice == "4":
            import_manual_deck_ui()
        elif choice == "5":
            remove_deck_ui()
        elif choice == "6":
            break
        else:
            print("❌ Invalid option.")

def list_all_decks():
    cur.execute("""
        SELECT d.deck_id, d.name, c.name
        FROM decks d
        JOIN cards c ON d.commander_id = c.card_id
        ORDER BY d.deck_id
    """)
    decks = cur.fetchall()
    if not decks:
        print("❌ No decks found.")
    else:
        print(tabulate(decks, headers=["Deck ID", "Deck Name", "Commander"]))

def search_decks_by_commander():
    name = input("Enter part of the commander's name: ").strip()
    cur.execute("""
        SELECT d.deck_id, d.name, c.name
        FROM decks d
        JOIN cards c ON d.commander_id = c.card_id
        WHERE c.name LIKE ?
        ORDER BY d.deck_id
    """, (f"%{name}%",))
    results = cur.fetchall()
    if results:
        print(tabulate(results, headers=["Deck ID", "Deck Name", "Commander"]))
    else:
        print("❌ No matching decks.")

def deck_lookup_ui():
    try:
        deck_id = int(input("Enter deck ID: ").strip())
    except ValueError:
        print("❌ Invalid ID.")
        return

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
        ORDER BY dc.is_commander DESC, c.name
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

def remove_deck_ui():
    try:
        deck_id = int(input("Enter deck ID to remove: ").strip())
    except ValueError:
        print("❌ Invalid ID.")
        return

    cur.execute("SELECT name FROM decks WHERE deck_id = ?", (deck_id,))
    row = cur.fetchone()
    if not row:
        print("❌ Deck not found.")
        return

    confirm = input(f"Are you sure you want to delete '{row[0]}'? (y/n): ").strip().lower()
    if confirm == "y":
        cur.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
        cur.execute("DELETE FROM decks WHERE deck_id = ?", (deck_id,))
        conn.commit()
        print(f"🗑 Deck '{row[0]}' deleted.")
    else:
        print("❌ Deletion canceled.")