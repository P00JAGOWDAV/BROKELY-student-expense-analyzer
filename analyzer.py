"""
analyzer.py — the brain of broke.ly (Student Expense Analyzer).

Pure Python + pandas, no Streamlit imports, so it can be unit-tested on its own.

Pipeline:
    raw CSV / text  ->  parse_input()  ->  clean DataFrame (date, description, amount)
                    ->  categorize()   ->  adds a "category" column
                    ->  summarize()    ->  numbers for the dashboard
                    ->  suggest()      ->  budget tips for a student
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import pandas as pd

# ---------------------------------------------------------------------------
# 1. Categories
# ---------------------------------------------------------------------------
# Keywords are matched as whole words (case-insensitive), so "pen" won't match
# "expensive" and "bus" won't match "business".
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Food & Dining": [
        "swiggy", "zomato", "canteen", "mess", "maggi", "chai", "tea", "coffee",
        "starbucks", "pizza", "burger", "restaurant", "cafe", "lunch", "dinner",
        "breakfast", "snack", "snacks", "dominos", "domino's", "kfc", "mcdonalds",
        "mcdonald's", "biryani", "momos", "dosa", "juice", "food", "eatery",
        "bakery", "ice cream", "subway", "chaayos", "samosa", "thali",
    ],
    "Groceries": [
        "grocery", "groceries", "blinkit", "zepto", "bigbasket", "instamart",
        "milk", "vegetables", "veggies", "fruits", "dmart", "eggs", "bread",
        "kirana", "supermarket",
    ],
    "Transport": [
        "uber", "ola", "rapido", "metro", "bus", "auto", "petrol", "fuel",
        "diesel", "train", "irctc", "cab", "taxi", "parking", "bike service",
        "flight", "redbus", "toll",
    ],
    "Rent & Bills": [
        "rent", "pg", "hostel", "electricity", "wifi", "wi-fi", "internet",
        "broadband", "recharge", "jio", "airtel", "vi", "bsnl", "water bill",
        "gas", "maintenance", "bill", "mobile plan",
    ],
    "Education": [
        "book", "books", "stationery", "course", "udemy", "coursera", "fees",
        "fee", "xerox", "printout", "print", "photocopy", "exam", "notebook",
        "pen", "pens", "tuition", "library", "lab", "assignment", "calculator",
    ],
    "Entertainment": [
        "movie", "movies", "netflix", "spotify", "prime", "hotstar", "jiocinema",
        "youtube premium", "game", "games", "gaming", "steam", "playstation",
        "concert", "pvr", "inox", "bookmyshow", "party", "club", "bowling",
        "outing", "trip", "fest",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "meesho", "ajio", "nykaa", "clothes",
        "shirt", "tshirt", "t-shirt", "jeans", "shoes", "sneakers", "watch",
        "headphones", "earphones", "gadget", "shopping", "mall", "accessories",
    ],
    "Health & Fitness": [
        "medicine", "medicines", "pharmacy", "chemist", "doctor", "clinic",
        "hospital", "apollo", "gym", "protein", "yoga", "pharmeasy", "1mg",
        "checkup", "dentist",
    ],
    "Personal Care": [
        "salon", "haircut", "barber", "laundry", "dhobi", "shampoo", "soap",
        "skincare", "toiletries", "grooming", "cosmetics",
    ],
}
OTHER = "Others"

# Needs vs wants, for the "needs / wants" split card.
NEEDS = {"Rent & Bills", "Groceries", "Transport", "Education", "Health & Fitness"}
WANTS = {"Food & Dining", "Entertainment", "Shopping", "Personal Care"}

# Common labels people already use in their own sheets.
CATEGORY_ALIASES = {
    "travel": "Transport", "commute": "Transport", "transportation": "Transport",
    "eating out": "Food & Dining", "dining": "Food & Dining", "snacks": "Food & Dining",
    "bills": "Rent & Bills", "utilities": "Rent & Bills", "housing": "Rent & Bills",
    "study": "Education", "studies": "Education", "college": "Education", "academics": "Education",
    "fun": "Entertainment", "leisure": "Entertainment", "subscriptions": "Entertainment",
    "medical": "Health & Fitness", "health": "Health & Fitness", "fitness": "Health & Fitness",
    "grocery": "Groceries", "personal": "Personal Care", "self care": "Personal Care",
    "misc": OTHER, "miscellaneous": OTHER, "other": OTHER, "others": OTHER,
}

SUBSCRIPTION_WORDS = [
    "netflix", "spotify", "prime", "hotstar", "jiocinema", "youtube premium",
    "apple music", "disney", "zee5", "sonyliv", "chatgpt", "subscription",
]

# Pre-compile one regex per category for speed + whole-word matching.
_CATEGORY_PATTERNS = {
    cat: re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(k) for k in kws) + r")(?![a-z0-9])")
    for cat, kws in CATEGORY_KEYWORDS.items()
}
_SUB_PATTERN = re.compile(
    r"(?<![a-z0-9])(" + "|".join(re.escape(k) for k in SUBSCRIPTION_WORDS) + r")(?![a-z0-9])"
)


def categorize_text(description: str) -> str:
    """Return the best category for one expense description."""
    text = str(description).lower()
    best_cat, best_hits = OTHER, 0
    for cat, pattern in _CATEGORY_PATTERNS.items():
        hits = len(pattern.findall(text))
        if hits > best_hits:
            best_cat, best_hits = cat, hits
    return best_cat


def _normalize_user_category(value) -> str | None:
    """If the user's file already has a category, map it onto ours when possible."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none", "-", "na", "n/a"}:
        return None
    low = raw.lower()
    if low in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[low]
    for cat in CATEGORY_KEYWORDS:
        # "food" -> "Food & Dining", "transport" -> "Transport", etc.
        first_word = cat.split()[0].lower()
        if low == cat.lower() or low == first_word or low.startswith(first_word):
            return cat
    # Try keyword match on the category label itself ("uber" -> Transport)
    guessed = categorize_text(raw)
    if guessed != OTHER:
        return guessed
    return raw.title()


