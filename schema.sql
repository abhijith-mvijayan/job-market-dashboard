-- ========================================================
--  Job Market Intelligence Dashboard
--  Step 3 — MySQL Schema
-- ========================================================
--  Run this file FIRST in MySQL Workbench before running
--  the Python loader script.
--
--  Tables created:
--    jobs        →  one row per job posting (838 rows)
--    job_skills  →  one row per skill per job (for analysis)
-- ========================================================

-- Create database
CREATE DATABASE IF NOT EXISTS job_market_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE job_market_db;

-- --------------------------------------------------------
--  TABLE 1: jobs
--  The main fact table. One row = one job posting.
-- --------------------------------------------------------

DROP TABLE IF EXISTS job_skills;
DROP TABLE IF EXISTS jobs;

CREATE TABLE jobs (
    job_id        VARCHAR(20)   NOT NULL,
    job_title     VARCHAR(255)  NOT NULL,
    job_category  VARCHAR(100),
    company       VARCHAR(255),
    city          VARCHAR(100),
    experience    VARCHAR(50),
    exp_min       FLOAT,
    exp_max       FLOAT,
    exp_bucket    VARCHAR(50),
    skills        TEXT,
    skill_count   INT           DEFAULT 0,
    posted_date   VARCHAR(50),
    job_url       TEXT,
    scraped_at    DATETIME,
    PRIMARY KEY (job_id)
);

-- --------------------------------------------------------
--  TABLE 2: job_skills
--  Normalised skills table — one skill per row.
--  This is what lets you answer "how many jobs need Python?"
--  with a simple GROUP BY query.
-- --------------------------------------------------------

CREATE TABLE job_skills (
    id            INT           AUTO_INCREMENT,
    job_id        VARCHAR(20)   NOT NULL,
    skill         VARCHAR(100)  NOT NULL,
    PRIMARY KEY   (id),
    FOREIGN KEY   (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    INDEX         idx_skill (skill),
    INDEX         idx_job_id (job_id)
);
