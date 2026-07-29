"""
========================================================
  Job Market Intelligence Dashboard
  Step 3 — Load Cleaned Data into MySQL
========================================================
  INPUT  : naukri_jobs_cleaned.csv
  OUTPUT : job_market_db  (MySQL database)
           Tables: jobs, job_skills

  BEFORE RUNNING:
    1. Run schema.sql in MySQL Workbench first
    2. Fill in your MySQL password in the CONFIG block below
    3. pip install mysql-connector-python
"""

import pandas as pd
import mysql.connector
from mysql.connector import Error
import numpy as np

# ─────────────────────────────────────────────────────────
#  CONFIG  — fill in your MySQL password
# ─────────────────────────────────────────────────────────

DB_CONFIG = {
    "host"    : "localhost",
    "user"    : "root",
    "password": "root123",   
    "database": "job_market_db",
    "charset" : "utf8mb4",
}

INPUT_FILE = "naukri_jobs_cleaned.csv"

# ─────────────────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────────────────

def none_if_nan(val):
    """Convert NaN/float NaN to None so MySQL stores NULL."""
    if val is None:
        return None
    try:
        if np.isnan(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


# ─────────────────────────────────────────────────────────
#  STEP 1 — LOAD CSV
# ─────────────────────────────────────────────────────────

print("=" * 58)
print("  Step 3: MySQL Loader")
print("=" * 58)

df = pd.read_csv(INPUT_FILE)
print(f"\n[1] Loaded {len(df)} rows from {INPUT_FILE}")

# Parse scraped_at to proper datetime
df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")
df["scraped_at"] = df["scraped_at"].dt.strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────
#  STEP 2 — CONNECT TO MYSQL
# ─────────────────────────────────────────────────────────

print(f"\n[2] Connecting to MySQL at {DB_CONFIG['host']} ...")

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("    Connected successfully.")
except Error as e:
    print(f"\n ERROR: Could not connect to MySQL.\n Details: {e}")
    print("\n  Check:")
    print("   1. MySQL is running (open MySQL Workbench and verify)")
    print("   2. Your password in DB_CONFIG is correct")
    print("   3. You ran schema.sql in Workbench first")
    exit(1)


# ─────────────────────────────────────────────────────────
#  STEP 3 — INSERT INTO jobs TABLE
# ─────────────────────────────────────────────────────────

print(f"\n[3] Inserting into jobs table ...")

INSERT_JOB = """
    INSERT IGNORE INTO jobs
        (job_id, job_title, job_category, company, city,
         experience, exp_min, exp_max, exp_bucket,
         skills, skill_count, posted_date, job_url, scraped_at)
    VALUES
        (%s, %s, %s, %s, %s,
         %s, %s, %s, %s,
         %s, %s, %s, %s, %s)
"""

jobs_inserted = 0
jobs_skipped  = 0

for _, row in df.iterrows():
    values = (
        str(row["job_id"]),
        str(row["job_title"])[:255],
        none_if_nan(row.get("job_category")),
        none_if_nan(row.get("company")),
        none_if_nan(row.get("city")),
        none_if_nan(row.get("experience")),
        none_if_nan(row.get("exp_min")),
        none_if_nan(row.get("exp_max")),
        none_if_nan(row.get("exp_bucket")),
        none_if_nan(row.get("skills")),
        int(row["skill_count"]) if pd.notna(row.get("skill_count")) else 0,
        none_if_nan(row.get("posted_date")),
        str(row["job_url"])[:500] if pd.notna(row.get("job_url")) else None,
        none_if_nan(row.get("scraped_at")),
    )
    try:
        cursor.execute(INSERT_JOB, values)
        jobs_inserted += 1
    except Error as e:
        jobs_skipped += 1
        print(f"    Skipped job_id {row['job_id']}: {e}")

conn.commit()
print(f"    Inserted : {jobs_inserted} rows")
print(f"    Skipped  : {jobs_skipped} rows (duplicates or errors)")


# ─────────────────────────────────────────────────────────
#  STEP 4 — INSERT INTO job_skills TABLE
#  Explode pipe-separated skills into one row per skill
# ─────────────────────────────────────────────────────────

print(f"\n[4] Inserting into job_skills table ...")

INSERT_SKILL = """
    INSERT IGNORE INTO job_skills (job_id, skill)
    VALUES (%s, %s)
"""

skill_rows = 0

for _, row in df.iterrows():
    if pd.isna(row.get("skills")) or str(row["skills"]).strip() == "":
        continue
    job_id = str(row["job_id"])
    skill_list = [s.strip() for s in str(row["skills"]).split("|") if s.strip()]
    for skill in skill_list:
        try:
            cursor.execute(INSERT_SKILL, (job_id, skill[:100]))
            skill_rows += 1
        except Error:
            pass

conn.commit()
print(f"    Inserted : {skill_rows} skill rows")


# ─────────────────────────────────────────────────────────
#  STEP 5 — VERIFY WITH QUICK QUERIES
# ─────────────────────────────────────────────────────────

print(f"\n[5] Running verification queries ...")

queries = {
    "Total jobs"            : "SELECT COUNT(*) FROM jobs",
    "Total skill entries"   : "SELECT COUNT(*) FROM job_skills",
    "Jobs per category"     : """
        SELECT job_category, COUNT(*) AS total
        FROM jobs
        GROUP BY job_category
        ORDER BY total DESC
        LIMIT 5
    """,
    "Top 10 skills"         : """
        SELECT skill, COUNT(*) AS demand
        FROM job_skills
        GROUP BY skill
        ORDER BY demand DESC
        LIMIT 10
    """,
    "Jobs per city"         : """
        SELECT city, COUNT(*) AS total
        FROM jobs
        GROUP BY city
        ORDER BY total DESC
        LIMIT 8
    """,
    "Avg experience by category" : """
        SELECT job_category,
               ROUND(AVG(exp_min), 1) AS avg_min_exp,
               ROUND(AVG(exp_max), 1) AS avg_max_exp
        FROM jobs
        WHERE exp_min IS NOT NULL
        GROUP BY job_category
        ORDER BY avg_min_exp DESC
    """,
}

for label, sql in queries.items():
    print(f"\n  ── {label} ──")
    cursor.execute(sql)
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    print("  " + " | ".join(f"{c:<30}" for c in col_names))
    print("  " + "-" * (32 * len(col_names)))
    for r in rows:
        print("  " + " | ".join(f"{str(v):<30}" for v in r))


# ─────────────────────────────────────────────────────────
#  DONE
# ─────────────────────────────────────────────────────────

cursor.close()
conn.close()

print("\n" + "=" * 58)
print("  Step 3 complete. MySQL database is ready.")
print("  Database : job_market_db")
print("  Tables   : jobs, job_skills")
print("  Next     : Step 4 — Python EDA")
print("=" * 58)