def categorize(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'category' column. A user-supplied category wins if it's present."""
    out = df.copy()
    user_cats = out["category"] if "category" in out.columns else pd.Series([None] * len(out), index=out.index)
    out["category"] = [
        _normalize_user_category(uc) or categorize_text(desc)
        for uc, desc in zip(user_cats, out["description"])
    ]
    return out


# ---------------------------------------------------------------------------
# 2. Parsing
# ---------------------------------------------------------------------------
class ParseError(ValueError):
    """Raised with a friendly message when the input can't be used."""


@dataclass
class ParseResult:
    df: pd.DataFrame
    warnings: list[str] = field(default_factory=list)
    source: str = "csv"  # "csv" or "text"


AMOUNT_COLS = ["amount", "amt", "cost", "price", "spent", "value", "expense amount",
               "rs", "inr", "money", "total", "debit", "amount (₹)", "amount(rs)", "amount (rs)"]
DESC_COLS = ["description", "desc", "item", "items", "details", "detail", "note", "notes",
             "name", "title", "particulars", "expense", "merchant", "narration", "remarks", "what"]
DATE_COLS = ["date", "day", "txn date", "transaction date", "when", "time", "datetime"]
CAT_COLS = ["category", "type", "cat", "tag"]

MAX_ROWS = 5000

_CURRENCY_RE = re.compile(r"(₹|rs\.?|inr|/-)", re.IGNORECASE)


def clean_amount(value) -> float | None:
    """'₹1,250.50' -> 1250.5 ; 'Rs. 40/-' -> 40.0 ; junk -> None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    text = _CURRENCY_RE.sub("", str(value)).replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        m = re.search(r"-?\d+(?:\.\d+)?", text)
        return float(m.group()) if m else None


def _pick_column(columns: list[str], candidates: list[str]) -> str | None:
    for cand in candidates:
        if cand in columns:
            return cand
    for col in columns:  # fuzzy: "amount_inr", "expense_description"
        for cand in candidates:
            if len(cand) > 2 and cand in col:
                return col
    return None


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse mixed date formats; Indian style (day first) for ambiguous ones.

    Dates without a year ("02/11", "3 Nov") borrow the year used elsewhere in
    the file, or the current year.
    """
    texts = series.map(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip())
    years = texts.str.extract(r"((?:19|20)\d{2})")[0].dropna()
    ref_year = int(years.mode().iloc[0]) if not years.empty else pd.Timestamp.today().year

    def has_year(s: str) -> bool:
        return bool(re.search(r"(?:19|20)\d{2}", s) or re.search(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2}\b", s))

    def one(s: str):
        if not s:
            return pd.NaT
        if not has_year(s):
            s = f"{s}/{ref_year}" if re.fullmatch(r"\d{1,2}[/.-]\d{1,2}", s) else f"{s} {ref_year}"
        # ISO dates (2026-10-05) must not be read day-first.
        dayfirst = not re.match(r"^\d{4}-\d{1,2}-\d{1,2}", s)
        try:
            return pd.to_datetime(s, errors="coerce", dayfirst=dayfirst)
        except (ValueError, OverflowError):
            return pd.NaT
    return pd.to_datetime(texts.map(one), errors="coerce")


def _finalize(df: pd.DataFrame, warnings: list[str]) -> pd.DataFrame:
    """Shared cleanup: drop bad amounts, refunds, blanks; validate."""
    start = len(df)
    df = df.copy()
    df["description"] = df["description"].fillna("").astype(str).str.strip()
    df.loc[df["description"] == "", "description"] = "Unnamed expense"

    bad_amount = df["amount"].isna()
    if bad_amount.any():
        warnings.append(f"Skipped {int(bad_amount.sum())} row(s) with a missing or unreadable amount.")
    df = df[~bad_amount]

    non_positive = df["amount"] <= 0
    if non_positive.any():
        warnings.append(
            f"Skipped {int(non_positive.sum())} row(s) with zero or negative amounts "
            "(refunds or income aren't counted as spending)."
        )
    df = df[~non_positive]

    if df.empty:
        raise ParseError(
            "No valid expenses found. Each row needs a description and a positive amount, "
            "like  Swiggy dinner, 250"
        )

    huge = df["amount"] > 1_000_000
    if huge.any():
        warnings.append(f"{int(huge.sum())} expense(s) are over ₹10,00,000. Double-check those amounts.")

    if "date" in df.columns:
        missing = int(df["date"].isna().sum())
        if missing > len(df) / 2:
            # Mostly undated: dates are optional, so skip the daily chart quietly.
            df = df.drop(columns=["date"])
        elif missing:
            # Mostly dated with a few gaps: probably a typo worth flagging.
            warnings.append(f"{missing} row(s) had no readable date; they're included but left out of the daily chart.")

    if len(df) < start and not warnings:
        warnings.append(f"Skipped {start - len(df)} row(s).")
    return df.reset_index(drop=True)


def parse_csv(text: str) -> ParseResult:
    warnings: list[str] = []
    try:
        raw = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str,
                          skip_blank_lines=True, on_bad_lines="skip")
    except Exception as exc:  # pandas raises many different errors here
        raise ParseError(f"Couldn't read this as a CSV ({type(exc).__name__}).") from exc

    raw.columns = [str(c).strip().lower() for c in raw.columns]
    cols = list(raw.columns)
    amount_col = _pick_column(cols, AMOUNT_COLS)

    if amount_col is None:
        # Maybe there's no header row ("Maggi,40") — let the text parser try.
        raise ParseError("no-amount-column")

    desc_col = _pick_column([c for c in cols if c != amount_col], DESC_COLS)
    date_col = _pick_column([c for c in cols if c not in (amount_col, desc_col)], DATE_COLS)
    cat_col = _pick_column([c for c in cols if c not in (amount_col, desc_col, date_col)], CAT_COLS)

    if desc_col is None:
        # Use the first text-looking column that isn't amount/date.
        leftovers = [c for c in cols if c not in (amount_col, date_col, cat_col)]
        if leftovers:
            desc_col = leftovers[0]
        elif cat_col:
            desc_col = cat_col
        else:
            warnings.append("No description column found, so items are listed as 'Unnamed expense'.")

    df = pd.DataFrame({
        "description": raw[desc_col] if desc_col else "",
        "amount": raw[amount_col].map(clean_amount),
    })
    if date_col:
        df["date"] = _parse_dates(raw[date_col])
    if cat_col:
        df["category"] = raw[cat_col]

    return ParseResult(_finalize(df, warnings), warnings, "csv")


# Date shapes we strip out of free text before hunting for the amount.
_DATE_PATTERNS = [
    r"\b\d{4}-\d{1,2}-\d{1,2}\b",                     # 2026-10-05
    r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",           # 05/10/2026, 5-10-26
    r"^\s*\d{1,2}[/.-]\d{1,2}(?=\s)",                 # 02/11 at the start of a line
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?(?:\s+\d{4})?\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b",
]
_DATE_RE = re.compile("|".join(_DATE_PATTERNS), re.IGNORECASE)
_AMOUNT_RE = re.compile(
    r"(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:₹|rs\.?|inr|/-|rupees)?",
    re.IGNORECASE,
)


def parse_text_line(line: str) -> tuple[str, float | None, str | None]:
    """'05/10 Swiggy dinner - ₹250' -> ('Swiggy dinner', 250.0, '05/10')."""
    date_match = _DATE_RE.search(line)
    date_str = date_match.group() if date_match else None
    rest = _DATE_RE.sub(" ", line) if date_match else line

    amounts = list(_AMOUNT_RE.finditer(rest))
    if not amounts:
        return rest.strip(" ,;:-|\t"), None, date_str

    # Prefer a number with a currency marker, otherwise the last number on the line.
    marked = [m for m in amounts if re.search(r"₹|rs|inr|/-|rupees", m.group(), re.IGNORECASE)]
    chosen = marked[-1] if marked else amounts[-1]
    amount = clean_amount(chosen.group(1))

    desc = (rest[: chosen.start()] + " " + rest[chosen.end():])
    desc = re.sub(r"\s+", " ", desc).strip(" ,;:-|=\t")
    return desc, amount, date_str


def parse_text(text: str) -> ParseResult:
    warnings: list[str] = []
    rows, bad_lines = [], []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        low = stripped.lower()
        if re.match(r"^(date|description|item)\b.*\b(amount|cost|price)\b", low):
            continue  # header row
        desc, amount, date_str = parse_text_line(stripped)
        if amount is None:
            bad_lines.append(i)
            continue
        rows.append({"description": desc, "amount": amount, "date": date_str})

    if bad_lines:
        shown = ", ".join(map(str, bad_lines[:8])) + ("…" if len(bad_lines) > 8 else "")
        warnings.append(f"Couldn't find an amount on line(s) {shown}, so they were skipped.")

    if not rows:
        raise ParseError(
            "No expenses found in that text. Put one expense per line with an amount, like\n"
            "Swiggy dinner 250\n05/10/2026, Uber to college, 120"
        )

    df = pd.DataFrame(rows)
    df["date"] = _parse_dates(df["date"])
    return ParseResult(_finalize(df, warnings), warnings, "text")


def parse_input(text: str, filename: str | None = None) -> ParseResult:
    """Entry point: decide CSV vs free text, parse, categorize."""
    if text is None or not str(text).strip():
        raise ParseError("The file or text is empty. Add at least one expense.")
    text = str(text).lstrip("﻿")  # strip Excel's BOM

    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) > MAX_ROWS + 1:
        raise ParseError(f"That's more than {MAX_ROWS:,} rows. Upload one month of expenses at a time.")

    is_csv_name = bool(filename and filename.lower().endswith(".csv"))
    looks_tabular = len(lines) >= 2 and all(l.count(",") >= 1 or "\t" in l or ";" in l for l in lines[:5])

    result: ParseResult | None = None
    if is_csv_name or looks_tabular:
        try:
            result = parse_csv(text)
        except ParseError as exc:
            if str(exc) != "no-amount-column":
                if is_csv_name:
                    raise
            # fall through to text parsing
    if result is None:
        try:
            result = parse_text(text)
        except ParseError:
            if is_csv_name:
                raise ParseError(
                    "This CSV has no amount column. Add a column named Amount (or Cost / Price) "
                    "with numbers, like  Date, Description, Amount"
                ) from None
            raise
        if is_csv_name:
            result.warnings.insert(0, "No 'amount' header found, so the file was read line by line.")

    result.df = categorize(result.df)
    return result


