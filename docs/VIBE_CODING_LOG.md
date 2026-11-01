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

Problems I hit while running, testing and deploying the app myself, and how I fixed them with the AI's help.

| # | What happened | Cause | Fix |
|---|---|---|---|
| 1 | `.venv\Scripts\activate` failed: "running scripts is disabled on this system" | Windows PowerShell blocks scripts by default | Ran `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| 2 | `pip install` said "requirements.txt not found" | Unzipping created a folder inside a folder, so the terminal was in the wrong one | Moved into the inner folder and opened it as the VS Code workspace |
| 3 | `streamlit` was "not recognized" and then "No module named streamlit" | Commands were using the system Python 3.14, not the project's virtual environment | Ran everything through `.venv\Scripts\python -m ...` |
| 4 | Pasted text showed "8 row(s) had no readable date" | The warning fired even though dates are optional in text input | Asked the AI to show it only when most rows are dated; added 2 tests (43 passing) |
| 5 | `git commit` said "not a git repository" | Git hadn't been initialised yet | Ran `git init` and committed the project in 5 stages |
| 6 | `git push` was rejected with "fetch first" | GitHub created its own files when I made the repo | Force-pushed my local history to the new, empty repo |
| 7 | The QR code pointed to the wrong URL | I chose `brokely` as the app name, but generated the QR for `brokely-pooja` | Regenerated it with `tools/make_qr.py https://brokely.streamlit.app` |
| 8 | Screenshots showed as text on GitHub | File names didn't match the README (GitHub is case-sensitive) | Renamed them to exact lowercase names |

**Extra test data:** asked the AI for varied sample files (hostel foodie, weekend shopper, tight budget, subscription hoarder, messy bank export, broken file) to test every personality and error message.

## What I learned

- Building in small steps and testing after each one finds bugs early
- Reading error messages carefully usually points straight to the fix
- Git basics: init, staged commits, push, and fixing a rejected push
- Python virtual environments and why the right interpreter matters
- Deploying a Python app for free and sharing it with a QR code
