CREATE TABLE cards (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mana_cost TEXT,
    cmc REAL,
    type_line TEXT,
    power TEXT,
    toughness TEXT,
    oracle_text TEXT,
    is_legendary BOOLEAN,
    set_code TEXT,
    rarity TEXT
);

CREATE TABLE card_types (
    card_id INTEGER,
    type TEXT,
    FOREIGN KEY (card_id) REFERENCES cards(card_id)
);


CREATE TABLE card_colors (
    card_id INTEGER,
    color TEXT,
    FOREIGN KEY (card_id) REFERENCES cards(card_id)
);


CREATE TABLE decks (
    deck_id INTEGER PRIMARY KEY,
    name TEXT,
    commander_id INTEGER,
    source_id INTEGER,
    date_created DATE,
    FOREIGN KEY (commander_id) REFERENCES cards(card_id),
    FOREIGN KEY (source_id) REFERENCES deck_sources(source_id)
);


CREATE TABLE deck_cards (
    deck_id INTEGER,
    card_id INTEGER,
    quantity INTEGER,
    is_commander BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (deck_id) REFERENCES decks(deck_id),
    FOREIGN KEY (card_id) REFERENCES cards(card_id)
);


CREATE TABLE deck_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    website TEXT,
    url TEXT,
    date_scraped DATE
);

CREATE TABLE collection (
    card_id INTEGER,
    quantity INTEGER,
    FOREIGN KEY (card_id) REFERENCES cards(card_id),
    PRIMARY KEY (card_id)
);