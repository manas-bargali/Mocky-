# 📝 Mocky – IBPS RRB PO Prelims Mock Test

AI-powered mock test app using **Context Engineering** + **RAG** from the real IBPS RRB PO Pre 2024 paper, generating questions live via Groq.

---

## 🆕 What's in this version

- **Sectional practice** — pick a subject (Reasoning / Quantitative / English) and how many questions to attempt: **10, 15, or 30**, same options for every subject.
- **Full-Length Mock** — a 4th mode that runs all 3 sections back-to-back using the **real IBPS RRB PO Pre 2024 pattern**: Reasoning 40 Q / 25 min, Quantitative 40 Q / 20 min, plus the standard IBPS English sectional timing (30 Q / 20 min), since RRB Pre itself has no English section but Mocky offers it as a 3rd subject.
- **Real exam pacing** — every timer is derived from that same official per-question pace, not an arbitrary guess:
  | Subject | Real pattern | Per-question pace |
  |---|---|---|
  | Reasoning | 40 Q / 25 min | 37.5 sec/Q |
  | Quantitative | 40 Q / 20 min | 30 sec/Q |
  | English | 30 Q / 20 min | 40 sec/Q |
- **No mid-test feedback** — selecting an option just highlights it. Correctness, the answer key, and all analysis are withheld until you hit **Submit**.
- **Exam-style navigation** — question palette (answered / not-answered / not-visited), Previous/Next, Clear Response, jump to any question.
- **Post-submit analysis** — score, section-wise breakdown (for the full mock), and a **topic-wise accuracy table** (e.g. Seating Arrangement, Blood Relation, Number Series, SI/CI…) so you can see exactly which question types are dragging your score down, sorted weakest-first with a "Needs Work" flag under 60% accuracy.

---

## 🏗️ Architecture

```
mocky/
├── app.py                  ← Flask backend (RAG + Context Engineering)
├── data/
│   └── ibps_patterns.json  ← RAG: real paper patterns stored here
├── templates/
│   └── index.html          ← Single-page UI (5 screens)
├── static/
│   ├── css/style.css
│   └── js/app.js
└── requirements.txt
```

## ⚙️ How It Works

### Context Engineering
System prompt is built dynamically with:
- Real question types from the actual IBPS RRB 2024 paper
- Actual examples from the paper
- History of the last 2 question types per section → forces variety

### RAG (Retrieval Augmented Generation)
- `ibps_patterns.json` = your "vector store" (the paper knowledge)
- On each request, the relevant section's patterns are retrieved and injected into context
- The model generates questions SIMILAR to the real paper, not random

### Exam flow
1. `/start` records the plan (one section for practice, or the full 3-section pattern for a Full Mock).
2. `/generate-next` is called in a loop by the frontend, one question at a time, so the whole section is generated *before* the timer starts — this is what allows free navigation (Previous/jump-to-question) like a real exam, instead of a one-at-a-time quiz.
3. `/section-questions` hands the frontend the question set **without answers**.
4. `/submit-section` grades everything server-side and just tells the frontend whether to move to the next section or the test is finished — no correctness is echoed back here.
5. `/final-result` is the only place the answer key, per-question correctness, and the topic-wise breakdown are revealed.

### Sessions
A Full Mock holds 110+ generated questions with full text/options — too big for Flask's default signed-cookie session. This version uses **Flask-Session** with a filesystem backend (`.flask_session/`, auto-created, git-ignore it) so session data lives server-side instead.

### API Usage
- Uses Groq's OpenAI-compatible endpoint with `openai/gpt-oss-120b`
- One Groq call per question, made just-in-time as each section is prepared
- A Full Mock makes 110 calls total (spread across 3 section-preparation screens, not all at once)

---

## 🚀 Setup

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Set API Key
```bash
# Linux/Mac
export GROQ_API_KEY=your_key_here

# Windows
set GROQ_API_KEY=your_key_here
```

### 3. Run
```bash
python app.py
```

Open `http://localhost:5000`

---

## 📱 Android?
Yes! Use **Termux** on Android:
```bash
pkg install python
pip install -r requirements.txt
export GROQ_API_KEY=your_key
python app.py
```
Then open `http://localhost:5000` in your phone browser.

---

## 🔑 What You Need
- Python 3.9+
- A Groq API key (from console.groq.com)
- That's it. No database, no complex setup.

---

## 💡 How to Extend
- Add more question types to `data/ibps_patterns.json` per subject to widen variety.
- Add a 4th/5th practice subject by adding it to `SECTION_TIME_PER_Q` in `app.py` and to `ibps_patterns.json`.
- Change `QUESTION_COUNT_CHOICES` in `app.py` to offer different practice sizes.
- Adjust `FULL_MOCK_PLAN` in `app.py` if IBPS changes the official pattern in a future year.
