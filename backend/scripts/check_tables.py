import sqlite3

connection = sqlite3.connect("local.db")
cursor = connection.cursor()

tables = cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table';"
).fetchall()

print("Tables found:")
print(tables)

connection.close()