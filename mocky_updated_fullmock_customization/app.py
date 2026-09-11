"""
Mocky - IBPS RRB PO Prelims Mock Test Platform
Uses Context Engineering + RAG pattern from the real IBPS RRB PO Pre 2024 paper.

Modes
-----
1. Sectional practice  – pick ONE subject (Reasoning / Quantitative / English)
   and how many questions to attempt (10 / 15 / 30). Timer is scaled from the
   real exam's per-question pace for that subject.
2. Full-length mock     – all 3 sections back-to-back, using the REAL
   question-count + sectional-time pattern IBPS used for RRB PO Pre 2024
   (Reasoning: 40 Q / 25 min, Quantitative: 40 Q / 20 min) plus the standard
   IBPS English sectional timing (30 Q / 20 min), since Mocky offers English
   as a third practice subject that the RRB Pre itself doesn't include.

During the test no correctness/explanation is ever revealed — only after the
final submit does /final-result expose the answer key plus a topic-wise
accuracy breakdown so a candidate can see exactly which question types are
dragging their score down.
"""

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from openai import OpenAI
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mocky_ibps_2024")

# ── Server-side sessions ──────────────────────────────────────────────────
# A full mock can hold 100+ generated questions with full text/options, which
# is far too big for Flask's default signed-cookie session (~4KB). Storing
# session data in files instead removes that ceiling.
_SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".flask_session")
os.makedirs(_SESSION_DIR, exist_ok=True)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = _SESSION_DIR
app.config["SESSION_PERMANENT"] = False
Session(app)

# ── Load RAG data (pattern from real paper) ──────────────────────────────
with open("data/ibps_patterns.json") as f:
    IBPS_PATTERNS = json.load(f)

# Groq exposes an OpenAI-compatible endpoint, so we reuse the openai SDK and
# just point it at Groq's base_url with a Groq key.
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY", ""),
)
GROQ_MODEL = "openai/gpt-oss-120b"

# ── Real IBPS timing, sourced from the official 2024 sectional-timing pattern ──
# Reasoning: 40 Q / 25 min · Quantitative: 40 Q / 20 min  (IBPS RRB PO Pre 2024)
# English:   30 Q / 20 min  (standard IBPS PO English sectional timing — RRB
#            Pre itself has no English section, Mocky borrows this so its
#            3rd practice subject still has an authentic pace)
SECTION_TIME_PER_Q = {
    "Reasoning":    37.5,   # 25 min / 40 Q
    "Quantitative": 30.0,   # 20 min / 40 Q
    "English":      40.0,   # 20 min / 30 Q
}

QUESTION_COUNT_CHOICES = [10, 15, 30]

# Real full-paper pattern used for the "Full-Length Mock"
FULL_MOCK_PLAN = [
    {"section": "Reasoning",    "count": 40},
    {"section": "Quantitative", "count": 40},
    {"section": "English",      "count": 30},
]


def _time_for(section: str, count: int) -> int:
    return round(SECTION_TIME_PER_Q[section] * count)


# ── Context Engineering: System prompt baked with real paper patterns ─────
def build_system_prompt(section: str) -> str:
    patterns = IBPS_PATTERNS.get(section, {})
    qtypes   = patterns.get("question_types", [])

    types_text = "\n".join(
        f"- {qt['type']}: e.g. {qt['example']}\n  Options style: {qt['options_style']}"
        for qt in qtypes
    )

    return f"""You are an IBPS RRB PO Prelims question generator.
You have studied the REAL IBPS RRB PO Pre 2024 paper (3rd August, 1st Shift).

SECTION: {section}
DESCRIPTION: {patterns.get('description', '')}

ACTUAL QUESTION TYPES FROM THAT PAPER:
{types_text}

STRICT RULES:
1. Generate ONE question at a time in the EXACT IBPS RRB format.
2. Provide EXACTLY 5 options labeled (a) through (e).
3. Mark correct answer as "ANSWER: (x)" on the last line.
4. Match difficulty level of actual IBPS RRB PO Pre exam.
5. Vary question types - do NOT repeat the same type consecutively.
6. For Reasoning: rotate between seating, blood relation, inequality, coding, floor, linear.
7. For Quantitative: rotate between series, DI, simplification, word problems.
8. For English: rotate between error detection, fill in the blanks, word/vocabulary based.
9. Keep question self-contained (no "refer to passage" unless you include the passage).
10. DO NOT add explanation. Just: Question + 5 options + ANSWER line.

FORMAT EXAMPLE:
Q. [Question text here]
(a) Option A
(b) Option B
(c) Option C
(d) Option D
(e) Option E
ANSWER: (b)"""


