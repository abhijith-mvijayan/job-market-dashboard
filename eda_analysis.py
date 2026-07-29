"""
========================================================
  Job Market Intelligence Dashboard
  Step 4 — Exploratory Data Analysis (EDA)
========================================================
  INPUT  : naukri_jobs_cleaned.csv
  OUTPUT : /eda_charts/  (8 PNG charts for Power BI)
           eda_insights.txt  (key findings summary)

  Charts produced:
    1. Top 15 In-Demand Skills (bar chart)
    2. Jobs by City (horizontal bar)
    3. Jobs by Category (donut chart)
    4. Experience Level Distribution (bar chart)
    5. Top 15 Hiring Companies (bar chart)
    6. Skills by Job Category (heatmap)
    7. Skill Count Distribution (histogram)
    8. Avg Experience Required by Category (bar chart)
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from collections import Counter

# ─────────────────────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────────────────────

INPUT_FILE  = "naukri_jobs_cleaned.csv"
CHARTS_DIR  = "eda_charts"
INSIGHTS_FILE = "eda_insights.txt"

os.makedirs(CHARTS_DIR, exist_ok=True)

# Colour palette — consistent across all charts
PALETTE = {
    "primary"    : "#1D6FA4",
    "secondary"  : "#F5A623",
    "accent"     : "#2ECC71",
    "danger"     : "#E74C3C",
    "purple"     : "#8E44AD",
    "dark"       : "#2C3E50",
    "light_blue" : "#AED6F1",
}
CATEGORY_COLORS = [
    "#1D6FA4","#F5A623","#2ECC71","#E74C3C",
    "#8E44AD","#1ABC9C","#E67E22","#34495E","#D35400",
]

sns.set_theme(style="whitegrid", font="DejaVu Sans")
plt.rcParams.update({
    "figure.facecolor" : "white",
    "axes.facecolor"   : "#FAFBFC",
    "axes.edgecolor"   : "#CCCCCC",
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "font.size"        : 11,
})

def save(fig, filename):
    path = os.path.join(CHARTS_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"    Saved: {path}")


# ─────────────────────────────────────────────────────────
#  LOAD DATA
# ─────────────────────────────────────────────────────────

print("=" * 58)
print("  Step 4: Python EDA")
print("=" * 58)

df = pd.read_csv(INPUT_FILE)
print(f"\n[load] {len(df)} rows, {len(df.columns)} columns")

# Explode skills into one row per skill for frequency analysis
skills_exploded = (
    df["skills"]
    .dropna()
    .str.split("|")
    .explode()
    .str.strip()
    .str.title()
)
# Remove overly generic terms
SKIP_SKILLS = {"Data", "Analytical", "Analytics", "Analysis", "Science",
               "Computer Science", "Other", ""}
skills_clean = skills_exploded[~skills_exploded.isin(SKIP_SKILLS)]
skill_counts = skills_clean.value_counts()


# ─────────────────────────────────────────────────────────
#  CHART 1 — TOP 15 IN-DEMAND SKILLS
# ─────────────────────────────────────────────────────────
print("\n[1] Top 15 In-Demand Skills")

top_skills = skill_counts.head(15)

fig, ax = plt.subplots(figsize=(10, 7))
bars = ax.barh(
    top_skills.index[::-1], top_skills.values[::-1],
    color=PALETTE["primary"], edgecolor="white", height=0.65
)
for bar, val in zip(bars, top_skills.values[::-1]):
    ax.text(val + 3, bar.get_y() + bar.get_height() / 2,
            str(val), va="center", fontsize=10, color=PALETTE["dark"])

ax.set_xlabel("Number of Job Postings", fontsize=11)
ax.set_title("Top 15 Most In-Demand Skills\nAcross 838 Data/AI Job Postings",
             fontsize=14, fontweight="bold", pad=15)
ax.set_xlim(0, top_skills.max() * 1.12)
fig.tight_layout()
save(fig, "01_top_skills.png")


# ─────────────────────────────────────────────────────────
#  CHART 2 — JOBS BY CITY
# ─────────────────────────────────────────────────────────
print("[2] Jobs by City")

city_counts = df["city"].value_counts().head(10)

fig, ax = plt.subplots(figsize=(9, 5))
colors = [PALETTE["primary"] if i == 0 else PALETTE["light_blue"]
          for i in range(len(city_counts))]
bars = ax.bar(city_counts.index, city_counts.values,
              color=colors, edgecolor="white", width=0.6)
for bar, val in zip(bars, city_counts.values):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 2,
            str(val), ha="center", fontsize=10, color=PALETTE["dark"])

ax.set_ylabel("Number of Job Postings", fontsize=11)
ax.set_title("Data/AI Job Distribution by City",
             fontsize=14, fontweight="bold", pad=15)
ax.set_ylim(0, city_counts.max() * 1.12)
plt.xticks(rotation=30, ha="right")
fig.tight_layout()
save(fig, "02_jobs_by_city.png")


# ─────────────────────────────────────────────────────────
#  CHART 3 — JOBS BY CATEGORY (DONUT)
# ─────────────────────────────────────────────────────────
print("[3] Jobs by Category")

cat_counts = df["job_category"].value_counts()

fig, ax = plt.subplots(figsize=(8, 7))
wedges, texts, autotexts = ax.pie(
    cat_counts.values,
    labels=None,
    autopct="%1.1f%%",
    colors=CATEGORY_COLORS[:len(cat_counts)],
    startangle=140,
    pctdistance=0.82,
    wedgeprops={"width": 0.55, "edgecolor": "white", "linewidth": 2},
)
for autotext in autotexts:
    autotext.set_fontsize(9)
    autotext.set_color("white")
    autotext.set_fontweight("bold")

legend_labels = [f"{cat}  ({cnt})" for cat, cnt in zip(cat_counts.index, cat_counts.values)]
ax.legend(wedges, legend_labels, loc="lower center",
          bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9,
          frameon=False)
ax.set_title("Job Postings by Role Category",
             fontsize=14, fontweight="bold", pad=15)
fig.tight_layout()
save(fig, "03_jobs_by_category.png")


# ─────────────────────────────────────────────────────────
#  CHART 4 — EXPERIENCE LEVEL DISTRIBUTION
# ─────────────────────────────────────────────────────────
print("[4] Experience Distribution")

bucket_order = [
    "0-2 Years (Fresher)",
    "3-5 Years (Mid)",
    "6-10 Years (Senior)",
    "10+ Years (Lead/Principal)",
    "Not Specified",
]
exp_counts = df["exp_bucket"].value_counts().reindex(bucket_order).dropna()
exp_colors = [PALETTE["accent"], PALETTE["primary"],
              PALETTE["secondary"], PALETTE["danger"], "#BDC3C7"]

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(range(len(exp_counts)), exp_counts.values,
              color=exp_colors[:len(exp_counts)], edgecolor="white", width=0.55)
for bar, val in zip(bars, exp_counts.values):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 3,
            str(val), ha="center", fontsize=10, color=PALETTE["dark"])

ax.set_xticks(range(len(exp_counts)))
ax.set_xticklabels(exp_counts.index, rotation=20, ha="right", fontsize=10)
ax.set_ylabel("Number of Job Postings", fontsize=11)
ax.set_title("Experience Level Distribution",
             fontsize=14, fontweight="bold", pad=15)
ax.set_ylim(0, exp_counts.max() * 1.12)
fig.tight_layout()
save(fig, "04_experience_distribution.png")


# ─────────────────────────────────────────────────────────
#  CHART 5 — TOP 15 HIRING COMPANIES
# ─────────────────────────────────────────────────────────
print("[5] Top 15 Hiring Companies")

top_companies = df["company"].value_counts().head(15)

fig, ax = plt.subplots(figsize=(10, 7))
bars = ax.barh(
    top_companies.index[::-1], top_companies.values[::-1],
    color=PALETTE["secondary"], edgecolor="white", height=0.65
)
for bar, val in zip(bars, top_companies.values[::-1]):
    ax.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
            str(val), va="center", fontsize=10, color=PALETTE["dark"])

ax.set_xlabel("Number of Job Postings", fontsize=11)
ax.set_title("Top 15 Hiring Companies in Data/AI",
             fontsize=14, fontweight="bold", pad=15)
ax.set_xlim(0, top_companies.max() * 1.15)
fig.tight_layout()
save(fig, "05_top_companies.png")


# ─────────────────────────────────────────────────────────
#  CHART 6 — SKILLS HEATMAP BY JOB CATEGORY
# ─────────────────────────────────────────────────────────
print("[6] Skills Heatmap by Category")

TOP_SKILLS_FOR_HEATMAP = [
    "Python", "Machine Learning", "Sql", "Deep Learning",
    "Nlp", "Tensorflow", "Pytorch", "Spark", "Aws",
    "Power Bi", "Tableau", "Data Engineering",
    "Statistics", "Feature Engineering",
]
TOP_CATS = [c for c in df["job_category"].value_counts().index
            if c != "Other"][:8]

heatmap_data = pd.DataFrame(0.0, index=TOP_CATS, columns=TOP_SKILLS_FOR_HEATMAP, dtype=float)

for _, row in df.iterrows():
    if pd.isna(row["skills"]) or row["job_category"] not in TOP_CATS:
        continue
    row_skills = {s.strip().title() for s in str(row["skills"]).split("|")}
    for skill in TOP_SKILLS_FOR_HEATMAP:
        if skill in row_skills:
            heatmap_data.loc[row["job_category"], skill] += 1

# Normalise each row to % of that category's total jobs
cat_totals = df[df["job_category"].isin(TOP_CATS)]["job_category"].value_counts()
for cat in TOP_CATS:
    if cat in cat_totals and cat_totals[cat] > 0:
        heatmap_data.loc[cat] = (heatmap_data.loc[cat] / cat_totals[cat] * 100).round(1)

fig, ax = plt.subplots(figsize=(13, 6))
sns.heatmap(
    heatmap_data,
    annot=True, fmt=".0f", cmap="Blues",
    linewidths=0.5, linecolor="#EEEEEE",
    ax=ax, cbar_kws={"label": "% of jobs in category requiring this skill"},
)
ax.set_title("Skill Demand by Job Category  (% of jobs requiring each skill)",
             fontsize=13, fontweight="bold", pad=15)
ax.set_xlabel("")
ax.set_ylabel("")
plt.xticks(rotation=35, ha="right", fontsize=10)
plt.yticks(rotation=0, fontsize=10)
fig.tight_layout()
save(fig, "06_skills_heatmap.png")


# ─────────────────────────────────────────────────────────
#  CHART 7 — SKILL COUNT DISTRIBUTION
# ─────────────────────────────────────────────────────────
print("[7] Skill Count Distribution")

fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(df["skill_count"].dropna(), bins=range(0, 20),
        color=PALETTE["purple"], edgecolor="white", alpha=0.85)
ax.axvline(df["skill_count"].median(), color=PALETTE["danger"],
           linestyle="--", linewidth=2, label=f"Median = {df['skill_count'].median():.0f}")
ax.set_xlabel("Number of Skills Listed per Job Posting", fontsize=11)
ax.set_ylabel("Number of Job Postings", fontsize=11)
ax.set_title("How Many Skills Do Companies Ask For?",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(fontsize=11)
fig.tight_layout()
save(fig, "07_skill_count_distribution.png")


# ─────────────────────────────────────────────────────────
#  CHART 8 — AVG EXPERIENCE BY CATEGORY
# ─────────────────────────────────────────────────────────
print("[8] Avg Experience by Category")

exp_by_cat = (
    df[df["job_category"] != "Other"]
    .groupby("job_category")[["exp_min", "exp_max"]]
    .mean()
    .round(1)
    .sort_values("exp_min", ascending=True)
)

fig, ax = plt.subplots(figsize=(9, 6))
y = range(len(exp_by_cat))
ax.barh(y, exp_by_cat["exp_max"] - exp_by_cat["exp_min"],
        left=exp_by_cat["exp_min"],
        color=PALETTE["primary"], alpha=0.75,
        edgecolor="white", height=0.55, label="Experience range")
ax.scatter(exp_by_cat["exp_min"], y, color=PALETTE["accent"],
           zorder=5, s=60, label="Min experience")
ax.scatter(exp_by_cat["exp_max"], y, color=PALETTE["danger"],
           zorder=5, s=60, label="Max experience")

for i, (_, row) in enumerate(exp_by_cat.iterrows()):
    ax.text(row["exp_min"] - 0.3, i, f'{row["exp_min"]:.1f}',
            ha="right", va="center", fontsize=9, color=PALETTE["dark"])
    ax.text(row["exp_max"] + 0.2, i, f'{row["exp_max"]:.1f}',
            ha="left", va="center", fontsize=9, color=PALETTE["dark"])

ax.set_yticks(list(y))
ax.set_yticklabels(exp_by_cat.index, fontsize=10)
ax.set_xlabel("Years of Experience", fontsize=11)
ax.set_title("Experience Required by Job Category\n(Average min–max years)",
             fontsize=14, fontweight="bold", pad=15)
ax.legend(fontsize=10, loc="lower right")
fig.tight_layout()
save(fig, "08_experience_by_category.png")


# ─────────────────────────────────────────────────────────
#  INSIGHTS SUMMARY
# ─────────────────────────────────────────────────────────

insights = f"""
============================================================
  JOB MARKET INTELLIGENCE — KEY INSIGHTS
  Data: {len(df)} Naukri.com postings, scraped June 2026
