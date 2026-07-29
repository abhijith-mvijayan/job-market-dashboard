"""
========================================================
  Job Market Intelligence Dashboard
  Step 2 — Data Cleaning Pipeline
========================================================
  INPUT  : naukri_jobs_raw.csv        (844 rows, 11 cols)
  OUTPUT : naukri_jobs_cleaned.csv    (clean, analysis-ready)

  What this script does:
    1. Drop columns that are 100% empty (salary, job_type)
    2. Handle missing values
    3. Standardise location / city names
    4. Parse experience strings  →  exp_min, exp_max (integers)
    5. Create experience buckets  →  exp_bucket
    6. Normalise and expand skills
    7. Fill null skills by extracting keywords from job titles
    8. Create job_category from job title
    9. Save final cleaned CSV + print a summary report
"""

import re
import ast
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────

INPUT_FILE  = "naukri_jobs_raw.csv"
OUTPUT_FILE = "naukri_jobs_cleaned.csv"

# ─────────────────────────────────────────────────────────
#  STEP 1 — LOAD
# ─────────────────────────────────────────────────────────

print("=" * 58)
print("  Step 2: Data Cleaning Pipeline")
print("=" * 58)

df = pd.read_csv(INPUT_FILE)
print(f"\n[1] Loaded raw data  →  {df.shape[0]} rows, {df.shape[1]} columns")


# ─────────────────────────────────────────────────────────
#  STEP 2 — DROP USELESS COLUMNS
# ─────────────────────────────────────────────────────────
# salary and job_type are 100% null — they carry zero information.
# Keeping them would just create confusion in Power BI.

cols_to_drop = [col for col in ["salary", "job_type"] if col in df.columns]
df.drop(columns=cols_to_drop, inplace=True)

print(f"\n[2] Dropped empty columns: {cols_to_drop}")
print(f"    Remaining columns: {list(df.columns)}")


# ─────────────────────────────────────────────────────────
#  STEP 3 — HANDLE MISSING VALUES
# ─────────────────────────────────────────────────────────

before = len(df)

# Rows with no company name (only 1) — fill with "Unknown Company"
df["company"] = df["company"].fillna("Unknown Company").str.strip()

# Rows with no location (6) — drop them; location is key for analysis
df = df.dropna(subset=["location"])

# Rows with no experience (11) — fill with "Not Specified"
df["experience"] = df["experience"].fillna("Not Specified").str.strip()

# Rows with no posted_date (1) — fill with "Unknown"
df["posted_date"] = df["posted_date"].fillna("Unknown").str.strip()

after = len(df)
print(f"\n[3] Handled missing values  →  dropped {before - after} rows with no location")
print(f"    Rows remaining: {after}")


# ─────────────────────────────────────────────────────────
#  STEP 4 — STANDARDISE LOCATION / CITY NAMES
# ─────────────────────────────────────────────────────────
# Naukri uses slightly different spellings for the same city.
# We map everything to one clean standard name.

CITY_MAP = {
    # Bangalore variants
    "bengaluru"   : "Bangalore",
    "bangalore"   : "Bangalore",
    "banglore"    : "Bangalore",
    # Hyderabad
    "hyderabad"   : "Hyderabad",
    # Pune
    "pune"        : "Pune",
    # Mumbai
    "mumbai"      : "Mumbai",
    "bombay"      : "Mumbai",
    # Delhi NCR
    "delhi"       : "Delhi",
    "new delhi"   : "Delhi",
    "noida"       : "Noida",
    "gurgaon"     : "Gurgaon",
    "gurugram"    : "Gurgaon",
    # Chennai
    "chennai"     : "Chennai",
    "madras"      : "Chennai",
    # Kolkata
    "kolkata"     : "Kolkata",
    "calcutta"    : "Kolkata",
}