def parse_question(raw: str):
    """Parse the model's output into a structured question dict."""
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]

    question_lines = []
    options = {}
    answer  = ""

    for line in lines:
        if line.startswith("ANSWER:"):
            answer = line.replace("ANSWER:", "").strip()
        elif line.startswith(("(a)", "(b)", "(c)", "(d)", "(e)")):
            key = line[1]          # a / b / c / d / e
            val = line[4:].strip()
            options[key] = val
        else:
            question_lines.append(line)

    question_text = " ".join(question_lines).lstrip("Q. ").strip()

    return {
        "question": question_text,
        "options":  options,
        "answer":   answer.strip("()"),   # just the letter
    }


def detect_type(text: str, section: str) -> str:
    text_lower = text.lower()
    if section == "Reasoning":
        if "row" in text_lower or "facing" in text_lower:       return "Seating Arrangement"
        if "daughter" in text_lower or "father" in text_lower:  return "Blood Relation"
        if "floor" in text_lower or "flat" in text_lower:       return "Floor Puzzle"
        if "coded" in text_lower or "code" in text_lower:       return "Coding-Decoding"
        if ">" in text_lower or "<" in text_lower:              return "Inequality"
        return "Linear Arrangement"
    elif section == "Quantitative":
        if "?" in text and any(c.isdigit() for c in text[:30]): return "Number Series"
        if "simple interest" in text_lower or "compound interest" in text_lower: return "SI/CI"
        if "profit" in text_lower or "loss" in text_lower:      return "Profit/Loss"
        if "work" in text_lower and "day" in text_lower:        return "Time/Work"
        if "%" in text_lower or "pie chart" in text_lower or "bar graph" in text_lower:
            return "Data Interpretation"
        return "Arithmetic/Simplification"
    elif section == "English":
        if "blank" in text_lower or "_____" in text or "___" in text:
            return "Fill in the Blanks"
        if "error" in text_lower or "grammatical" in text_lower or "incorrect part" in text_lower:
            return "Error Detection"
        if "passage" in text_lower or "comprehension" in text_lower:
            return "Reading Comprehension"
        if "meaningful word" in text_lower or "rearrange" in text_lower or "letters" in text_lower:
            return "Word Formation"
        return "Vocabulary/Usage"
    return "General"


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    session.clear()
    return render_template("index.html")


@app.route("/config", methods=["GET"])
def get_config():
    """Single source of truth the frontend uses to render the home screen."""
    return jsonify({
        "subjects":        list(SECTION_TIME_PER_Q.keys()),
        "question_counts": QUESTION_COUNT_CHOICES,
        "full_mock_plan": [
            {"section": p["section"], "count": p["count"],
             "time_sec": _time_for(p["section"], p["count"])}
            for p in FULL_MOCK_PLAN
        ],
    })


