"""
Mocky - IBPS RRB Mock Test Platform
Context Engineering + RAG from real IBPS RRB Pre 2024 paper
API key is baked in — just run: python app.py
"""

from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import json
import os

app = Flask(__name__)
app.secret_key = "mocky_ibps_2024_secret"

# ── API KEY (read from environment — never hardcode a key in source) ─────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY environment variable is not set.\n"
        "Get a free key at https://console.groq.com/keys, then either:\n"
        "  - run via run.sh / run.bat (it will prompt you), or\n"
        "  - export GROQ_API_KEY=your_key_here   (Linux/Mac/Termux)\n"
        "  - set GROQ_API_KEY=your_key_here      (Windows cmd)"
    )

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Load RAG data ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "data", "ibps_patterns.json")) as f:
    IBPS_PATTERNS = json.load(f)

# ── Context Engineering: system prompt with real paper patterns ───────────────
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
8. Keep question self-contained (include full passage/setup if needed).
9. DO NOT add explanation. Just: Question + 5 options + ANSWER line.

FORMAT — follow EXACTLY:
Q. [Question text here]
(a) Option A
(b) Option B
(c) Option C
(d) Option D
(e) Option E
ANSWER: (b)"""


def parse_question(raw: str):
    """Parse Claude's output into structured dict."""
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    question_lines, options, answer = [], {}, ""

    for line in lines:
        if line.startswith("ANSWER:"):
            answer = line.replace("ANSWER:", "").strip()
        elif line.startswith(("(a)", "(b)", "(c)", "(d)", "(e)")):
            key = line[1]
            val = line[4:].strip()
            options[key] = val
        else:
            question_lines.append(line)

    question_text = " ".join(question_lines).lstrip("Q. ").strip()
    return {
        "question": question_text,
        "options":  options,
        "answer":   answer.strip("()"),
    }


def detect_type(text: str, section: str) -> str:
    t = text.lower()
    if section == "Reasoning":
        if "row" in t or "facing" in t:            return "Seating"
        if "daughter" in t or "father" in t:       return "Blood Relation"
        if "floor" in t or "flat" in t:            return "Floor Puzzle"
        if "coded" in t or "code" in t:            return "Coding"
        if ">" in t or "<" in t:                   return "Inequality"
        return "Linear Arrangement"
    elif section == "Quantitative":
        if "?" in text and any(c.isdigit() for c in text[:30]): return "Number Series"
        if "simple interest" in t or "compound interest" in t:  return "SI/CI"
        if "profit" in t or "loss" in t:           return "Profit/Loss"
        if "work" in t and "day" in t:             return "Time/Work"
        if "%" in t:                               return "Percentage/DI"
        return "Arithmetic"
    return "General"


def get_grade(pct):
    if pct >= 90: return "Excellent — IBPS Cut-off Cleared! 🎉"
    if pct >= 70: return "Good — Near Cut-off 👍"
    if pct >= 50: return "Average — Need More Practice 📚"
    return "Below Average — Revise Concepts 💪"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    session.clear()
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start_exam():
    data    = request.json
    section = data.get("section", "Reasoning")
    session["section"] = section
    session["score"]   = 0
    session["total"]   = 0
    session["answers"] = []
    session["history"] = []
    return jsonify({"status": "ok", "section": section})


@app.route("/question", methods=["GET"])
def get_question():
    section = session.get("section", "Reasoning")
    history = session.get("history", [])

    history_note = ""
    if history:
        last_types   = ", ".join(history[-2:])
        history_note = f"\n\nIMPORTANT: Last types used [{last_types}]. Use a DIFFERENT type now."

    system = build_system_prompt(section) + history_note

    try:
        response = client.chat.completions.create(
            model      = GROQ_MODEL,
            max_tokens = 500,
            messages   = [
                {"role": "system", "content": system},
                {"role": "user",
                 "content": f"Generate 1 {section} question for IBPS RRB PO Pre exam."}
            ]
        )
        raw = response.choices[0].message.content
        q   = parse_question(raw)

        qtype = detect_type(q["question"], section)
        history.append(qtype)
        session["history"]          = history[-6:]
        session["current_answer"]   = q["answer"]
        session["current_question"] = q["question"]

        return jsonify({
            "question": q["question"],
            "options":  q["options"],
            "q_num":    session.get("total", 0) + 1,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/submit", methods=["POST"])
def submit_answer():
    data        = request.json
    user_ans    = data.get("answer", "").lower().strip("()")
    correct_ans = session.get("current_answer", "").lower().strip("()")
    is_correct  = (user_ans == correct_ans)

    session["total"] = session.get("total", 0) + 1
    if is_correct:
        session["score"] = session.get("score", 0) + 1

    answers = session.get("answers", [])
    answers.append({
        "q_num":      session["total"],
        "question":   session.get("current_question", ""),
        "user_ans":   user_ans,
        "correct":    correct_ans,
        "is_correct": is_correct,
    })
    session["answers"] = answers

    return jsonify({
        "is_correct":  is_correct,
        "correct_ans": correct_ans,
        "score":       session["score"],
        "total":       session["total"],
    })


@app.route("/result", methods=["GET"])
def get_result():
    score   = session.get("score", 0)
    total   = session.get("total", 0)
    answers = session.get("answers", [])
    section = session.get("section", "")
    pct     = round((score / total * 100) if total else 0, 1)

    return jsonify({
        "score":   score,
        "total":   total,
        "percent": pct,
        "section": section,
        "answers": answers,
        "grade":   get_grade(pct),
    })


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Mocky — IBPS RRB Mock Test")
    print("  Open in browser: http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
