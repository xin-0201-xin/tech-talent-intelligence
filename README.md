# 🚀 Tech Talent Intelligence: North American IT Job Market Analysis

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Data_Engineering-Pandas-green.svg)](https://pandas.pydata.org/)
[![Tableau](https://img.shields.io/badge/Data_Visualization-Tableau-orange.svg)](https://public.tableau.com/)

## 🔗 Live Dashboard
**👉 [Click here to view the Interactive Tableau Dashboard](https://public.tableau.com/views/Tech_Talent_Intelligence_Dashboard/Dashboard?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)**

## 📌 Project Overview
This project is an end-to-end data analytics pipeline designed to benchmark the I&IT (Information & Information Technology) job market across North America. By scraping, cleaning, and visualizing over 1,000 real-time job postings, this project provides actionable intelligence on compensation distributions, geographic talent clusters, and highly sought-after technical skills.

![Dashboard Preview](images/dashboard_preview.png) *(Note: Please upload your Tableau screenshot to the images folder!)*

## 🛠️ Tech Stack & Methodology
1. **Data Extraction (Web Scraping):** Harvested job postings (titles, locations, salaries, descriptions) across US and Canadian tech hubs.
2. **Data Engineering (Python / Pandas / RegEx):**
   - **Salary Normalization:** Programmatically converted hourly/monthly wages into standardized Annual Salaries using Regular Expressions.
   - **Geospatial Processing:** Cleaned unstructured text (e.g., removing "Hybrid/Remote", extracting core cities).
   - **Feature Extraction (NLP):** Scanned unstructured job descriptions to extract 17 key technical skills (SQL, Python, AWS, etc.) into structured binary features.
3. **Data Visualization (Tableau):** Designed a high-contrast, cyberpunk-themed BI dashboard focusing on macro (geographic) and micro (seniority/skill) trends.

## 📊 Key Business Insights
- **The Outlier Effect:** While Junior/Mid-level salaries are concentrated, Senior and Management roles exhibit massive variance with exceptionally high-paying outliers in the private sector.
- **Top Tech Stack:** **SQL, Python, and Cloud technologies (AWS/Azure)** dominate the current market demand, serving as a benchmark for technical recruiting and upskilling.
- **Geographic Gravity:** Ontario (GTA) remains a massive center of gravity for IT jobs, rivaling major US tech hubs.

## 📂 Repository Structure
- `/data`: Contains samples of the raw extracted data and the final cleaned dataset.
- `/scripts`: Python scripts for data cleaning, Regex transformations, and feature engineering.
- `/images`: Screenshots used for documentation.