@app.route("/start", methods=["POST"])
def start_exam():
    data = request.json or {}
    mode = data.get("mode", "practice")

    if mode == "full":
        plan = [
            {"section": p["section"], "count": p["count"],
             "time_sec": _time_for(p["section"], p["count"])}
            for p in FULL_MOCK_PLAN
        ]
    else:
        section = data.get("section", "Reasoning")
        count   = int(data.get("count", 10))
        if section not in SECTION_TIME_PER_Q:
            return jsonify({"error": "Unknown subject"}), 400
        if count not in QUESTION_COUNT_CHOICES:
            return jsonify({"error": "Invalid question count"}), 400
        plan = [{"section": section, "count": count, "time_sec": _time_for(section, count)}]

    session.clear()
    session["mode"]          = mode
    session["plan"]          = plan
    session["plan_idx"]      = 0
    session["bank"]          = {}   # qid -> {question, options, answer, type, section}
    session["section_queue"] = []   # ordered qids for the CURRENT section
    session["history"]       = {}   # section -> recent question types (forces variety)
    session["results"]       = []   # graded sections, appended as each is submitted

    return jsonify({"status": "ok", "plan": plan})


@app.route("/generate-next", methods=["POST"])
def generate_next():
    """Generate ONE more question for the current section (called in a loop
    by the frontend so a normal request/response cycle keeps the session
    consistent — no background threads needed)."""
    plan = session.get("plan")
    idx  = session.get("plan_idx", 0)
    if not plan or idx >= len(plan):
        return jsonify({"error": "No active section"}), 400

    current = plan[idx]
    section = current["section"]
    target  = current["count"]

    queue = session.get("section_queue", [])
    if len(queue) >= target:
        return jsonify({"done": True, "generated": len(queue), "total": target})

    history    = session.get("history", {})
    sect_hist  = history.get(section, [])
    history_note = ""
    if sect_hist:
        last_types = ", ".join(sect_hist[-2:])
        history_note = f"\n\nIMPORTANT: Last question types used were [{last_types}]. Use a DIFFERENT type now."

    system = build_system_prompt(section) + history_note

    try:
        response = client.chat.completions.create(
            model    = GROQ_MODEL,
            messages = [
                {"role": "system", "content": system},
                {"role": "user",
                 "content": f"Generate 1 {section} question for IBPS RRB PO Pre exam."},
            ],
            max_completion_tokens = 1500,
            reasoning_effort       = "low",
            extra_body = {"reasoning_format": "hidden"},
        )
        raw = response.choices[0].message.content

        if not raw or not raw.strip():
            raise ValueError("Model returned empty content — try again.")

        q     = parse_question(raw)
        qtype = detect_type(q["question"], section)

        qid  = uuid.uuid4().hex[:8]
        bank = session.get("bank", {})
        bank[qid] = {
            "question": q["question"],
            "options":  q["options"],
            "answer":   q["answer"],
            "type":     qtype,
            "section":  section,
        }
        session["bank"] = bank

        queue.append(qid)
        session["section_queue"] = queue

        sect_hist.append(qtype)
        history[section] = sect_hist[-6:]
        session["history"] = history

        return jsonify({"done": len(queue) >= target, "generated": len(queue), "total": target})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/section-questions", methods=["GET"])
def section_questions():
    """Everything needed to render the exam screen — answers withheld."""
    plan = session.get("plan")
    idx  = session.get("plan_idx", 0)
    if not plan or idx >= len(plan):
        return jsonify({"error": "No active section"}), 400

    current = plan[idx]
    queue   = session.get("section_queue", [])
    bank    = session.get("bank", {})

    questions = [
        {"id": qid, "q_num": i + 1, "question": bank[qid]["question"], "options": bank[qid]["options"]}
        for i, qid in enumerate(queue)
    ]

    return jsonify({
        "section":       current["section"],
        "section_num":   idx + 1,
        "total_sections": len(plan),
        "total":         current["count"],
        "time_sec":      current["time_sec"],
        "questions":     questions,
    })


