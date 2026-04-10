# StyleSense AI

StyleSense AI is a Flask-based fashion styling platform with a dashboard UI, wardrobe manager, outfit recommendations, image-based styling input, virtual try-on simulation, analytics, and weather-aware outfit suggestions.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
```powershell
pip install -r requirements.txt
```
3. Create a local `.env` file in the project root with your keys:
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
SERPAPI_API_KEY=your_key_here
FLASK_SECRET_KEY=your_random_secret_here
```
4. Run the app:
```powershell
python .\backend\app.py
```
5. Open `http://127.0.0.1:5000`

## Project Layout

- `backend/` Flask app, storage, and styling engine
- `templates/` HTML pages
- `static/` CSS, JavaScript, and uploads
- `data/` local persistence files
- `datasets/` clothing dataset used by the engine

## Notes

- Keep `.env` private.
- Generated uploads, databases, and cache files are ignored by Git.
- The app works with local fallback behavior if optional API keys are not set.
