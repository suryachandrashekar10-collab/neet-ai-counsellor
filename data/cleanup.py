import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=neet_counsellor;Trusted_Connection=yes;",
    autocommit=True
)
cur = conn.cursor()

# Remove (Ret.), (No Change) etc. from college names
for table in ["allotments", "cutoffs"]:
    cur.execute(f"UPDATE {table} SET college_name = REPLACE(college_name, '(Ret.)', '')")
    cur.execute(f"UPDATE {table} SET college_name = REPLACE(college_name, '(No Change)', '')")
    cur.execute(f"UPDATE {table} SET college_name = RTRIM(college_name)")

# Show sample
print("Sample college names after cleanup:")
for row in cur.execute("SELECT DISTINCT college_code, college_name FROM cutoffs WHERE round='R1' ORDER BY college_code"):
    print(f"  {row.college_code}  {row.college_name}")

conn.close()
print("Done")
