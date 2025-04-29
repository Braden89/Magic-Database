from db import conn, cur
from collections import deque

# Cards we don't want to include in bacon paths (by name)
BLACKLIST = set([
    "Sol Ring", "Arcane Signet", "Command Tower", "Forest", "Island", "Mountain", "Swamp", "Plains",
    "Fabled Passage", "Evolving Wilds", "Arcane Lighthouse", "Temple of the False God",
])

def build_graph():
    cur.execute("""
        SELECT d1.card_id, d2.card_id
        FROM deck_cards d1
        JOIN deck_cards d2 ON d1.deck_id = d2.deck_id
        WHERE d1.card_id != d2.card_id
    """)
    rows = cur.fetchall()

    graph = {}
    for a, b in rows:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)

    return graph

def get_card_id(name):
    cur.execute("SELECT card_id FROM cards WHERE name = ?", (name,))
    row = cur.fetchone()
    return row[0] if row else None

def get_card_name(card_id):
    cur.execute("SELECT name FROM cards WHERE card_id = ?", (card_id,))
    row = cur.fetchone()
    return row[0] if row else str(card_id)

def bacon_number_cli():
    name1 = input("Enter first card name: ").strip()
    name2 = input("Enter second card name (or leave blank to find all within 4): ").strip()

    id1 = get_card_id(name1)
    if not id1:
        print(f"❌ Card not found: {name1}")
        return

    id2 = get_card_id(name2) if name2 else None
    if name2 and not id2:
        print(f"❌ Card not found: {name2}")
        return

    graph = build_graph()

    # Remove blacklisted cards
    cur.execute("SELECT card_id FROM cards WHERE name IN ({})".format(
        ",".join("?" for _ in BLACKLIST)
    ), list(BLACKLIST))
    blacklist_ids = {row[0] for row in cur.fetchall()}
    for banned in blacklist_ids:
        graph.pop(banned, None)
    for neighbors in graph.values():
        neighbors.difference_update(blacklist_ids)

    if id2:
        find_bacon_path(graph, id1, id2)
    else:
        find_bacon_neighbors(graph, id1)

def find_bacon_path(graph, start, goal):
    queue = deque([(start, [start])])
    visited = set()

    while queue:
        current, path = queue.popleft()
        if current == goal:
            print(f"✅ Bacon number between cards is {len(path) - 1}")
            print("Path:")
            for card_id in path:
                print("  →", get_card_name(card_id))
            return

        visited.add(current)
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                queue.append((neighbor, path + [neighbor]))

    print("❌ No connection found between cards.")

def find_bacon_neighbors(graph, start):
    queue = deque([(start, 0)])
    visited = {start}

    print("\nCards reachable within 4 steps:")
    while queue:
        current, distance = queue.popleft()
        if distance > 4:
            continue
        if distance > 0:
            print(f"Bacon {distance}: {get_card_name(current)}")

        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))