# ---------------------------------------------------------------------------
# 3. Summary
# ---------------------------------------------------------------------------
def summarize(df: pd.DataFrame, budget: float | None = None) -> dict:
    total = float(df["amount"].sum())
    by_cat = (
        df.groupby("category")["amount"].agg(["sum", "count"])
        .sort_values("sum", ascending=False)
        .reset_index()
        .rename(columns={"sum": "total", "count": "transactions"})
    )
    by_cat["share"] = by_cat["total"] / total * 100

    top = by_cat.iloc[0]
    needs = float(df.loc[df["category"].isin(NEEDS), "amount"].sum())
    wants = float(df.loc[df["category"].isin(WANTS), "amount"].sum())
    other = total - needs - wants

    small = df[df["amount"] < 100]
    summary = {
        "total": total,
        "count": int(len(df)),
        "average": total / len(df),
        "largest": df.loc[df["amount"].idxmax()].to_dict(),
        "by_category": by_cat,
        "top_category": str(top["category"]),
        "top_share": float(top["share"]),
        "top_expenses": df.nlargest(5, "amount")[[c for c in ["date", "description", "category", "amount"] if c in df.columns]],
        "needs": needs,
        "wants": wants,
        "other": other,
        "small_count": int(len(small)),
        "small_total": float(small["amount"].sum()),
        "subscriptions": sorted({d for d in df["description"] if _SUB_PATTERN.search(d.lower())}),
        "budget": budget if budget and budget > 0 else None,
        "has_dates": "date" in df.columns and df["date"].notna().any(),
    }
    # Day-based insights only make sense when most rows have a date.
    n_dated = int(df["date"].notna().sum()) if "date" in df.columns else 0
    summary["dates_reliable"] = n_dated >= max(5, 0.6 * len(df))

    if summary["has_dates"]:
        dated = df.dropna(subset=["date"]).copy()
        dated["day"] = dated["date"].dt.normalize()
        daily = dated.groupby("day")["amount"].sum().sort_index()
        days_span = (daily.index.max() - daily.index.min()).days + 1
        weekend = float(dated.loc[dated["date"].dt.dayofweek >= 5, "amount"].sum())
        flex = dated[~dated["category"].isin({"Rent & Bills"})].groupby("day")["amount"].sum()
        summary.update({
            "flex_peak_day": flex.idxmax() if not flex.empty else None,
            "flex_peak_amount": float(flex.max()) if not flex.empty else 0.0,
            "flex_daily_average": float(flex.sum()) / days_span if not flex.empty else 0.0,
        })
        summary.update({
            "daily": daily,
            "days_span": days_span,
            "daily_average": float(daily.sum()) / days_span,
            "peak_day": daily.idxmax(),
            "peak_day_amount": float(daily.max()),
            "weekend_share": weekend / float(dated["amount"].sum()) * 100,
            "period": (daily.index.min(), daily.index.max()),
        })
    return summary


