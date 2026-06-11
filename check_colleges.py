import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLEXPRESS;"
    "DATABASE=neet_counsellor;Trusted_Connection=yes;"
)
cur = conn.cursor()

cur.execute("""
SELECT
    sm.section,
    COUNT(DISTINCT a.college_code) AS unique_colleges
FROM allotments a
JOIN seat_matrix sm
    ON sm.college_code = a.college_code
    AND sm.round = 'R1'
    AND sm.row_type = 'GEN'
    AND sm.year = 2025
GROUP BY sm.section
ORDER BY sm.section
""")
print("By section:")
total = 0
for r in cur.fetchall():
    print(f"  {r.section:<15} {r.unique_colleges}")
    total += r.unique_colleges
print(f"  {'TOTAL':<15} {total}")

cur.execute("SELECT COUNT(DISTINCT college_code) AS n FROM allotments WHERE allotted=1")
print(f"\nTotal unique colleges with at least 1 allotment: {cur.fetchone().n}")

cur.execute("SELECT COUNT(DISTINCT college_code) AS n FROM seat_matrix WHERE round='R1' AND year=2025")
print(f"Total unique colleges in seat matrix (R1):      {cur.fetchone().n}")
conn.close()