def standardise_city(raw: str) -> str:
    if pd.isna(raw):
        return "Other"
    city = raw.strip()
    # Strip "Hybrid - " prefix
    city = re.sub(r"(?i)^hybrid\s*[-–]\s*", "", city)
    # Take first city if comma-separated or slash-separated
    city = re.split(r"[,/]", city)[0].strip()
    # Remove sub-area in brackets e.g. "Mumbai(Andheri East)"
    city = re.sub(r"\s*\(.*\)", "", city).strip()
    # Remove "(All Areas)" suffix
    city = city.replace("(All Areas)", "").strip()
    return CITY_MAP.get(city.lower(), city.title())

df["city"] = df["location"].apply(standardise_city)

print(f"\n[4] Standardised city names")
print(f"    City distribution:\n{df['city'].value_counts().to_string()}")


# ─────────────────────────────────────────────────────────
#  STEP 5 — PARSE EXPERIENCE  →  exp_min, exp_max, exp_bucket
# ─────────────────────────────────────────────────────────
# Raw format examples:
#   "7-10 Yrs"   →  min=7,  max=10
#   "10-15 Yrs"  →  min=10, max=15
#   "0-1 Yrs"    →  min=0,  max=1
#   "Not Specified" → min=NaN, max=NaN

def parse_experience(raw: str):
    """
    Returns (exp_min, exp_max) as integers.
    Returns (NaN, NaN) when experience is not available or unparseable.
    """
    if pd.isna(raw) or raw.strip().lower() in ("not specified", ""):
        return np.nan, np.nan

    # Match patterns like "3-7", "10-15", "0-1"
    match = re.search(r"(\d+)\s*[-–]\s*(\d+)", raw)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Match single number like "5 Yrs" or "5+ Yrs"
    match = re.search(r"(\d+)\s*\+?", raw)
    if match:
        val = int(match.group(1))
        return val, val

    return np.nan, np.nan


results = df["experience"].apply(parse_experience)
df["exp_min"] = results.apply(lambda x: x[0])
df["exp_max"] = results.apply(lambda x: x[1])


def exp_bucket(min_val):
    """
    Group experience into buckets for charts in Power BI.
    """
    if pd.isna(min_val):
        return "Not Specified"
    elif min_val <= 2:
        return "0-2 Years (Fresher)"
    elif min_val <= 5:
        return "3-5 Years (Mid)"
    elif min_val <= 10:
        return "6-10 Years (Senior)"
    else:
        return "10+ Years (Lead/Principal)"


df["exp_bucket"] = df["exp_min"].apply(exp_bucket)

print(f"\n[5] Parsed experience into numeric columns + buckets")
print(f"    exp_min range: {df['exp_min'].min():.0f} – {df['exp_min'].max():.0f} years")
print(f"    Experience bucket distribution:")
print(f"{df['exp_bucket'].value_counts().to_string()}")


# ─────────────────────────────────────────────────────────
#  STEP 6 — CLEAN AND NORMALISE SKILLS
# ─────────────────────────────────────────────────────────
# Raw format: "Computer science | Data analysis | data science | Python"
# We normalise each skill: strip whitespace, title-case, deduplicate.