# ---------------------------------------------------------------------------
# 4. Spending personality + suggestions
# ---------------------------------------------------------------------------
def personality(s: dict) -> tuple[str, str]:
    """A fun one-liner label for the dashboard."""
    cat, share = s["top_category"], s["top_share"]
    if s.get("budget") and s["total"] > s["budget"] * 1.1:
        return "The Overdraft Speedrunner", "Budget? Never heard of her. Let's fix that."
    if len(s["subscriptions"]) >= 3:
        return "The Subscription Collector", "Netflix, Spotify, Prime… you're funding half the internet."
    if s.get("dates_reliable") and s.get("weekend_share", 0) > 45:
        return "The Weekend Warrior", "Monday to Friday you're a monk. Saturday you're a millionaire."
    if cat == "Food & Dining" and share > 30:
        return "The Foodie", "Swiggy knows your order before you do."
    if cat == "Shopping" and share > 25:
        return "The Cart Addict", "Add to cart is your cardio."
    if cat == "Entertainment" and share > 25:
        return "The Main Character", "Movies, games, fests. Living the plot."
    if cat == "Transport" and share > 25:
        return "The Road Runner", "Always on the move, wallet included."
    if s["small_count"] >= 10:
        return "The Chai-and-Snacks Spender", "Small buys, big total. Death by a thousand samosas."
    if s["wants"] <= s["needs"]:
        return "The Responsible Adult", "Needs first, wants later. Your future self says thanks."
    return "The Balanced Budgeter", "No major red flags. A few tweaks and you're golden."


