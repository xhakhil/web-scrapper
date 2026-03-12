
Currently supported platforms:
- Alison
- Florence Academy
- Praxhub

Running 

- pip install -r requirements.txt

- playwright install

streamlit run ui.py 
or 
python -m streamlit run ui.py


http://localhost:8501




env files 

# Alison
ALISON_EMAIL=your_email
ALISON_PASSWORD=your_password

# Florence
FLORENCE_EMAIL=your_email
FLORENCE_PASSWORD=your_password

# Praxhub
EMAIL=your_email
PASSWORD=your_password

# Gemini
GEMINI_API_KEY=your_api_key
GEMINI_PROMPT=Rewrite the course content clearly

# Optional
OUTPUT_FILE=lesson_output.txt
HEADLESS=True