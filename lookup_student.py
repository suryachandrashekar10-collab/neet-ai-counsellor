import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLEXPRESS;"
    "DATABASE=neet_counsellor;Trusted_Connection=yes;"
)
cur = conn.cursor()

cur.execute("""
    SELECT
        sr_no, air, neet_roll, cet_form, name, gender,
        category, quota, women_quota, college_code, college_name,
        round, year, allotted
    FROM allotments
    WHERE neet_roll = '3130105229'
       OR cet_form  = '256004732'
       OR name LIKE '%MOINUDDIN%'
    ORDER BY round
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"Round:    {r.round}")
        print(f"Name:     {r.name}")
        print(f"AIR:      {r.air}")
        print(f"NEET Roll:{r.neet_roll}  CET Form:{r.cet_form}")
        print(f"Category: {r.category}  Quota:{r.quota}  Women:{r.women_quota}")
        print(f"College:  [{r.college_code}] {r.college_name}")
        print(f"Allotted: {r.allotted}")
        print("-" * 50)
else:
    print("No records found.")
conn.close()