_CATEGORY_TIPS = {
    "Food & Dining": "Food delivery is your biggest leak. Cooking or eating at the mess 3–4 extra days a week could save around {save}.",
    "Shopping": "Try the 48-hour rule: leave items in your cart for two days before buying. Cutting shopping by a third saves about {save}.",
    "Entertainment": "Set a fixed fun budget each week and look for student discounts on movies and events. Trimming 30% saves about {save}.",
    "Transport": "A monthly metro or bus student pass, or sharing cabs with friends, could cut travel costs by about {save}.",
    "Rent & Bills": "Rent and bills are fixed, but check for a cheaper mobile or Wi-Fi plan and split utilities fairly with flatmates.",
    "Groceries": "Buy staples in bulk at DMart and plan meals weekly to cut impulse quick-commerce orders. That could save about {save}.",
    "Education": "Use the library, second-hand books and free courses (NPTEL, YouTube) before paying. Could save around {save}.",
    "Health & Fitness": "Health spending is worth it. Check if your college offers a free gym, health centre or student insurance.",
    "Personal Care": "Do laundry in batches and compare salon prices. Small, steady cuts here could save about {save}.",
}


def inr(x: float) -> str:
    """Indian-style currency: 125000 -> ₹1,25,000."""
    x = round(float(x))
    s = str(abs(int(x)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(i - 2, 0):i] for i in range(len(head), 0, -2)][::-1])
        s = head + "," + tail
    return ("-" if x < 0 else "") + "₹" + s


