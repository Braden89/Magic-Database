import sqlite3

def initialize_database(schema_file="schema.sql", db_file="mtg_commander.db"):
    # Read the SQL schema file
    try:
        with open(schema_file, "r") as f:
            schema_sql = f.read()
    except FileNotFoundError:
        print(f"❌ Schema file '{schema_file}' not found.")
        return

    # Connect to the SQLite database
    try:
        conn = sqlite3.connect(db_file)
        conn.executescript(schema_sql)
        conn.commit()
        conn.close()
        print(f"✅ Database '{db_file}' initialized successfully using '{schema_file}'.")
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")

if __name__ == "__main__":
    initialize_database()