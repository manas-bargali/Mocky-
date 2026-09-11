/* ── Mocky Frontend ───────────────────────────────────────────── */

const ICONS = { Reasoning: "🧠", Quantitative: "🔢", English: "📖" };

let CONFIG = null;

/* Current section state */
let currentSectionMeta = null;  // {section, section_num, total_sections, total, time_sec}
let questions   = [];           // [{id, q_num, question, options}]
let answers     = {};           // qid -> selected letter
let visited     = {};           // qid -> true
let currentIndex = 0;
let timerInterval = null;
let timeRemaining  = 0;         // seconds
let sectionStartTime = null;

/* ── Helpers ──────────────────────────────────────────────────── */
function switchScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById("screen-" + name).classList.add("active");
}

function fmtTime(sec) {
  if (sec === null || sec === undefined) return "--";
  sec = Math.max(0, Math.round(sec));
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/* ── Home screen: build from /config ─────────────────────────── */
async function loadConfig() {
  const r = await fetch("/config");
  CONFIG = await r.json();
  renderHome();
}

function renderHome() {
  const list = document.getElementById("subject-list");
  list.innerHTML = "";

  CONFIG.subjects.forEach(subject => {
    const row = document.createElement("div");
    row.className = "subject-row";

    const name = document.createElement("div");
    name.className = "subject-name";
    name.textContent = `${ICONS[subject] || "📘"} ${subject}`;

    const pills = document.createElement("div");
    pills.className = "count-pills";
    CONFIG.question_counts.forEach(c => {
      const btn = document.createElement("button");
      btn.className = "pill";
      btn.textContent = `${c} Qs`;
      btn.addEventListener("click", () => startTest("practice", subject, c));
      pills.appendChild(btn);
    });

    row.appendChild(name);
    row.appendChild(pills);
    list.appendChild(row);
  });

  const fm = CONFIG.full_mock_plan;
  const totalQ   = fm.reduce((s, p) => s + p.count, 0);
  const totalMin = Math.round(fm.reduce((s, p) => s + p.time_sec, 0) / 60);
  const desc = fm.map(p => `${p.section} ${p.count}Q · ${Math.round(p.time_sec / 60)}m`).join("  +  ");

  document.getElementById("fullmock-desc").textContent = desc;
  document.getElementById("fullmock-meta").textContent =
    `${totalQ} Questions · ${totalMin} Minutes · ${fm.length} Sections`;
}

document.getElementById("btn-fullmock").addEventListener("click", () => startTest("full"));

/* ── Start a test (practice or full) ─────────────────────────── */
async function startTest(mode, section, count) {
  const body = mode === "practice" ? { mode, section, count } : { mode };
  await fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  switchScreen("loading");
  await generateSection();
}

/* ── Generate all questions for the current section, one at a time,
     showing progress (keeps each call a normal request so the server
     session stays consistent — no background threads needed) ─────── */
async function generateSection() {
  document.getElementById("loading-title").textContent = "Preparing your section…";
  document.getElementById("progress-fill").style.width = "0%";
  document.getElementById("progress-text").textContent = "Starting…";

  let done = false;
  while (!done) {
    const r = await fetch("/generate-next", { method: "POST" });
    const data = await r.json();

    if (data.error) {
      document.getElementById("loading-title").textContent = `Error: ${data.error}`;
      return;
    }

    done = data.done;
    const pct = data.total ? Math.round((data.generated / data.total) * 100) : 0;
    document.getElementById("progress-fill").style.width = pct + "%";
    document.getElementById("progress-text").textContent =
      `${data.generated} / ${data.total} questions generated`;
  }

  await loadSectionQuestions();
}

async function loadSectionQuestions() {
  const r = await fetch("/section-questions");
  const data = await r.json();

  currentSectionMeta = data;
  questions = data.questions;
  answers = {};
  visited = {};
  currentIndex = 0;
  timeRemaining = data.time_sec;
  sectionStartTime = Date.now();

  document.getElementById("section-label").textContent = data.section;
  document.getElementById("section-progress").textContent =
    data.total_sections > 1 ? `Section ${data.section_num} of ${data.total_sections}` : "";
  document.getElementById("q-total").textContent = data.total;

  buildPalette();
  renderQuestion(0);
  startTimer();
  switchScreen("exam");
}

/* ── Palette ──────────────────────────────────────────────────── */
function buildPalette() {
  const grid = document.getElementById("palette-grid");
  grid.innerHTML = "";
  questions.forEach((q, i) => {
    const btn = document.createElement("button");
    btn.className = "palette-btn";
    btn.textContent = i + 1;
    btn.addEventListener("click", () => renderQuestion(i));
    grid.appendChild(btn);
  });
  refreshPalette();
}

function refreshPalette() {
  const btns = document.querySelectorAll(".palette-btn");
  btns.forEach((btn, i) => {
    const qid = questions[i].id;
    btn.classList.remove("answered", "visited", "current");
    if (i === currentIndex) btn.classList.add("current");
    else if (answers[qid]) btn.classList.add("answered");
    else if (visited[qid]) btn.classList.add("visited");
  });
}

/* ── Question rendering (no correctness feedback ever shown here) ─ */
function renderQuestion(index) {
  currentIndex = index;
  const q = questions[index];
  visited[q.id] = true;

  document.getElementById("q-num").textContent = index + 1;
  document.getElementById("question-text").textContent = q.question;

  const box = document.getElementById("options-box");
  box.innerHTML = "";
  const order = ["a", "b", "c", "d", "e"];
  order.forEach(key => {
    if (!q.options[key]) return;
    const btn = document.createElement("button");
    btn.className = "option-btn";
    if (answers[q.id] === key) btn.classList.add("selected");
    btn.innerHTML = `<span class="opt-label">(${key})</span><span>${q.options[key]}</span>`;
    btn.addEventListener("click", () => selectOption(btn, q.id, key));
    box.appendChild(btn);
  });

  document.getElementById("btn-prev").disabled = index === 0;
  document.getElementById("btn-next").textContent =
    (index === questions.length - 1) ? "Save ✓" : "Save & Next →";

  refreshPalette();
}

function selectOption(btn, qid, key) {
  answers[qid] = key;
  document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
  refreshPalette();
}

/* ── Navigation ───────────────────────────────────────────────── */
document.getElementById("btn-prev").addEventListener("click", () => {
  if (currentIndex > 0) renderQuestion(currentIndex - 1);
});

document.getElementById("btn-next").addEventListener("click", () => {
  if (currentIndex < questions.length - 1) renderQuestion(currentIndex + 1);
});

document.getElementById("btn-clear").addEventListener("click", () => {
  const q = questions[currentIndex];
  delete answers[q.id];
  renderQuestion(currentIndex);
});

document.getElementById("btn-palette-toggle").addEventListener("click", () => {
  document.getElementById("palette-panel").classList.toggle("open");
});

document.getElementById("btn-submit-section").addEventListener("click", () => {
  const total = questions.length;
  const answeredCount = Object.keys(answers).length;
  const unanswered = total - answeredCount;
  const msg = unanswered > 0
    ? `You have ${unanswered} unanswered question(s) in this section. Submit anyway?`
    : "Submit this section? You won't be able to change answers after this.";
  if (confirm(msg)) submitSection(false);
});

/* ── Timer ────────────────────────────────────────────────────── */
function startTimer() {
  clearInterval(timerInterval);
  updateTimerDisplay();
  timerInterval = setInterval(() => {
    timeRemaining--;
    updateTimerDisplay();
    if (timeRemaining <= 0) {
      clearInterval(timerInterval);
      submitSection(true);
    }
  }, 1000);
}

function updateTimerDisplay() {
  const el = document.getElementById("timer");
  el.textContent = fmtTime(timeRemaining);
  el.classList.toggle("timer-low", timeRemaining <= 60);
}

/* ── Submit section (grading happens server-side, nothing revealed) ─ */
async function submitSection(auto) {
  clearInterval(timerInterval);
  const timeTaken = Math.round((Date.now() - sectionStartTime) / 1000);

  const r = await fetch("/submit-section", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, time_taken_sec: timeTaken }),
  });
  const data = await r.json();

  if (data.finished) {
    await showFinalResult();
    return;
  }

  switchScreen("transition");
  document.getElementById("transition-text").textContent =
    auto ? "Time's up! Section submitted." : "Section submitted!";
  document.getElementById("transition-next").textContent = `Next up: ${data.next_section}`;

  setTimeout(async () => {
    switchScreen("loading");
    await generateSection();
  }, 1800);
}

