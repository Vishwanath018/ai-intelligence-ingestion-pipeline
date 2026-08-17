# AI Intelligence Ingestion & Entity Resolution Pipeline

A scalable, fault-tolerant data intelligence pipeline for ingesting, normalizing, enriching, and resolving information across AI startups, products, research papers, AI jobs, and AI news.

## Project Overview

This project is designed as a production-oriented data ingestion pipeline capable of collecting structured intelligence from multiple legitimate data sources.

The system focuses on:

- Asynchronous data acquisition
- Concurrent web crawling
- Structured data extraction
- Multi-tier LLM orchestration
- Intelligent payload chunking
- Rate-limit handling
- 24-hour freshness validation
- Research paper and GitHub repository correlation
- Dynamic GitHub star tracking
- Deterministic entity resolution
- Source URL traceability
- Scalable architecture for 500,000+ records

## Project Objectives

The pipeline targets six major data categories:

1. AI Startups
2. AI Products
3. AI Research Papers
4. AI Jobs
5. AI News
6. Entity Mapping

The target output includes:

- Minimum 1,000 unique startup records
- Minimum 1,000 unique product records
- Minimum 1,000 unique research paper records
- GitHub metrics for research papers where available
- AI jobs published within the previous 24 hours
- AI news published within the previous 24 hours
- Raw-to-canonical entity mapping

## System Architecture

```text
Data Sources
     |
     v
Async Crawler
     |
     v
Content Extraction
     |
     v
LLM Orchestrator
     |
     v
Schema Validation
     |
     +-------------------+
     |                   |
     v                   v
Entity Resolution   Freshness Engine
     |                   |
     +---------+---------+
               |
               v
           Storage
               |
       +-------+-------+
       |       |       |
    Startups Products Papers
       |       |       |
       +-------+-------+
               |
         Jobs / News
               |
               v
        Google Sheets
