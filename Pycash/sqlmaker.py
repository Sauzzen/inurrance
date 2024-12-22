import sqlite3

# Connect to SQLite database (creates a new database if it doesn't exist)
conn = sqlite3.connect('users.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# SQL command to create the users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Auto-increment ID
        username TEXT NOT NULL,                   -- Username (required)
        email TEXT UNIQUE NOT NULL,               -- Email (required and unique)
        password TEXT NOT NULL,                   -- Password (required)
        photo TEXT DEFAULT 'default.jpg',         -- Photo with default value
        is_admin BOOLEAN DEFAULT 0                -- Admin flag, default to False
    )
''')

# Commit changes and close the connection
conn.commit()
conn.close()

print("Table created successfully.")