# Master skill normalisation map — maps raw strings to clean names
SKILL_NORM = {
    # Python ecosystem
    "python"              : "Python",
    "python 3"            : "Python",
    "core python"         : "Python",
    "python programming"  : "Python",
    # SQL / databases
    "sql"                 : "SQL",
    "mysql"               : "MySQL",
    "postgresql"          : "PostgreSQL",
    "postgres"            : "PostgreSQL",
    "nosql"               : "NoSQL",
    "mongodb"             : "MongoDB",
    # ML / DL frameworks
    "machine learning"    : "Machine Learning",
    "ml"                  : "Machine Learning",
    "deep learning"       : "Deep Learning",
    "dl"                  : "Deep Learning",
    "tensorflow"          : "TensorFlow",
    "tensor flow"         : "TensorFlow",
    "pytorch"             : "PyTorch",
    "keras"               : "Keras",
    "scikit-learn"        : "Scikit-learn",
    "sklearn"             : "Scikit-learn",
    "scikit learn"        : "Scikit-learn",
    # Data / analytics
    "data science"        : "Data Science",
    "data analysis"       : "Data Analysis",
    "data analytics"      : "Data Analytics",
    "data engineering"    : "Data Engineering",
    "data visualization"  : "Data Visualization",
    "data visualisation"  : "Data Visualization",
    "data wrangling"      : "Data Wrangling",
    "data modelling"      : "Data Modeling",
    "data modeling"       : "Data Modeling",
    "statistical analysis": "Statistics",
    "statistics"          : "Statistics",
    "statistical modeling": "Statistics",
    # NLP
    "nlp"                 : "NLP",
    "natural language processing" : "NLP",
    "text mining"         : "NLP",
    # Computer Vision
    "computer vision"     : "Computer Vision",
    "cv"                  : "Computer Vision",
    "image processing"    : "Computer Vision",
    # Big Data
    "apache spark"        : "Spark",
    "spark"               : "Spark",
    "pyspark"             : "PySpark",
    "hadoop"              : "Hadoop",
    "hive"                : "Hive",
    "kafka"               : "Kafka",
    # Cloud
    "aws"                 : "AWS",
    "amazon web services" : "AWS",
    "azure"               : "Azure",
    "microsoft azure"     : "Azure",
    "gcp"                 : "GCP",
    "google cloud"        : "GCP",
    # BI Tools
    "power bi"            : "Power BI",
    "powerbi"             : "Power BI",
    "tableau"             : "Tableau",
    "looker"              : "Looker",
    # Other common tools
    "git"                 : "Git",
    "github"              : "Git",
    "docker"              : "Docker",
    "kubernetes"          : "Kubernetes",
    "airflow"             : "Airflow",
    "excel"               : "Excel",
    "r"                   : "R",
    "computer science"    : "Computer Science",
    "llm"                 : "LLMs",
    "large language model": "LLMs",
    "generative ai"       : "Generative AI",
    "gen ai"              : "Generative AI",
    "langchain"           : "LangChain",
    "rag"                 : "RAG",
    "mlops"               : "MLOps",
    "feature engineering" : "Feature Engineering",
    "a/b testing"         : "A/B Testing",
}


def clean_skills(raw):
    """
    Split the pipe-separated skills string, normalise each skill,
    remove duplicates, return a clean pipe-separated string.
    """
    if pd.isna(raw) or str(raw).strip() == "":
        return np.nan

    parts = [s.strip() for s in str(raw).split("|") if s.strip()]
    normalised = []
    seen = set()

    for part in parts:
        key = part.lower().strip()
        clean = SKILL_NORM.get(key, part.strip().title())
        # Deduplicate
        if clean.lower() not in seen:
            seen.add(clean.lower())
            normalised.append(clean)

    return " | ".join(normalised) if normalised else np.nan


df["skills_clean"] = df["skills"].apply(clean_skills)

print(f"\n[6] Normalised skills column")
print(f"    Rows with skills: {df['skills_clean'].notna().sum()} / {len(df)}")


# ─────────────────────────────────────────────────────────
#  STEP 7 — FILL NULL SKILLS FROM JOB TITLE
# ─────────────────────────────────────────────────────────
# For the 33 rows where skills_clean is still NaN, we scan
# the job title for known technology keywords and use those.

TITLE_SKILL_KEYWORDS = [
    "Python", "SQL", "R", "Java", "Scala",
    "Machine Learning", "Deep Learning", "NLP",
    "Computer Vision", "TensorFlow", "PyTorch",
    "Spark", "PySpark", "Hadoop", "Kafka",
    "AWS", "Azure", "GCP", "Power BI", "Tableau",
    "Generative AI", "LLMs", "MLOps", "LangChain",
    "Data Engineering", "Data Science", "Data Analysis",
    "BI", "Analytics",
]


def extract_skills_from_title(title: str) -> str:
    """
    Scan job title for skill keywords and return them pipe-separated.
    """
    if pd.isna(title):
        return np.nan
    found = []
    title_lower = title.lower()
    for kw in TITLE_SKILL_KEYWORDS:
        if kw.lower() in title_lower:
            found.append(kw)
    return " | ".join(found) if found else np.nan


null_skill_mask = df["skills_clean"].isna()
df.loc[null_skill_mask, "skills_clean"] = df.loc[null_skill_mask, "job_title"].apply(
    extract_skills_from_title
)