def suggest(s: dict) -> list[dict]:
    """Return a list of {title, body, tone} tips. tone: alert | tip | win."""
    tips: list[dict] = []
    total = s["total"]

    # Budget check
    if s.get("budget"):
        b = s["budget"]
        used = total / b * 100
        if total > b:
            tips.append({"tone": "alert", "title": f"Over budget by {inr(total - b)}",
                         "body": f"You spent {used:.0f}% of your {inr(b)} budget. Start with the biggest category below."})
        elif used >= 85:
            tips.append({"tone": "tip", "title": f"Cutting it close: {used:.0f}% used",
                         "body": f"Only {inr(b - total)} left. Hold off on non-essentials until next month."})
        else:
            tips.append({"tone": "win", "title": f"Under budget: {inr(b - total)} left",
                         "body": f"You used {used:.0f}% of your budget. Move the leftover into savings before it disappears."})

    # Biggest category
    cat, share = s["top_category"], s["top_share"]
    cat_total = float(s["by_category"].iloc[0]["total"])
    if share >= 30 and cat in _CATEGORY_TIPS:
        cut = 0.3 if cat != "Food & Dining" else 0.35
        tips.append({"tone": "alert" if share >= 45 and cat not in NEEDS else "tip",
                     "title": f"{cat} takes {share:.0f}% of your money",
                     "body": _CATEGORY_TIPS[cat].format(save=inr(cat_total * cut))})

    # Wants vs needs
    if total > 0 and s["wants"] / total > 0.5:
        tips.append({"tone": "tip", "title": f"Wants are {s['wants'] / total * 100:.0f}% of spending",
                     "body": "A good student target is 50% needs, 30% wants, 20% savings. Try moving one weekly treat into a savings jar."})

    # Subscriptions
    if s["subscriptions"]:
        names = ", ".join(s["subscriptions"][:4])
        tips.append({"tone": "tip", "title": f"{len(s['subscriptions'])} subscription(s) spotted",
                     "body": f"Found: {names}. Switch to student plans (Spotify and YouTube have them), share family plans, or cancel the one you used least."})

    # Small purchases
    if s["small_count"] >= 8:
        tips.append({"tone": "tip", "title": f"{s['small_count']} small buys added up to {inr(s['small_total'])}",
                     "body": "Chai, snacks and quick orders under ₹100 sneak up on you. Carry a water bottle and snacks from home."})

    # Weekend spending
    if s.get("dates_reliable") and s.get("weekend_share", 0) > 40:
        tips.append({"tone": "tip", "title": f"{s['weekend_share']:.0f}% spent on weekends",
                     "body": "Plan weekends ahead: pick one paid outing and fill the rest with free plans like campus events or parks."})

    # Peak day
    if s.get("dates_reliable") and s.get("flex_peak_amount", 0) > 2.5 * max(s.get("flex_daily_average", 0), 1):
        tips.append({"tone": "tip", "title": f"Spending spike on {s['flex_peak_day']:%d %b}",
                     "body": f"Leaving out rent and bills, you spent {inr(s['flex_peak_amount'])} that day, over twice your usual {inr(s['flex_daily_average'])} a day. Was it planned?"})

    # Always end with something actionable
    daily_cap = (s["budget"] if s.get("budget") else total) / 30
    tips.append({"tone": "win", "title": f"Try a daily cap of {inr(daily_cap)}",
                 "body": "Track every spend for a week in a notes app. People who track spend less without trying."})
    if len(tips) < 3:
        tips.append({"tone": "win", "title": "Pay yourself first",
                     "body": "When pocket money or salary arrives, move 10–20% to savings straight away and budget with the rest."})
    return tips


def report_text(s: dict, tips: list[dict]) -> str:
    """Plain-text report for the download button."""
    lines = ["broke.ly — Student Expense Report", "=" * 34, "",
             f"Total spent:      {inr(s['total'])}",
             f"Transactions:     {s['count']}",
             f"Average per item: {inr(s['average'])}"]
    if s.get("budget"):
        lines.append(f"Budget:           {inr(s['budget'])}")
    if s.get("has_dates"):
        a, b = s["period"]
        lines.append(f"Period:           {a:%d %b %Y} – {b:%d %b %Y}")
    lines += ["", "Spending by category", "-" * 20]
    for _, r in s["by_category"].iterrows():
        lines.append(f"{r['category']:<18} {inr(r['total']):>10}  {r['share']:5.1f}%  ({int(r['transactions'])} items)")
    lines += ["", "Suggestions", "-" * 11]
    for i, t in enumerate(tips, 1):
        lines.append(f"{i}. {t['title']}\n   {t['body']}")
    return "\n".join(lines)
