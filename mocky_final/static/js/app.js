/* ── Mocky Frontend ───────────────────────── */
const TOTAL_QUESTIONS = 3;

let currentQ  = 0;
let answered  = false;

/* ── Helpers ──────────────────────────────── */
function show(id)  { document.getElementById(id).style.display = ""; }
function hide(id)  { document.getElementById(id).style.display = "none"; }

function switchScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById("screen-" + name).classList.add("active");
}

/* ── Home: section buttons ────────────────── */
document.querySelectorAll(".section-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const section = btn.dataset.section;
    await startExam(section);
  });
});

async function startExam(section) {
  currentQ = 0;
  answered = false;

  await fetch("/start", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ section }),
  });

  document.getElementById("section-label").textContent = section;
  document.getElementById("score-live").textContent    = "Score: 0";
  switchScreen("exam");
  await loadQuestion();
}

/* ── Load question ────────────────────────── */
async function loadQuestion() {
  answered = false;
  hide("question-box");
  hide("feedback-box");
  show("loading");

  const r = await fetch("/question");
  const data = await r.json();

  if (data.error) {
    document.getElementById("loading").innerHTML =
      `<p style="color:#f87171">Error: ${data.error}</p>`;
    return;
  }

  hide("loading");
  show("question-box");
  hide("feedback-box");

  currentQ = data.q_num;
  document.getElementById("q-counter").textContent = `Q ${currentQ} / ${TOTAL_QUESTIONS}`;
  document.getElementById("question-text").textContent = data.question;

  // Build options
  const box = document.getElementById("options-box");
  box.innerHTML = "";
  const order = ["a","b","c","d","e"];
  order.forEach(key => {
    if (!data.options[key]) return;
    const btn = document.createElement("button");
    btn.className = "option-btn";
    btn.dataset.key = key;
    btn.innerHTML =
      `<span class="opt-label">(${key})</span><span>${data.options[key]}</span>`;
    btn.addEventListener("click", () => selectOption(btn, key));
    box.appendChild(btn);
  });
}

/* ── Option selected ──────────────────────── */
async function selectOption(btn, key) {
  if (answered) return;
  answered = true;

  btn.classList.add("selected");

  // Disable all options
  document.querySelectorAll(".option-btn").forEach(b => b.disabled = true);

  const r    = await fetch("/submit", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ answer: key }),
  });
  const data = await r.json();

  // Colour options
  document.querySelectorAll(".option-btn").forEach(b => {
    const k = b.dataset.key;
    if (k === data.correct_ans) b.classList.add("correct");
    else if (k === key && !data.is_correct) b.classList.add("wrong");
  });

  // Update score
  document.getElementById("score-live").textContent = `Score: ${data.score}`;

  // Feedback
  const fb = document.getElementById("feedback-text");
  if (data.is_correct) {
    fb.innerHTML = `<span style="color:#4ade80">✅ Correct!</span>`;
  } else {
    fb.innerHTML =
      `<span style="color:#f87171">❌ Wrong.</span> Correct answer: <strong>(${data.correct_ans})</strong>`;
  }

  show("feedback-box");

  const btnNext   = document.getElementById("btn-next");
  const btnResult = document.getElementById("btn-result");

  if (data.total >= TOTAL_QUESTIONS) {
    hide("btn-next");
    show("btn-result");
    btnResult.style.display = "inline-block";
  } else {
    show("btn-next");
    hide("btn-result");
    btnResult.style.display = "none";
  }
}

/* ── Next question ────────────────────────── */
document.getElementById("btn-next").addEventListener("click", async () => {
  await loadQuestion();
});

/* ── See result ───────────────────────────── */
document.getElementById("btn-result").addEventListener("click", async () => {
  const r    = await fetch("/result");
  const data = await r.json();
  showResult(data);
});

/* ── Show result screen ───────────────────── */
function showResult(data) {
  document.getElementById("result-score").textContent = `${data.score}/${data.total}`;
  document.getElementById("result-pct").textContent   = `${data.percent}%`;
  document.getElementById("result-grade").textContent = data.grade;

  const review = document.getElementById("answer-review");
  review.innerHTML = "<p style='font-size:0.85rem;color:#64748b;margin-bottom:10px'>Answer Review:</p>";

  (data.answers || []).forEach(a => {
    const div = document.createElement("div");
    div.className = "review-item " + (a.is_correct ? "correct-item" : "wrong-item");

    const label = document.createElement("div");
    label.className = "review-label " + (a.is_correct ? "c" : "w");
    label.textContent = a.is_correct ? `Q${a.q_num} ✅ Correct` : `Q${a.q_num} ❌ Wrong`;

    const qtext = document.createElement("div");
    qtext.style.cssText = "color:#cbd5e1;margin-top:2px;";
    qtext.textContent = a.question.substring(0, 100) + (a.question.length > 100 ? "…" : "");

    const ans = document.createElement("div");
    ans.className = "review-ans";
    ans.textContent = a.is_correct
      ? `Your answer: (${a.user_ans}) ✓`
      : `Your answer: (${a.user_ans})  Correct: (${a.correct}) `;

    div.appendChild(label);
    div.appendChild(qtext);
    div.appendChild(ans);
    review.appendChild(div);
  });

  switchScreen("result");
}

/* ── Go home ──────────────────────────────── */
function goHome() {
  switchScreen("home");
}