still_null = df["skills_clean"].isna().sum()
print(f"\n[7] Filled null skills from job titles")
print(f"    Rows still without any skills: {still_null}")


# ─────────────────────────────────────────────────────────
#  STEP 8 — CREATE JOB CATEGORY FROM JOB TITLE
# ─────────────────────────────────────────────────────────
# Map each job title to one of 8 clean role categories.
# Order matters — more specific rules go first.

CATEGORY_RULES = [
    ("NLP Engineer",            ["nlp", "natural language", "text mining", "computational linguistics"]),
    ("Deep Learning Engineer",  ["deep learning", "computer vision", "cnn", "image recognition"]),
    ("ML Engineer",             ["machine learning engineer", "ml engineer", "mlops", "ml ops"]),
    ("AI Engineer",             ["ai engineer", "artificial intelligence engineer", "genai", "generative ai", "llm"]),
    ("Data Engineer",           ["data engineer", "etl", "pipeline", "spark", "hadoop", "databricks"]),
    ("BI Analyst",              ["business intelligence", "bi analyst", "bi developer", "power bi", "tableau developer"]),
    ("Data Analyst",            ["data analyst", "business analyst", "analytics analyst", "reporting analyst"]),
    ("Data Scientist",          ["data scientist", "data science", "ml", "ai", "machine learning", "research scientist"]),
]


def categorise_job(title: str) -> str:
    if pd.isna(title):
        return "Other"
    title_lower = title.lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in title_lower for kw in keywords):
            return category
    return "Other"


df["job_category"] = df["job_title"].apply(categorise_job)

print(f"\n[8] Created job_category column")
print(f"    Category distribution:")
print(f"{df['job_category'].value_counts().to_string()}")


# ─────────────────────────────────────────────────────────
#  STEP 9 — ADD SKILL COUNT COLUMN
# ─────────────────────────────────────────────────────────
# Useful for Power BI visuals — how many skills does a
# typical job posting require?

df["skill_count"] = df["skills_clean"].apply(
    lambda x: len(str(x).split("|")) if pd.notna(x) else 0
)


# ─────────────────────────────────────────────────────────
#  STEP 10 — FINAL COLUMN SELECTION AND ORDERING
# ─────────────────────────────────────────────────────────
# Drop the original messy columns now that we have clean ones.
# Keep only what is needed for SQL loading and Power BI.

FINAL_COLUMNS = [
    "job_id",
    "job_title",
    "job_category",
    "company",
    "city",
    "experience",
    "exp_min",
    "exp_max",
    "exp_bucket",
    "skills_clean",
    "skill_count",
    "posted_date",
    "job_url",
    "scraped_at",
]

df_final = df[FINAL_COLUMNS].copy()

# Rename skills_clean → skills for clarity downstream
df_final.rename(columns={"skills_clean": "skills"}, inplace=True)

print(f"\n[9] Final column selection: {list(df_final.columns)}")


# ─────────────────────────────────────────────────────────
#  STEP 11 — SAVE
# ─────────────────────────────────────────────────────────

df_final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print(f"\n[10] Saved cleaned data  →  {OUTPUT_FILE}")
print(f"     Final shape: {df_final.shape[0]} rows × {df_final.shape[1]} columns")


# ─────────────────────────────────────────────────────────
#  SUMMARY REPORT
# ─────────────────────────────────────────────────────────

print("\n" + "=" * 58)
print("  CLEANING SUMMARY")
print("=" * 58)
print(f"  Raw rows        : 844")
print(f"  Clean rows      : {len(df_final)}")
print(f"  Columns kept    : {len(df_final.columns)}")
print(f"  Nulls remaining :")
print(df_final.isnull().sum()[df_final.isnull().sum() > 0].to_string())
print("\n  Sample of cleaned data:")
print(df_final[["job_title", "job_category", "company", "city",
                "exp_bucket", "skill_count"]].head(5).to_string())
print("=" * 58)
print("  Step 2 complete. Ready for Step 3 (SQL loading).")
print("=" * 58)