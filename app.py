import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dashboard.db"
STATIC_DIR = BASE_DIR / "static"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'Favorites')"
        )
        conn.commit()
    finally:
        conn.close()


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def _serve_static(self, filename):
        file_path = STATIC_DIR / filename
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        mime_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_types.get(file_path.suffix, "text/plain"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            return self._serve_static("index.html")
        if path == "/styles.css":
            return self._serve_static("styles.css")
        if path == "/app.js":
            return self._serve_static("app.js")

        if path == "/api/categories":
            conn = get_db_connection()
            try:
                categories = [dict(row) for row in conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()]
            finally:
                conn.close()
            return self._send_json(200, categories)

        if path == "/api/links":
            conn = get_db_connection()
            try:
                rows = conn.execute(
                    """
                    SELECT l.id, l.name, l.url, l.category_id, c.name as category_name
                    FROM links l
                    JOIN categories c ON c.id = l.category_id
                    ORDER BY c.name, l.name
                    """
                ).fetchall()
                links = [dict(row) for row in rows]
            finally:
                conn.close()
            return self._send_json(200, links)

        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        payload = self._read_json()

        if path == "/api/categories":
            name = (payload.get("name") or "").strip()
            if not name:
                return self._send_json(400, {"error": "Category name is required."})
            conn = get_db_connection()
            try:
                cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                conn.commit()
                category = {"id": cur.lastrowid, "name": name}
            except sqlite3.IntegrityError:
                return self._send_json(400, {"error": "Category already exists."})
            finally:
                conn.close()
            return self._send_json(201, category)

        if path == "/api/links":
            name = (payload.get("name") or "").strip()
            url = (payload.get("url") or "").strip()
            category_id = payload.get("category_id")
            if not name or not url or not category_id:
                return self._send_json(400, {"error": "Name, URL and category are required."})

            conn = get_db_connection()
            try:
                category = conn.execute(
                    "SELECT id FROM categories WHERE id = ?", (category_id,)
                ).fetchone()
                if not category:
                    return self._send_json(400, {"error": "Selected category does not exist."})
                cur = conn.execute(
                    "INSERT INTO links (name, url, category_id) VALUES (?, ?, ?)",
                    (name, url, category_id),
                )
                conn.commit()
                link = {
                    "id": cur.lastrowid,
                    "name": name,
                    "url": url,
                    "category_id": category_id,
                }
            finally:
                conn.close()
            return self._send_json(201, link)

        self.send_error(404)

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/links/"):
            return self.send_error(404)

        link_id = path.split("/")[-1]
        payload = self._read_json()
        name = (payload.get("name") or "").strip()
        url = (payload.get("url") or "").strip()
        category_id = payload.get("category_id")

        if not name or not url or not category_id:
            return self._send_json(400, {"error": "Name, URL and category are required."})

        conn = get_db_connection()
        try:
            exists = conn.execute("SELECT id FROM links WHERE id = ?", (link_id,)).fetchone()
            if not exists:
                return self._send_json(404, {"error": "Link not found."})

            category = conn.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
            if not category:
                return self._send_json(400, {"error": "Selected category does not exist."})

            conn.execute(
                "UPDATE links SET name = ?, url = ?, category_id = ? WHERE id = ?",
                (name, url, category_id, link_id),
            )
            conn.commit()
        finally:
            conn.close()

        return self._send_json(200, {"id": int(link_id), "name": name, "url": url, "category_id": category_id})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/links/"):
            link_id = path.split("/")[-1]
            conn = get_db_connection()
            try:
                cur = conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
                conn.commit()
                if cur.rowcount == 0:
                    return self._send_json(404, {"error": "Link not found."})
            finally:
                conn.close()
            return self._send_json(204, {})

        if path.startswith("/api/categories/"):
            category_id = path.split("/")[-1]
            conn = get_db_connection()
            try:
                remaining = conn.execute(
                    "SELECT COUNT(*) as count FROM categories"
                ).fetchone()["count"]
                if remaining <= 1:
                    return self._send_json(400, {"error": "At least one category is required."})

                has_links = conn.execute(
                    "SELECT COUNT(*) as count FROM links WHERE category_id = ?",
                    (category_id,),
                ).fetchone()["count"]
                if has_links:
                    return self._send_json(400, {"error": "Move or delete links first."})

                cur = conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                conn.commit()
                if cur.rowcount == 0:
                    return self._send_json(404, {"error": "Category not found."})
            finally:
                conn.close()
            return self._send_json(204, {})

        self.send_error(404)


def run(host="127.0.0.1", port=8000):
    init_db()
    server = HTTPServer((host, port), DashboardHandler)
    print(f"Dashboard running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
