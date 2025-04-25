from tabulate import tabulate
from moxfield_import import import_deck_from_list
from mtg_scryfall import get_card_from_scryfall, insert_card
from db import conn, cur
import os

def deck_menu():
    while True:
        
        print("\n🧾 Deck Manager")
        print("1. View all decks")
        print("2. Search decks by commander name")
        print("3. View a deck by ID")
        print("4. Add a new deck (paste list)")
        print("5. Remove a deck")
        print("6. Rename a deck")
        print("7. Deck statistics")
        print("8. Back to main menu")

        choice = input("Choose an option (1–8): ").strip()
        clear_screen()

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
            rename_deck_ui()
        elif choice == "7":
            deck_stats_ui()
        elif choice == "8":
            break
        else:
            print("❌ Invalid option.")


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


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
        SELECT c.name, dc.quantity AS in_deck,
               IFNULL(col.quantity, 0) AS in_collection
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.card_id
        LEFT JOIN collection col ON dc.card_id = col.card_id
        WHERE dc.deck_id = ?
        ORDER BY c.name
    """, (deck_id,))
    cards = cur.fetchall()
    display_rows = []

    for name, in_deck, in_collection in cards:
        if in_collection < in_deck:
            # Apply red formatting to the whole row
            display_rows.append([
                f"\033[91m{name}\033[0m",
                f"\033[91m{in_deck}\033[0m",
                f"\033[91m{in_collection}\033[0m"
            ])
        else:
            display_rows.append([name, in_deck, in_collection])

    print(tabulate(display_rows, headers=["Card", "In Deck", "In Collection"]))

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
    if confirm != "y":
        print("❌ Deletion canceled.")
        return

    # Delete the deck and related cards
    cur.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
    cur.execute("DELETE FROM decks WHERE deck_id = ?", (deck_id,))

    # Shift all decks with higher IDs down by one
    cur.execute("SELECT deck_id FROM decks WHERE deck_id > ? ORDER BY deck_id", (deck_id,))
    decks_to_shift = [row[0] for row in cur.fetchall()]

    for old_id in decks_to_shift:
        new_id = old_id - 1
        cur.execute("UPDATE decks SET deck_id = ? WHERE deck_id = ?", (new_id, old_id))
        cur.execute("UPDATE deck_cards SET deck_id = ? WHERE deck_id = ?", (new_id, old_id))

    conn.commit()
    print(f"🗑 Deck '{row[0]}' removed and deck IDs reindexed.")


def deck_stats_ui():
    print("\n📊 Deck Statistics")

    print("\n🎨 Most Used Colors:")
    cur.execute("""
        SELECT color, COUNT(*) as total
        FROM deck_cards dc
        JOIN card_colors cc ON dc.card_id = cc.card_id
        GROUP BY color
        ORDER BY total DESC
    """)
    print(tabulate(cur.fetchall(), headers=["Color", "Count"]))

    print("\n🧠 Most Common Card Types (excluding basic lands):")
    cur.execute("""
        SELECT ct.type, COUNT(*) as total
        FROM deck_cards dc
        JOIN card_types ct ON dc.card_id = ct.card_id
        JOIN cards c ON dc.card_id = c.card_id
        WHERE c.type_line NOT LIKE '%Basic%'
        GROUP BY ct.type
        ORDER BY total DESC
    """)
    print(tabulate(cur.fetchall(), headers=["Type", "Count"]))

    print("\n💡 Most Used Cards (excluding basics):")
    cur.execute("""
        SELECT c.name, SUM(dc.quantity) as total
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.card_id
        WHERE c.type_line NOT LIKE '%Basic%'
        GROUP BY c.name
        ORDER BY total DESC
        LIMIT 10
    """)
    print(tabulate(cur.fetchall(), headers=["Card", "Total Uses"]))

    print("\n📏 Average Converted Mana Cost (CMC):")
    cur.execute("""
        SELECT ROUND(AVG(c.cmc), 2)
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.card_id
        WHERE c.cmc IS NOT NULL
    """)
    print(f"Average CMC: {cur.fetchone()[0]}")

    print("\n🌍 Land vs Nonland Cards (by count):")
    cur.execute("""
        SELECT
            SUM(CASE WHEN c.type_line LIKE '%Land%' THEN dc.quantity ELSE 0 END) AS Land,
            SUM(CASE WHEN c.type_line NOT LIKE '%Land%' THEN dc.quantity ELSE 0 END) AS Nonland
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.card_id
    """)
    land, nonland = cur.fetchone()
    print(f"Land: {land} | Nonland: {nonland} | Ratio: {round(land / nonland, 2) if nonland else 'N/A'}")


def rename_deck_ui():
    try:
        deck_id = int(input("Enter the deck ID to rename: ").strip())
    except ValueError:
        print("❌ Invalid ID.")
        return

    cur.execute("SELECT name FROM decks WHERE deck_id = ?", (deck_id,))
    row = cur.fetchone()
    if not row:
        print("❌ Deck not found.")
        return

    current_name = row[0]
    print(f"Current name: {current_name}")
    new_name = input("Enter new deck name: ").strip()

    if not new_name:
        print("❌ Name cannot be empty.")
        return

    cur.execute("UPDATE decks SET name = ? WHERE deck_id = ?", (new_name, deck_id))
    conn.commit()
    print(f"✅ Renamed deck ID {deck_id} to '{new_name}'")


def display_deck_with_collection(deck_id):
    cur.execute("""
        SELECT c.name, dc.quantity AS in_deck,
               IFNULL(col.quantity, 0) AS in_collection
        FROM deck_cards dc
        JOIN cards c ON dc.card_id = c.card_id
        LEFT JOIN collection col ON dc.card_id = col.card_id
        WHERE dc.deck_id = ?
        ORDER BY c.name
    """, (deck_id,))
    cards = cur.fetchall()
    if not cards:
        print("❌ No cards found for this deck.")
    else:
        print(tabulate(cards, headers=["Card", "In Deck", "In Collection"]))