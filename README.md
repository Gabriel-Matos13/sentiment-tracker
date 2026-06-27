# Public Utility Crisis Sentiment Tracker
### Boca Chica & Santo Domingo Este, Dominican Republic

**Live dashboard →** [gabriel-matos13.github.io/sentiment-tracker/dashboard/](https://gabriel-matos13.github.io/sentiment-tracker/dashboard/)

---

## Overview

Citizens in Boca Chica and Santo Domingo Este voice utility complaints — blackouts, water outages, waste mismanagement — primarily in the comment sections of local news and institutional social media pages, not through official government portals.

This project builds an end-to-end pipeline that ingests those comments, scores their sentiment, and renders an interactive bilingual dashboard for public viewing — at zero hosting cost.

**71% of 195 analyzed comments scored negative.** EDEESTE (electricity) and CORAABO (water) drew the most complaints. The data was collected on June 27, 2026.

---

## Pipeline Architecture

```
Instagram / Facebook public posts
        ↓
[ Apify SDK ] — comment scraper
        ↓
raw_comments.csv  (248 rows)
        ↓
[ pandas + regex ] — text cleaning
[ langdetect ]     — language filter
        ↓
[ pysentimiento ]  — Spanish transformer model
[ DR lexicon ]     — domain-specific boost
        ↓
scored_comments.csv  (195 scored, 53 excluded)
        ↓
[ Plotly-free static HTML + Chart.js + Bootstrap ]
        ↓
GitHub Pages — live bilingual dashboard
```

---

## Results

| Label | Count | % |
|-------|-------|---|
| Negative (NEG) | 139 | 71.3% |
| Neutral (NEU) | 41 | 21.0% |
| Positive (POS) | 15 | 7.7% |

- **195** comments scored after language filtering
- **53** excluded (non-Spanish, too short, or empty after cleaning)
- **80** comments boosted by the Dominican utility lexicon (41%)
- **9** source pages across Instagram and Facebook
- **4** utility categories: EDEESTE, CORAABO, ALCALDIA_BC, MEDIA

---

## Data Sources

All data is from **public** Instagram and Facebook pages. No private data, no authentication, no PII stored.

| Handle | Platform | Category |
|--------|----------|----------|
| @edeeste.rd | Instagram | EDEESTE (electricity) |
| ededeje | Facebook | EDEESTE (electricity) |
| @coraabord | Instagram | CORAABO (water) |
| coraabo.do | Facebook | CORAABO (water) |
| @alcaldiabc | Instagram | Alcaldía Boca Chica |
| AlcaldiaBC | Facebook | Alcaldía Boca Chica |
| @bocachicard04 | Instagram | Community media |
| @bocachicainformando | Instagram | Community media |
| @mediosilustradostv | Instagram | Community media |

---

## Stack

| Layer | Tools |
|-------|-------|
| Ingestion | Python, Apify SDK |
| Processing | pandas, regex, unicodedata |
| Language detection | langdetect |
| Sentiment model | pysentimiento (RoBERTuito, trained on Spanish Twitter) |
| Domain boost | Custom Dominican utility lexicon |
| Dashboard | HTML, Chart.js, PapaParse, Google Fonts |
| Hosting | GitHub Pages (zero cost) |

---

## Project Structure

```
sentiment-tracker/
├── getting the data/
│   ├── instagram_comments_scraper.py   # Apify scraper
│   └── raw_comments.csv                # gitignored
├── data processing and sentiment/
│   ├── sentiment_analyzer.py           # Cleaning + scoring pipeline
│   └── scored_comments.csv             # Model output
├── dashboard/
│   ├── index.html                      # Bilingual static dashboard
│   └── scored_comments.csv             # Copy served by GitHub Pages
├── post_urls.json                      # Target post URLs per source
├── sources.json                        # Source registry
├── .env                                # gitignored — Apify token
├── .gitignore
└── README.md
```

---

## Running Locally

**Prerequisites:** Python 3.10+, an [Apify](https://apify.com) account (free tier)

```bash
# 1. Clone and set up environment
git clone https://github.com/gabriel-matos13/sentiment-tracker.git
cd sentiment-tracker
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 2. Install dependencies
pip install apify-client pandas python-dotenv langdetect pysentimiento

# 3. Add your Apify token
echo APIFY_API_TOKEN=your_token_here > .env

# 4. Add target post URLs to post_urls.json, then scrape
python "getting the data/instagram_comments_scraper.py"

# 5. Run sentiment analysis
python "data processing and sentiment/sentiment_analyzer.py"

# 6. Copy scored CSV to dashboard and serve
copy "data processing and sentiment\scored_comments.csv" dashboard\
cd dashboard
python -m http.server 8000
# Open http://localhost:8000
```

---

## NLP Methodology

**Model:** [pysentimiento](https://github.com/pysentimiento/pysentimiento) — RoBERTuito, a RoBERTa model fine-tuned on 500M+ Spanish tweets. Outputs three class probabilities: POS, NEU, NEG.

**Dominican lexicon boost:** A custom dictionary of 30+ terms specific to DR utility complaints (`apagón`, `edeeste`, `coraabo`, `sin agua`, `maldito`, etc.) nudges the model's score by +0.15 when matched, then renormalizes. 41% of scored comments triggered at least one lexicon term.

**Language filtering:** Comments detected as non-Spanish by `langdetect` are excluded from scoring but retained in the CSV with `is_excluded = True` for auditability.

**Limitations:** The model was trained on general Spanish Twitter data, not Dominican Spanish specifically. Colloquialisms, code-switching, and heavy slang may reduce accuracy. The lexicon partially compensates for this.

---

## Ethical Notes

- Only public content is collected — no login, no private data
- Usernames are not stored in the output CSV
- This project is for research and educational purposes
- Data reflects a single point-in-time snapshot (June 2026)

---

## Author

**Gabriel Matos** — Data Analyst, Santo Domingo, Dominican Republic  
Portfolio project · Open source · June 2026
