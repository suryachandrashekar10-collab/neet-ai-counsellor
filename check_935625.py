import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLEXPRESS;"
    "DATABASE=neet_counsellor;Trusted_Connection=yes;"
)
cur = conn.cursor()

print("=== All students with AIR exactly 935625 ===")
cur.execute("""
    SELECT air, name, neet_roll, cet_form, category, college_code, college_name, round, allotted
    FROM allotments
    WHERE air = 935625
    ORDER BY round
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        status = "ALLOTTED" if r.allotted else "NOT allotted"
        print(f"  {r.round}  AIR {r.air:,}  {r.name}")
        print(f"        Cat: {r.category}  College: [{r.college_code}] {r.college_name}  → {status}")
else:
    print("  No student with AIR 935625 found in our data.")

print("\n=== Nearest AIRs in data (930000-940000) who got allotted ===")
cur.execute("""
    SELECT air, name, category, college_code, college_name, round
    FROM allotments
    WHERE air BETWEEN 930000 AND 940000 AND allotted = 1
    ORDER BY air
""")
for r in cur.fetchall():
    print(f"  AIR {r.air:,}  {r.name[:30]:<30}  {r.category}  [{r.college_code}] {r.college_name}  {r.round}")

conn.close()
