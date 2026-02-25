# Personal Link Dashboard

A minimal, fast local dashboard for your browser's new tab page.

## Stack used here
- **Python 3** (`http.server`) for a tiny local backend
- **SQLite** for persistent storage
- **Vanilla HTML/CSS/JS** for a fast-loading UI

## Features
- Links grouped by category
- Add, edit, delete links
- Create and delete categories
- SQLite persistence (`dashboard.db`)

## Run locally
```bash
python3 app.py
```

Then open: http://127.0.0.1:8000

## Notes
- Deleting a category is blocked if it still has links.
- At least one category must always remain.
