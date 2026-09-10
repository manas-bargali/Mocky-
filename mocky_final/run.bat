@echo off
echo Installing dependencies...
pip install flask openai

if "%GROQ_API_KEY%"=="" (
    set /p GROQ_API_KEY="Enter your Groq API key (from console.groq.com/keys): "
)

echo.
echo Starting Mocky...
echo Open browser at: http://localhost:5000
echo Press Ctrl+C to stop.
echo.
python app.py
pause
