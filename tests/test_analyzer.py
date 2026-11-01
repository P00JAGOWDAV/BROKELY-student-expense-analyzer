"""Run with:  python -m pytest -q"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyzer import (ParseError, categorize_text, clean_amount, inr, parse_input,
                      parse_text_line, personality, suggest, summarize, report_text)


# --- categorization -------------------------------------------------------
@pytest.mark.parametrize("desc, cat", [
    ("Swiggy biryani", "Food & Dining"),
    ("Uber to college", "Transport"),
    ("PG rent October", "Rent & Bills"),
    ("Netflix", "Entertainment"),
    ("Myntra tshirt", "Shopping"),
    ("Blinkit groceries", "Groceries"),
    ("Xerox notes", "Education"),
    ("Medicine pharmacy", "Health & Fitness"),
    ("Haircut salon", "Personal Care"),
    ("random thing", "Others"),
    ("Expensive business dinner", "Food & Dining"),  # 'pen'/'bus' must not match inside words
])
def test_categorize_text(desc, cat):
    assert categorize_text(desc) == cat


# --- amounts --------------------------------------------------------------
@pytest.mark.parametrize("raw, val", [
    ("₹1,250.50", 1250.5), ("Rs. 40/-", 40.0), ("300", 300.0), (99, 99.0), ("abc", None), ("", None),
])
def test_clean_amount(raw, val):
    assert clean_amount(raw) == val


def test_inr_format():
    assert inr(125000) == "₹1,25,000"
    assert inr(999) == "₹999"
    assert inr(1234567.6) == "₹12,34,568"


# --- text lines -----------------------------------------------------------
@pytest.mark.parametrize("line, desc, amt", [
    ("Swiggy dinner 280", "Swiggy dinner", 280),
    ("01/11/2026 PG rent - ₹6500", "PG rent", 6500),
    ("Uber to college Rs. 145", "Uber to college", 145),
    ("3 Nov chai with friends 30", "chai with friends", 30),
    ("Myntra jeans 1,299", "Myntra jeans", 1299),
    ("Metro recharge 250/-", "Metro recharge", 250),
    ("2 samosa 40", "2 samosa", 40),
])
def test_parse_text_line(line, desc, amt):
    d, a, _ = parse_text_line(line)
    assert d == desc and a == amt


# --- full files -----------------------------------------------------------
def test_sample_csv():
    text = (ROOT / "sample_data/october_expenses.csv").read_text()
    res = parse_input(text, "october_expenses.csv")
    assert len(res.df) == 44
    assert res.df["amount"].sum() == 17085
    s = summarize(res.df, budget=15000)
    assert s["has_dates"] and s["top_category"] == "Rent & Bills"
    tips = suggest(s)
    assert tips[0]["tone"] == "alert"  # over budget
    assert len(tips) >= 3
    assert "Total spent" in report_text(s, tips)


def test_sample_text_notes():
    text = (ROOT / "sample_data/quick_notes.txt").read_text()
    res = parse_input(text, "quick_notes.txt")
    assert len(res.df) == 14
    assert res.df.loc[1, "description"] == "Swiggy dinner"  # "02/11" stripped as a date
    assert any("line" in w for w in res.warnings)  # "forgot what this was" skipped
    s = summarize(res.df)
    assert len(s["subscriptions"]) == 3
    assert personality(s)[0] == "The Subscription Collector"


def test_csv_with_other_headers_and_categories():
    text = "Item;Cost (Rs);Type\nPizza;₹300;Food\nBus pass;500;travel\nRefund;-200;Other\n"
    res = parse_input(text, "x.csv")
    assert list(res.df["category"]) == ["Food & Dining", "Transport"]
    assert any("negative" in w for w in res.warnings)


def test_headerless_csv_falls_back_to_text():
    res = parse_input("Maggi,40\nUber,120\n", "x.csv")
    assert res.df["amount"].tolist() == [40, 120]


def test_tsv_and_ddmmyyyy():
    text = "date\tdescription\tamount\n05/10/2026\tChai\t20\n31/10/2026\tRent\t5000\n"
    res = parse_input(text, "x.csv")
    assert res.df["date"].dt.month.tolist() == [10, 10]
    assert res.df["date"].dt.day.tolist() == [5, 31]


@pytest.mark.parametrize("bad", ["", "   \n\n", "hello world\nno numbers here"])
def test_bad_input_raises(bad):
    with pytest.raises(ParseError):
        parse_input(bad, "x.txt")


def test_csv_with_no_valid_amounts():
    with pytest.raises(ParseError):
        parse_input("description,amount\nPizza,abc\nTea,\n", "x.csv")


def test_yearless_dates_borrow_year():
    res = parse_input("01/11/2026 Rent 5000\n02/11 Swiggy 280\n3 Nov chai 30\n", "n.txt")
    assert res.df["date"].dt.year.tolist() == [2026, 2026, 2026]
    assert res.df["date"].dt.day.tolist() == [1, 2, 3]


def test_few_dates_skip_weekend_tip():
    text = (ROOT / "sample_data/quick_notes.txt").read_text()
    s = summarize(parse_input(text, "n.txt").df)
    assert not s["dates_reliable"]
    assert not any("weekend" in t["title"] for t in suggest(s))


@pytest.mark.parametrize("fname, persona", [
    ("hostel_foodie.csv", "The Foodie"),
    ("weekend_shopper.csv", "The Weekend Warrior"),
    ("subscription_hoarder.txt", "The Subscription Collector"),
])
def test_extra_samples(fname, persona):
    res = parse_input((ROOT / "sample_data" / fname).read_text(encoding="utf-8"), fname)
    assert personality(summarize(res.df))[0] == persona


def test_bank_export_skips_refund_and_junk():
    res = parse_input((ROOT / "sample_data/semicolon_bank_export.csv").read_text(encoding="utf-8"), "b.csv")
    assert len(res.df) == 6 and len(res.warnings) == 2


def test_broken_csv_message():
    with pytest.raises(ParseError, match="no amount column"):
        parse_input((ROOT / "sample_data/broken_file.csv").read_text(), "broken_file.csv")


def test_mostly_undated_text_has_no_date_warning():
    text = "05/10/2026 Swiggy biryani 280\nZomato pizza ₹410\nNetflix 199\nUber Rs. 150\nchai 20\n"
    res = parse_input(text, "pasted.txt")
    assert res.warnings == [] and "date" not in res.df.columns


def test_few_missing_dates_still_warn():
    text = "date,description,amount\n2026-10-01,Chai,20\n2026-10-02,Uber,120\n2026-10-03,Rent,5000\nbad-date,Pizza,300\n"
    res = parse_input(text, "x.csv")
    assert any("no readable date" in w for w in res.warnings)
