import re

from tabulate import tabulate
from mtg_scryfall import get_card_from_scryfall, insert_card
from db import conn, cur

line_regex = re.compile(r"(?P<qty>\d+)\s+(?P<name>.+?)\s+\([A-Z0-9]+\)\s+\d+[a-zA-Z]*")

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

    for name, qty in collection:
        card_info = get_card_from_scryfall(name)
        if not card_info:
            print(f"⚠️ Skipping (not found): {name}")
            continue

        card_id = insert_card(card_info)

        # Insert or update the collection quantity
        cur.execute("""
            INSERT INTO collection (card_id, quantity)
            VALUES (?, ?)
            ON CONFLICT(card_id) DO UPDATE SET quantity = quantity + EXCLUDED.quantity
        """, (card_id, qty))

    conn.commit()
    print(f"✅ Imported {len(collection)} cards into your collection.")


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


def multi_filter_collection():
    filters = []
    params = []

    print("\n🧩 Multi-Filter Collection View (press Enter to skip a filter):")

    color = input("Color (W, U, B, R, G): ").strip().upper()
    if color:
        filters.append("EXISTS (SELECT 1 FROM card_colors WHERE card_id = col.card_id AND color = ?)")
        params.append(color)

    cmc = input("CMC (exact number): ").strip()
    if cmc:
        try:
            filters.append("c.cmc = ?")
            params.append(float(cmc))
        except ValueError:
            print("⚠️ Skipping invalid CMC.")

    type_keyword = input("Card type keyword (e.g., Creature): ").strip()
    if type_keyword:
        filters.append("EXISTS (SELECT 1 FROM card_types WHERE card_id = col.card_id AND type LIKE ?)")
        params.append(f"%{type_keyword}%")

    rarity = input("Rarity (common, uncommon, rare, mythic): ").strip().lower()
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
        ORDER BY color
    """)
    rows = cur.fetchall()
    if not rows:
        print("📦 No color data in collection.")
    else:
        print("\n🎨 Card Count by Color:\n")
        print(tabulate(rows, headers=["Color", "Total"]))


def add_or_remove_card():
    name = input("Card name: ").strip()
    try:
        delta = int(input("Quantity to add (use negative to remove): ").strip())
    except ValueError:
        print("❌ Invalid number.")
        return

    card_info = get_card_from_scryfall(name)
    if not card_info:
        print(f"❌ Card not found: {name}")
        return

    card_id = insert_card(card_info)
    if delta > 0:
        cur.execute("""
            INSERT INTO collection (card_id, quantity)
            VALUES (?, ?)
            ON CONFLICT(card_id) DO UPDATE SET quantity = quantity + EXCLUDED.quantity
        """, (card_id, delta))
        print(f"✅ Added {delta} {name}")
    else:
        cur.execute("SELECT quantity FROM collection WHERE card_id = ?", (card_id,))
        row = cur.fetchone()
        if row:
            new_qty = max(0, row[0] + delta)
            if new_qty == 0:
                cur.execute("DELETE FROM collection WHERE card_id = ?", (card_id,))
                print(f"🗑 Removed all copies of {name}")
            else:
                cur.execute("UPDATE collection SET quantity = ? WHERE card_id = ?", (new_qty, card_id))
                print(f"➖ Reduced {name} to {new_qty}")
        else:
            print("📦 No copies to remove.")

    conn.commit()

    

def view_collection_ui():
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
        print("↩️ Returning to main menu...")
    else:
        print("❌ Invalid option.")
