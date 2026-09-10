#!/bin/bash
echo "Installing dependencies..."
pip install flask openai --break-system-packages 2>/dev/null || pip install flask openai

if [ -z "$GROQ_API_KEY" ]; then
  read -p "Enter your Groq API key (from console.groq.com/keys): " GROQ_API_KEY
  export GROQ_API_KEY
fi

echo ""
echo "Starting Mocky..."
echo "Open browser at: http://localhost:5000"
echo "Press Ctrl+C to stop."
echo ""
python app.py
