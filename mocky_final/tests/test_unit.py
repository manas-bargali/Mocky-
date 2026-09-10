"""
UNIT TESTS
Test individual functions in isolation — no Flask app, no network calls.
"""
import pytest
import app as mocky_app


# ── parse_question ────────────────────────────────────────────────────────
def test_parse_question_extracts_all_fields():
    raw = """Q. What is 2+2?
(a) 3
(b) 4
(c) 5
(d) 6
(e) None of these
ANSWER: (b)"""
    result = mocky_app.parse_question(raw)
    assert result["question"] == "What is 2+2?"
    assert result["options"] == {"a": "3", "b": "4", "c": "5", "d": "6", "e": "None of these"}
    assert result["answer"] == "b"


def test_parse_question_handles_multiline_question_text():
    raw = """Q. Line one of the question.
Line two continues it.
(a) Opt A
(b) Opt B
ANSWER: (a)"""
    result = mocky_app.parse_question(raw)
    assert "Line one" in result["question"]
    assert "Line two" in result["question"]


# ── detect_type: Reasoning ──────────────────────────────────────────────────
@pytest.mark.parametrize("text,expected", [
    ("Fourteen persons sit in two rows facing each other", "Seating"),
    ("Q is the only daughter of R who is father of S", "Blood Relation"),
    ("They live on different floors of a building", "Floor Puzzle"),
    ("The code for RAIN is coded as XYZ", "Coding"),
    ("P > Q and R < S", "Inequality"),
    ("Seven persons P, Q, R, S, T, U and V like different fruits and sit together.", "Linear Arrangement"),
])
def test_detect_type_reasoning_branches(text, expected):
    assert mocky_app.detect_type(text, "Reasoning") == expected


# ── detect_type: Quantitative ────────────────────────────────────────────
@pytest.mark.parametrize("text,expected", [
    ("361, 425, ? , 920 find the missing number", "Number Series"),
    ("Simple interest for 2 years at 5 percent per annum", "SI/CI"),
    ("Find the profit percentage on the article", "Profit/Loss"),
    ("A can do a work in 10 days", "Time/Work"),
    ("What is 20% of 500", "Percentage/DI"),
])
def test_detect_type_quant_branches(text, expected):
    assert mocky_app.detect_type(text, "Quantitative") == expected


# ── get_grade ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("pct,expected_substr", [
    (95, "Excellent"),
    (75, "Good"),
    (55, "Average"),
    (20, "Below Average"),
])
def test_get_grade_bands(pct, expected_substr):
    assert expected_substr in mocky_app.get_grade(pct)


# ── build_system_prompt ──────────────────────────────────────────────────
def test_build_system_prompt_pulls_in_rag_patterns():
    prompt = mocky_app.build_system_prompt("Reasoning")
    assert "Reasoning" in prompt
    assert "Seating Arrangement" in prompt   # comes from data/ibps_patterns.json
    assert "STRICT RULES" in prompt


def test_build_system_prompt_unknown_section_does_not_crash():
    prompt = mocky_app.build_system_prompt("NotASection")
    assert "STRICT RULES" in prompt  # falls back gracefully, patterns section empty