@app.route("/submit-section", methods=["POST"])
def submit_section():
    """Grade the current section server-side (no correctness is echoed back
    here — that only happens in /final-result) and advance the plan."""
    data       = request.json or {}
    answers    = data.get("answers", {}) or {}
    time_taken = data.get("time_taken_sec")

    plan = session.get("plan")
    idx  = session.get("plan_idx", 0)
    if not plan or idx >= len(plan):
        return jsonify({"error": "No active section"}), 400

    current = plan[idx]
    queue   = session.get("section_queue", [])
    bank    = session.get("bank", {})

    items, score, attempted = [], 0, 0
    for i, qid in enumerate(queue):
        b           = bank[qid]
        raw_user    = answers.get(qid)
        user_ans    = raw_user.lower().strip("()") if raw_user else None
        correct_ans = (b["answer"] or "").lower().strip("()")
        is_correct  = bool(user_ans) and user_ans == correct_ans

        if user_ans:
            attempted += 1
        if is_correct:
            score += 1

        items.append({
            "qid": qid, "q_num": i + 1,
            "question": b["question"], "options": b["options"],
            "user_ans": user_ans, "correct_ans": correct_ans,
            "is_correct": is_correct, "type": b["type"],
        })

    results = session.get("results", [])
    results.append({
        "section":          current["section"],
        "score":            score,
        "total":            current["count"],
        "attempted":        attempted,
        "time_allotted_sec": current["time_sec"],
        "time_taken_sec":   time_taken,
        "items":            items,
    })
    session["results"] = results

    session["plan_idx"]      = idx + 1
    session["section_queue"] = []

    finished     = session["plan_idx"] >= len(plan)
    next_section = plan[session["plan_idx"]]["section"] if not finished else None

    return jsonify({"finished": finished, "next_section": next_section})


@app.route("/final-result", methods=["GET"])
def final_result():
    """Only NOW do we reveal correct answers, per-question correctness, and
    a topic-wise accuracy breakdown so the candidate can see exactly which
    question types need work."""
    results = session.get("results", [])
    mode    = session.get("mode", "practice")

    total_score      = sum(r["score"] for r in results)
    total_qs         = sum(r["total"] for r in results)
    total_attempted  = sum(r["attempted"] for r in results)
    pct              = round((total_score / total_qs * 100) if total_qs else 0, 1)

    topic_stats = {}   # type -> {correct, attempted, total}
    for r in results:
        for it in r["items"]:
            s = topic_stats.setdefault(it["type"], {"correct": 0, "attempted": 0, "total": 0})
            s["total"] += 1
            if it["user_ans"]:
                s["attempted"] += 1
            if it["is_correct"]:
                s["correct"] += 1

    topics = []
    for t, s in topic_stats.items():
        acc = round((s["correct"] / s["attempted"] * 100) if s["attempted"] else 0, 1)
        topics.append({"topic": t, "accuracy": acc, **s})
    topics.sort(key=lambda x: x["accuracy"])   # weakest first

    weak_topics = [t["topic"] for t in topics if t["attempted"] > 0 and t["accuracy"] < 60][:5]

    sections = [{
        "section":           r["section"],
        "score":             r["score"],
        "total":             r["total"],
        "attempted":         r["attempted"],
        "time_allotted_sec": r["time_allotted_sec"],
        "time_taken_sec":    r["time_taken_sec"],
    } for r in results]

    return jsonify({
        "mode":        mode,
        "score":       total_score,
        "total":       total_qs,
        "attempted":   total_attempted,
        "percent":     pct,
        "grade":       get_grade(pct),
        "sections":    sections,
        "topics":      topics,
        "weak_topics": weak_topics,
        "review":      results,   # full per-question detail, safe to show now
    })


def get_grade(pct):
    if pct >= 90: return "Excellent - IBPS Cut-off Cleared!"
    if pct >= 70: return "Good - Near Cut-off"
    if pct >= 50: return "Average - Need More Practice"
    return "Below Average - Revise Concepts"


if __name__ == "__main__":
    # use_reloader=False is important here: the reloader's file-watcher
    # would otherwise restart the whole process every time Flask-Session
    # writes a session file into .flask_session/, killing requests mid-flight.
    app.run(debug=True, port=5000, use_reloader=False)
