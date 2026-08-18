# AI Intelligence Ingestion Pipeline

A Python project I built to collect and organize AI-related information from different real-world sources.

The idea behind this project is simple:

> Instead of manually checking AI startups, products, research papers, jobs, and news from different places, I wanted one pipeline that could collect, validate, connect, and store this information.

I built this mainly to learn how a real data ingestion system works when APIs fail, websites respond slowly, data is duplicated, and company names appear in different forms.

---

## What I built

The pipeline collects five types of AI information:

- AI Startups
- AI Products
- AI Research Papers
- AI Jobs
- AI News

After collecting the data, it performs validation, entity resolution, GitHub enrichment, and finally stores everything as structured JSON.

---

# Architecture

The overall flow of the project is:

```text
                    REAL-WORLD SOURCES
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
    STARTUPS           PRODUCTS           RESEARCH
        |                  |                  |
        |                  |                  |
        +------------------+------------------+
                           |
                  +--------+--------+
                  |                 |
                  v                 v
                JOBS              NEWS
                  |                 |
                  +--------+--------+
                           |
                           v
                  DATA COLLECTION
                           |
                           v
                 CLEANING + VALIDATION
                           |
                           v
                  ENTITY RESOLUTION
                           |
                           v
              GITHUB DISCOVERY / STARS
                           |
                           v
                    DATA UNIFICATION
                           |
                           v
                    OUTPUT MANAGER
                           |
                           v
              STRUCTURED JSON DATA
                           |
                           v
                    AUTOMATED TESTS