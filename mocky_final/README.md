# 📝 Mocky — IBPS RRB PO Prelims Mock Test

AI-powered mock using real Aug 2024 paper pattern. Runs on Groq's free API (Llama 3.3 70B).

---

## ▶️ HOW TO RUN

### Windows
```
Double-click run.bat
```
It will ask for your Groq API key the first time (get one free, no card, at https://console.groq.com/keys).

### Linux / Mac
```bash
bash run.sh
```

### Android (Termux)
```bash
pkg install python
bash run.sh
```
Then open **http://localhost:5000** in your phone browser.

### Manual
```bash
pip install flask openai
export GROQ_API_KEY=your_key_here   # Windows: set GROQ_API_KEY=your_key_here
python app.py
```

---

## 📁 File Structure
```
mocky/
├── app.py                   ← Main server (reads GROQ_API_KEY from environment)
├── run.bat                  ← Windows one-click run (prompts for key)
├── run.sh                   ← Linux/Mac/Android one-click run (prompts for key)
├── requirements.txt
├── data/
│   └── ibps_patterns.json   ← RAG: real paper question patterns
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## 🔑 API Key
Never hardcode your key in `app.py`. `run.sh`/`run.bat` will ask for it and set it
as an environment variable (`GROQ_API_KEY`) for that session. To make it permanent,
add `export GROQ_API_KEY=your_key_here` to your shell profile (`.bashrc`/`.zshrc`).

## 💡 How it works
- Select section (Reasoning / Quantitative / English)
- 3 questions generated one by one using real IBPS RRB 2024 pattern, via Groq's
  free Llama 3.3 70B endpoint
- Submit → get correct/wrong feedback
- See score + grade at the end