/* ── Final result & analysis ─────────────────────────────────── */
async function showFinalResult() {
  const r = await fetch("/final-result");
  const data = await r.json();
  renderResult(data);
  switchScreen("result");
}

function renderResult(data) {
  document.getElementById("result-score").textContent = `${data.score}/${data.total}`;
  document.getElementById("result-pct").textContent   = `${data.percent}%`;
  document.getElementById("result-grade").textContent = data.grade;

  /* Section-wise breakdown */
  const sb = document.getElementById("section-breakdown");
  sb.innerHTML = "";
  data.sections.forEach(s => {
    const pct = s.total ? Math.round((s.score / s.total) * 100) : 0;
    const div = document.createElement("div");
    div.className = "section-card";
    div.innerHTML = `
      <div class="section-card-name">${s.section}</div>
      <div class="section-card-score">${s.score}/${s.total} <span class="section-card-pct">(${pct}%)</span></div>
      <div class="section-card-meta">Attempted ${s.attempted}/${s.total} · Time ${fmtTime(s.time_taken_sec)} / ${fmtTime(s.time_allotted_sec)}</div>
    `;
    sb.appendChild(div);
  });

  /* Topic-wise weak-area analysis */
  const ta = document.getElementById("topic-analysis");
  ta.innerHTML = "";

  if (data.weak_topics && data.weak_topics.length) {
    const note = document.createElement("p");
    note.className = "weak-summary";
    note.textContent = `Focus areas: ${data.weak_topics.join(", ")}`;
    ta.appendChild(note);
  }

  data.topics.forEach(t => {
    const weak = t.attempted > 0 && t.accuracy < 60;
    const row = document.createElement("div");
    row.className = "topic-row";
    row.innerHTML = `
      <div class="topic-row-top">
        <span class="topic-name">${t.topic} ${weak ? '<span class="tag-weak">Needs Work</span>' : ""}</span>
        <span class="topic-acc">${t.accuracy}%</span>
      </div>
      <div class="topic-bar-track"><div class="topic-bar-fill ${weak ? "weak" : ""}" style="width:${t.accuracy}%"></div></div>
      <div class="topic-meta">${t.correct} correct · ${t.attempted} attempted · ${t.total} appeared</div>
    `;
    ta.appendChild(row);
  });

  /* Full answer review — revealed only now */
  const review = document.getElementById("answer-review");
  review.innerHTML = "";

  data.review.forEach(section => {
    if (data.mode === "full") {
      const h = document.createElement("p");
      h.className = "review-section-title";
      h.textContent = section.section;
      review.appendChild(h);
    }

    section.items.forEach(a => {
      const status = a.user_ans == null ? "unattempted-item" : (a.is_correct ? "correct-item" : "wrong-item");
      const div = document.createElement("div");
      div.className = "review-item " + status;

      const label = document.createElement("div");
      label.className = "review-label " + (a.user_ans == null ? "u" : (a.is_correct ? "c" : "w"));
      label.textContent = a.user_ans == null
        ? `Q${a.q_num} ⏺ Not Attempted`
        : (a.is_correct ? `Q${a.q_num} ✅ Correct` : `Q${a.q_num} ❌ Wrong`);

      const tag = document.createElement("span");
      tag.className = "topic-tag";
      tag.textContent = a.type;
      label.appendChild(tag);

      const qtext = document.createElement("div");
      qtext.className = "review-qtext";
      qtext.textContent = a.question;

      const ans = document.createElement("div");
      ans.className = "review-ans";
      ans.textContent = a.user_ans == null
        ? `Correct answer: (${a.correct_ans})`
        : (a.is_correct ? `Your answer: (${a.user_ans}) ✓` : `Your answer: (${a.user_ans})  ·  Correct: (${a.correct_ans})`);

      div.appendChild(label);
      div.appendChild(qtext);
      div.appendChild(ans);
      review.appendChild(div);
    });
  });
}

/* ── Go home ──────────────────────────────────────────────────── */
function goHome() {
  switchScreen("home");
}

loadConfig();