============================================================

TOP 5 MOST IN-DEMAND SKILLS
  1. Machine Learning  — {skill_counts.get('Machine Learning', 0)} jobs
  2. Python            — {skill_counts.get('Python', 0)} jobs
  3. SQL               — {skill_counts.get('Sql', skill_counts.get('SQL', 0))} jobs
  4. NLP               — {skill_counts.get('Nlp', skill_counts.get('NLP', 0))} jobs
  5. Deep Learning     — {skill_counts.get('Deep Learning', 0)} jobs

TOP 3 HIRING CITIES
  1. {df['city'].value_counts().index[0]}  ({df['city'].value_counts().iloc[0]} jobs)
  2. {df['city'].value_counts().index[1]}  ({df['city'].value_counts().iloc[1]} jobs)
  3. {df['city'].value_counts().index[2]}  ({df['city'].value_counts().iloc[2]} jobs)

TOP 3 JOB CATEGORIES
  1. {df['job_category'].value_counts().index[0]}  ({df['job_category'].value_counts().iloc[0]} jobs)
  2. {df['job_category'].value_counts().index[1]}  ({df['job_category'].value_counts().iloc[1]} jobs)
  3. {df['job_category'].value_counts().index[2]}  ({df['job_category'].value_counts().iloc[2]} jobs)

EXPERIENCE INSIGHTS
  Most jobs require  : {df['exp_bucket'].value_counts().index[0]}
  Avg min experience : {df['exp_min'].mean():.1f} years
  Avg max experience : {df['exp_max'].mean():.1f} years
  Toughest role      : Data Engineer ({exp_by_cat['exp_min'].idxmax()})

SKILL DEPTH
  Avg skills per job : {df['skill_count'].mean():.1f}
  Median skills/job  : {df['skill_count'].median():.0f}
  Most skills in one posting: {int(df['skill_count'].max())}

TOP 5 HIRING COMPANIES
{chr(10).join(f'  {i+1}. {co}  ({cnt} jobs)' for i, (co, cnt) in enumerate(df['company'].value_counts().head(5).items()))}

============================================================
"""

with open(INSIGHTS_FILE, "w", encoding="utf-8") as f:
    f.write(insights)

print(insights)

print("=" * 58)
print(f"  All 8 charts saved to /{CHARTS_DIR}/")
print(f"  Insights saved to {INSIGHTS_FILE}")
print("  Step 4 complete. Ready for Step 5 — Power BI Dashboard.")
print("=" * 58)
