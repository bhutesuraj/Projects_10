import sqlite3

connection = sqlite3.connect("student.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS STUDENT (
  NAME TEXT,
  CLASS TEXT,
  SECTION TEXT,
  MARKS INTEGER
)
""")

rows = [
    ('Ravi','Data Science','A',90),
    ('Sam','Data Science','B',100),
    ('Mukesh','Data Science','A',86),
    ('Yuvi','DEVOPS','A',50),
    ('Puru','DEVOPS','A',35),
]

# Insert only if not already present
for r in rows:
    cursor.execute("""
    INSERT INTO STUDENT (NAME, CLASS, SECTION, MARKS)
    SELECT ?, ?, ?, ?
    WHERE NOT EXISTS (
      SELECT 1 FROM STUDENT
      WHERE NAME=? AND CLASS=? AND SECTION=? AND MARKS=?
    )
    """, (*r, *r))

print("Current STUDENT rows:")
for row in cursor.execute("SELECT * FROM STUDENT"):
    print(row)

connection.commit()
connection.close()
