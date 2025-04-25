import re
from db import conn, cur
from mtg_scryfall import get_cards_from_scryfall, get_card_from_scryfall, insert_card
from tabulate import tabulate

# Updated regex for card list parsing
line_regex = re.compile(r"(?P<qty>\d+)\s+(?P<name>.+?)\s+\([^)]+\)\s+[A-Z0-9\-]+")


def view_collection_ui():
    while True:
        print("\n📋 View Your Collection")
        print("1. View full collection")
        print("2. Filter by color")
        print("3. Filter by mana cost (cmc)")
        print("4. Filter by type")
        print("5. Filter by rarity")
        print("6. Multi-filter search")
        print("7. Color breakdown (pie-style count)")
        print("8. Add/Remove cards manually")
        print("9. Back to main menu")

        choice = input("Choose an option (1–9): ").strip()

        if choice == "1":
            show_collection()
        elif choice == "2":
            color = input("Enter color (W, U, B, R, G): ").strip().upper()
            show_collection("EXISTS (SELECT 1 FROM card_colors WHERE card_id = col.card_id AND color = ?)", [color])
        elif choice == "3":
            try:
                cmc = float(input("Enter converted mana cost: "))
                show_collection("c.cmc = ?", [cmc])
            except ValueError:
                print("❌ Invalid number.")
        elif choice == "4":
            type_keyword = input("Enter card type keyword (e.g., Creature, Artifact): ").strip()
            show_collection("EXISTS (SELECT 1 FROM card_types WHERE card_id = col.card_id AND type LIKE ?)", [f"%{type_keyword}%"])
        elif choice == "5":
            rarity = input("Enter rarity (common, uncommon, rare, mythic): ").strip().lower()
            show_collection("c.rarity = ?", [rarity])
        elif choice == "6":
            multi_filter_collection()
        elif choice == "7":
            show_color_distribution()
        elif choice == "8":
            add_or_remove_card()
        elif choice == "9":
            break
        else:
            print("❌ Invalid option.")


def show_collection(where_clause: str = "", params: list = []):
    query = """
        SELECT c.name, c.mana_cost, c.type_line, c.rarity, col.quantity
        FROM collection col
        JOIN cards c ON col.card_id = c.card_id
    """
    if where_clause:
        query += f" WHERE {where_clause}"
    query += " ORDER BY col.quantity DESC, c.name"

    cur.execute(query, params)
    rows = cur.fetchall()
    if not rows:
        print("📦 No matching cards in your collection.")
    else:
        print(tabulate(rows, headers=["Card", "Mana Cost", "Type", "Rarity", "Quantity"]))


def parse_card_list(text: str):
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    entries = []

    for line in lines:
        match = line_regex.match(line)
        if not match:
            print(f"⚠️ Skipping line: {line}")
            continue
        name = match.group("name")
        qty = int(match.group("qty"))
        entries.append((name, qty))

    return entries

def import_collection_from_list(cardlist_text):
    collection = parse_card_list(cardlist_text)
    if not collection:
        print("❌ No valid cards found.")
        return

    # Batch in groups of 60
    card_data_map = {}
    for i in range(0, len(collection), 60):
        batch = collection[i:i + 60]
        names_to_fetch = [name for name, _ in batch]
        result = get_cards_from_scryfall(names_to_fetch)
        card_data_map.update(result)

    imported_count = 0
    for name, qty in collection:
        card = card_data_map.get(name)
        if not card:
            print(f"⚠️ Skipping (not found): {name}")
            continue

        card_id = insert_card(card)

        cur.execute("""
            INSERT INTO collection (card_id, quantity)
            VALUES (?, ?)
            ON CONFLICT(card_id) DO UPDATE SET quantity = quantity + EXCLUDED.quantity
        """, (card_id, qty))
        imported_count += 1

    conn.commit()
    print(f"✅ Imported {imported_count} cards into your collection.")

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
        display_rows = []
        for name, in_deck, in_collection in cards:
            if in_collection < in_deck:
                display_rows.append([
                    f"\033[91m{name}\033[0m",
                    f"\033[91m{in_deck}\033[0m",
                    f"\033[91m{in_collection}\033[0m"
                ])
            else:
                display_rows.append([name, in_deck, in_collection])

        print(tabulate(display_rows, headers=["Card", "In Deck", "In Collection"]))


def multi_filter_collection():
    filters = []
    params = []

    print("\n🧩 Multi-Filter Collection View (press Enter to skip a filter):")

    color = input("Filter by color (W, U, B, R, G): ").strip().upper()
    if color:
        filters.append("EXISTS (SELECT 1 FROM card_colors WHERE card_id = col.card_id AND color = ?)")
        params.append(color)

    cmc = input("Filter by converted mana cost (e.g. 3): ").strip()
    if cmc:
        try:
            filters.append("c.cmc = ?")
            params.append(float(cmc))
        except ValueError:
            print("⚠️ Skipping invalid CMC.")

    type_keyword = input("Filter by type keyword (e.g. Creature): ").strip()
    if type_keyword:
        filters.append("EXISTS (SELECT 1 FROM card_types WHERE card_id = col.card_id AND type LIKE ?)")
        params.append(f"%{type_keyword}%")

    rarity = input("Filter by rarity (common, uncommon, rare, mythic): ").strip().lower()
    if rarity:
        filters.append("c.rarity = ?")
        params.append(rarity)

    where_clause = " AND ".join(filters) if filters else ""
    show_collection(where_clause, params)


def show_color_distribution():
    cur.execute("""
        SELECT color, SUM(col.quantity) AS total
        FROM card_colors cc
        JOIN collection col ON cc.card_id = col.card_id
        GROUP BY color
        ORDER BY total DESC
    """)
    rows = cur.fetchall()
    if not rows:
        print("📦 No color data in collection.")
    else:
        print("\n🎨 Card Count by Color:\n")
        print(tabulate(rows, headers=["Color", "Total"]))


def add_or_remove_card():
    name = input("Card name: ").strip()
    if not name:
        print("❌ Card name cannot be empty.")
        return

    try:
        delta = int(input("Quantity to add (use negative number to remove): ").strip())
    except ValueError:
        print("❌ Invalid number.")
        return

    card = get_card_from_scryfall(name)
    if not card:
        print(f"❌ Card not found: {name}")
        return

    card_id = insert_card(card)

    cur.execute("SELECT quantity FROM collection WHERE card_id = ?", (card_id,))
    row = cur.fetchone()

    if row:
        new_quantity = max(0, row[0] + delta)
        if new_quantity == 0:
            cur.execute("DELETE FROM collection WHERE card_id = ?", (card_id,))
            print(f"🗑 Removed all copies of '{name}' from your collection.")
        else:
            cur.execute("UPDATE collection SET quantity = ? WHERE card_id = ?", (new_quantity, card_id))
            print(f"🔄 Updated '{name}' to quantity {new_quantity}.")
    else:
        if delta > 0:
            cur.execute("INSERT INTO collection (card_id, quantity) VALUES (?, ?)", (card_id, delta))
            print(f"✅ Added {delta} of '{name}' to your collection.")
        else:
            print(f"⚠️ Cannot remove '{name}' — it's not in your collection.")

    conn.commit()