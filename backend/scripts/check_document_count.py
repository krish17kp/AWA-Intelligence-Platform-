import sqlite3

connection = sqlite3.connect("local.db")
cursor = connection.cursor()

count = cursor.execute("SELECT COUNT(*) FROM source_documents;").fetchone()[0]

print("source_documents count:", count)

connection.close()