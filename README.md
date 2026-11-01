# broke.ly 💸 — Student Expense Analyzer

> where did my money go??

Upload a month of expenses as a CSV or messy text notes. broke.ly sorts every expense into a category, shows where your money went, spots spending patterns, and gives budget tips written for students.

**Live demo:** https://YOUR-APP-NAME.streamlit.app  ← replace after deploying

![screenshot](docs/screenshot.png)

## The problem

Students get pocket money or a stipend, and by the 20th of the month it's gone. Bank and UPI apps show a list of transactions, but not *where* the money actually went or what to change.

| | |
|---|---|
| **Who uses it** | College students tracking a monthly budget |
| **Input** | A CSV file (`Date, Description, Amount`, category optional) or plain text, one expense per line, plus an optional monthly budget |
| **Output** | Categorized expenses, totals by category, charts, spending patterns, a "spending personality", and budget suggestions |

## Features

- **Two input formats**: CSV/TSV with flexible headers (`Amount`, `Cost`, `Price (Rs)`, …) or free text like `05/10 Swiggy dinner ₹250`
- **Auto-categorization** into 9 categories (Food & Dining, Rent & Bills, Transport, Groceries, Education, Entertainment, Shopping, Health & Fitness, Personal Care) using whole-word keyword matching. Your own category column is respected if you have one.
- **Dashboard**: total spent, biggest category, daily average, budget left or over
- **Charts**: category donut, category bars, day-by-day spending
- **Patterns**: top 5 expenses, small purchases under ₹100, subscriptions, weekend share, spending spikes
- **Suggestions**: rule-based tips like the 50/30/20 split, subscription audit, food-delivery savings estimate
- **Downloads**: categorized CSV and a text report
- **Validation and error handling**: empty files, wrong file types, files over 2 MB, missing amounts, negative refunds, unreadable dates and encodings all show a friendly message instead of crashing

## Tech stack

Python · Streamlit · pandas · Plotly · pytest · deployed on Streamlit Community Cloud

## Run it locally

```bash
git clone https://github.com/P00JAGOWDAV/BROKELY-student-expense-analyzer.git
cd BROKELY-student-expense-analyzer
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Run the tests:

```bash
pip install pytest
python -m pytest -q
```

## Input examples

CSV:

```csv
Date,Description,Amount
2026-10-01,PG rent October,6500
2026-10-02,Swiggy biryani,240
2026-10-03,Uber to college,120
```

Text:

```text
01/11/2026 PG rent - ₹6500
Swiggy dinner 280
Uber to college Rs. 145
Netflix 199
```

Sample files are in [`sample_data/`](sample_data).

## Project structure

```
├── app.py               # Streamlit UI (neo-brutalist theme)
├── analyzer.py          # parsing, categorization, summary, suggestions (no UI code)
├── sample_data/         # example CSV and text inputs
├── tests/               # pytest unit tests for analyzer.py
├── docs/VIBE_CODING_LOG.md  # how the app was built with GenAI, step by step
├── requirements.txt
└── .streamlit/config.toml
```

## Built with vibe coding

This project was built iteratively with Claude as a coding partner: refining requirements, generating the structure, writing code, testing edge cases, fixing bugs and polishing the UI. The full prompt-by-prompt log is in [`docs/VIBE_CODING_LOG.md`](docs/VIBE_CODING_LOG.md).

## Future ideas

- AI-written suggestions with the Gemini or Claude API
- Month-over-month comparison
- Import directly from UPI/bank statement PDFs

## License

MIT
