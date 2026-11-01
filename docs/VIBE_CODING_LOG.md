# Vibe coding log

How broke.ly was built with GenAI (Claude) as a coding partner, one step at a time instead of one giant prompt. Each step ended with testing, and the issues found fed the next prompt.

## Step 1 — Understand the requirement

**Prompt (summary):** Here's my problem statement and project rules. Suggest free tools, design options, and help me plan.

**Requirement analysis**

| Question | Answer |
|---|---|
| Problem | Students lose track of where their monthly money goes |
| Users | College students on a fixed monthly budget |
| Inputs | CSV or text expenses, optional monthly budget |
| Outputs | Categories, major expense areas, spending patterns, suggestions |
| Core features | Upload/paste, parse, categorize, summarize, chart, suggest, validate |

**Decisions:** Python + Streamlit (free hosting on Streamlit Community Cloud, gives a public URL for the QR code), pandas for data, Plotly for charts. Design style chosen from four previews: neo-brutalist pop.

## Step 2 — Generate the structure

Split the app into two files so the logic could be tested without the UI:

- `analyzer.py`: parse → categorize → summarize → suggest
- `app.py`: Streamlit UI only

## Step 3 — Generate the analysis engine + tests

**Prompt:** Write a parser that accepts CSV with flexible headers and free text lines, a keyword categorizer, a summary function and rule-based suggestions. Write pytest tests with realistic student expenses.

**Result:** 34 tests, 32 passed on the first run.

## Step 4 — Debug the failures

| Issue found by testing | Fix |
|---|---|
| A user category column saying "travel" stayed as "Travel" instead of mapping to Transport | Added a `CATEGORY_ALIASES` table |
| `02/11 Swiggy dinner 280` kept "02/11" in the description | Added a short-date pattern at the start of a line |
| Test expected 15 rows from the notes file, but one line has no amount | The test was wrong; corrected to 14 |

## Step 5 — Find logic bugs by reading the output

Ran the sample files and read the results like a user would.

| Issue | Fix |
|---|---|
| Dates without a year ("02/11", "3 Nov") were parsed as year 1 | Borrow the year used elsewhere in the file, else the current year |
| "96% spent on weekends" appeared when only 3 of 14 rows had dates | Day-based insights only run when at least 60% of rows have dates (`dates_reliable`) |
| "Spending spike on 1 Oct" just pointed at rent day | Spike detection now ignores Rent & Bills |
| Rent at 42% was flagged red as an "alert" | Essential categories get a softer "tip" tone |

## Step 6 — Build the UI

**Prompt:** Build the Streamlit app in a neo-brutalist Gen Z style: cream dotted background, thick black borders, hard offset shadows, Archivo Black headings, a scrolling marquee, stat cards, a spending personality card, donut chart, daily bar chart, tip cards, downloads.

Validations added: file type, empty file, file over 2 MB, text encoding fallbacks, missing amounts, negative refunds, no valid rows, more than 5,000 rows.

## Step 7 — Test the main workflow

Smoke-tested `app.py` with six scenarios: sample CSV with budget, messy text sample, pasted text, uploaded CSV with unusual headers, junk text, and empty input. All produced either a full dashboard or a friendly error.

## Step 8 — Deploy and share

GitHub repo → Streamlit Community Cloud → QR code for the live URL.

## My own iterations

<!-- Add the changes you made yourself here. Examples: -->
<!-- - Asked Copilot to ... because ... -->
<!-- - Changed the colors of ... -->
<!-- - Found a bug when I uploaded my real bank export: ... -->
