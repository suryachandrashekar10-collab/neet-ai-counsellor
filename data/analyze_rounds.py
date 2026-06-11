"""Analyze round-wise cutoff movement to inform the prediction model."""
import pyodbc

SQL_SERVER = r"localhost\SQLEXPRESS"
DB_NAME    = "neet_counsellor"

def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={DB_NAME};"
        f"Trusted_Connection=yes;"
    )

conn = get_conn()
cur  = conn.cursor()

print("=== Round-wise closing rank movement for top colleges (OPEN category) ===\n")
cur.execute("""
    SELECT college_code, college_name, round, MIN(closing_rank) as closing_rank, SUM(seats_filled) as seats
    FROM cutoffs
    WHERE category = 'OPEN' AND women_quota = 0 AND year = 2025
      AND college_code IN ('1103','1104','1110','1101','1221','1102','1163','1327')
    GROUP BY college_code, college_name, round
    ORDER BY college_code, round
""")
rows = cur.fetchall()
from collections import defaultdict
college_rounds = defaultdict(dict)
for r in rows:
    college_rounds[r.college_code][r.round] = (r.closing_rank, r.seats, r.college_name)

for code, rounds in sorted(college_rounds.items()):
    name = list(rounds.values())[0][2]
    print(f"{code} {name}")
    for rnd in ['R1','R2','R3','R4','R5']:
        if rnd in rounds:
            cr, seats, _ = rounds[rnd]
            print(f"  {rnd}: closing={cr:7,}  seats={seats}")
    print()

print("\n=== OBC category round movement ===\n")
cur.execute("""
    SELECT college_code, college_name, round, MIN(closing_rank) as closing_rank, SUM(seats_filled) as seats
    FROM cutoffs
    WHERE category = 'OBC' AND women_quota = 0 AND year = 2025
      AND college_code IN ('1103','1104','1110','1101','1221','1102','1163','1327')
    GROUP BY college_code, college_name, round
    ORDER BY college_code, round
""")
rows = cur.fetchall()
college_rounds = defaultdict(dict)
for r in rows:
    college_rounds[r.college_code][r.round] = (r.closing_rank, r.seats, r.college_name)

for code, rounds in sorted(college_rounds.items()):
    name = list(rounds.values())[0][2]
    print(f"{code} {name}")
    for rnd in ['R1','R2','R3','R4','R5']:
        if rnd in rounds:
            cr, seats, _ = rounds[rnd]
            prev = rounds.get({'R2':'R1','R3':'R2','R4':'R3'}.get(rnd,''), (None,None,None))[0]
            movement = ""
            if prev:
                diff = cr - prev
                movement = f"  (+{diff:,} opened)" if diff > 0 else f"  ({diff:,} tightened)"
            print(f"  {rnd}: closing={cr:7,}  seats={seats}{movement}")
    print()

print("\n=== How many colleges have data for all 4 rounds? ===")
cur.execute("""
    SELECT COUNT(DISTINCT college_code) as colleges, COUNT(DISTINCT round) as rounds
    FROM cutoffs WHERE category='OPEN' AND women_quota=0 AND year=2025
""")
r = cur.fetchone()
print(f"  Total unique colleges: {r.colleges}, rounds: {r.rounds}")

cur.execute("""
    SELECT round_count, COUNT(*) as colleges FROM (
        SELECT college_code, COUNT(DISTINCT round) as round_count
        FROM cutoffs WHERE category='OPEN' AND women_quota=0 AND year=2025
        GROUP BY college_code
    ) x GROUP BY round_count ORDER BY round_count
""")
for r in cur.fetchall():
    print(f"  Colleges with {r.round_count} round(s) of data: {r.colleges}")

conn.close()
