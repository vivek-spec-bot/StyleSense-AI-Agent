from __future__ import annotations

import json
import os
import sqlite3
import uuid
from copy import deepcopy
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


class DataStore:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.upload_dir = os.path.join(base_dir, "static", "uploads")
        self.db_path = os.path.join(self.data_dir, "stylesense.db")
        self.legacy_state_path = os.path.join(self.data_dir, "state.json")
        self.json_state_path = os.path.join(self.data_dir, "state_v2.json")
        self.use_sqlite = True
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        name TEXT NOT NULL,
                        style_personality TEXT NOT NULL,
                        body_type TEXT NOT NULL,
                        climate TEXT NOT NULL,
                        preferred_palette TEXT NOT NULL,
                        style_dna TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS wardrobe_items (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        color TEXT NOT NULL,
                        season TEXT NOT NULL,
                        occasion TEXT NOT NULL,
                        fabric TEXT NOT NULL,
                        pattern TEXT NOT NULL,
                        image_hint TEXT,
                        image_url TEXT,
                        favorite INTEGER NOT NULL DEFAULT 0,
                        times_worn INTEGER NOT NULL DEFAULT 0
                    );
                    CREATE TABLE IF NOT EXISTS outfit_history (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        occasion TEXT NOT NULL,
                        weather TEXT NOT NULL,
                        mood TEXT NOT NULL,
                        items_json TEXT NOT NULL,
                        score REAL NOT NULL,
                        liked INTEGER NOT NULL DEFAULT 0,
                        date TEXT NOT NULL,
                        style_request TEXT NOT NULL DEFAULT ''
                    );
                    CREATE TABLE IF NOT EXISTS community_feed (
                        id TEXT PRIMARY KEY,
                        creator TEXT NOT NULL,
                        title TEXT NOT NULL,
                        style TEXT NOT NULL,
                        likes INTEGER NOT NULL,
                        saves INTEGER NOT NULL,
                        trend TEXT NOT NULL
                    );
                    """
                )
            self._seed_if_needed()
            self._ensure_schema_updates()
        except sqlite3.Error:
            self.use_sqlite = False
            self._ensure_json_storage()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _seed_if_needed(self) -> None:
        with self._connect() as connection:
            user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            feed_count = connection.execute("SELECT COUNT(*) FROM community_feed").fetchone()[0]
        if user_count == 0:
            self._seed_database()
        if feed_count == 0:
            self._seed_feed()

    def _ensure_schema_updates(self) -> None:
        if not self.use_sqlite:
            return
        with self._connect() as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(outfit_history)").fetchall()}
            if "style_request" not in columns:
                connection.execute("ALTER TABLE outfit_history ADD COLUMN style_request TEXT NOT NULL DEFAULT ''")

    def _seed_database(self) -> None:
        demo_password = generate_password_hash("demo123")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    email, password_hash, name, style_personality, body_type, climate,
                    preferred_palette, style_dna
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "demo@stylesense.ai",
                    demo_password,
                    "Avery",
                    "Modern Minimalist",
                    "Athletic",
                    "Warm tropical",
                    json.dumps(["Sand", "Charcoal", "Sage", "Ivory"]),
                    json.dumps(["clean lines", "smart layering", "soft neutrals", "athleisure balance"]),
                ),
            )
            user_id = cursor.lastrowid
            wardrobe_items = [
                ("itm-linen-shirt", "Linen Camp Shirt", "Top", "Ivory", "Summer", "Casual", "Linen", "Solid", "light breathable shirt", None, 1, 8),
                ("itm-tailored-trouser", "Tailored Pleated Trouser", "Bottom", "Charcoal", "All Season", "Formal", "Wool Blend", "Solid", "clean pleated trouser", None, 0, 4),
                ("itm-knit-polo", "Textured Knit Polo", "Top", "Sage", "Spring", "Smart Casual", "Cotton Knit", "Rib", "soft knit polo", None, 1, 6),
                ("itm-sneaker", "Retro Court Sneaker", "Shoes", "White", "All Season", "Casual", "Leather", "Solid", "low top sneaker", None, 1, 13),
                ("itm-blazer", "Soft Structure Blazer", "Outerwear", "Navy", "Winter", "Formal", "Twill", "Micro check", "tailored blazer", None, 0, 3),
            ]
            connection.executemany(
                """
                INSERT INTO wardrobe_items (
                    id, user_id, name, category, color, season, occasion, fabric, pattern,
                    image_hint, image_url, favorite, times_worn
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(item_id, user_id, *values) for item_id, *values in wardrobe_items],
            )
            outfit_history = [
                ("outfit-001", "Airport Smart Casual", "Travel", "Mild", "Relaxed", json.dumps(["Textured Knit Polo", "Tailored Pleated Trouser", "Retro Court Sneaker"]), 92, 1, "2026-04-05", ""),
                ("outfit-002", "Gallery Evening", "Evening Event", "Warm", "Elevated", json.dumps(["Linen Camp Shirt", "Tailored Pleated Trouser", "Soft Structure Blazer"]), 88, 1, "2026-04-07", ""),
            ]
            connection.executemany(
                """
                INSERT INTO outfit_history (
                    id, user_id, name, occasion, weather, mood, items_json, score, liked, date, style_request
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(outfit_id, user_id, *values) for outfit_id, *values in outfit_history],
            )

    def _seed_feed(self) -> None:
        entries = [
            ("feed-001", "Mila Studio", "Quiet luxury with vacation energy", "Resort Minimal", 248, 91, "Neutral layering"),
            ("feed-002", "Noah Street", "Tech utility remix", "Urban Techwear", 191, 75, "Utility pockets"),
            ("feed-003", "Asha Edit", "Monochrome tailoring that still feels soft", "Modern Tailored", 316, 134, "Relaxed suiting"),
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO community_feed (id, creator, title, style, likes, saves, trend)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                entries,
            )

    def _base_seed(self) -> dict:
        return {
            "users": [
                {
                    "id": 1,
                    "email": "demo@stylesense.ai",
                    "password_hash": generate_password_hash("demo123"),
                    "name": "Avery",
                    "style_personality": "Modern Minimalist",
                    "body_type": "Athletic",
                    "climate": "Warm tropical",
                    "preferred_palette": ["Sand", "Charcoal", "Sage", "Ivory"],
                    "style_dna": ["clean lines", "smart layering", "soft neutrals", "athleisure balance"],
                }
            ],
            "wardrobe_items": [
                {"id": "itm-linen-shirt", "user_id": 1, "name": "Linen Camp Shirt", "category": "Top", "color": "Ivory", "season": "Summer", "occasion": "Casual", "fabric": "Linen", "pattern": "Solid", "image_hint": "light breathable shirt", "image_url": None, "favorite": True, "times_worn": 8},
                {"id": "itm-tailored-trouser", "user_id": 1, "name": "Tailored Pleated Trouser", "category": "Bottom", "color": "Charcoal", "season": "All Season", "occasion": "Formal", "fabric": "Wool Blend", "pattern": "Solid", "image_hint": "clean pleated trouser", "image_url": None, "favorite": False, "times_worn": 4},
                {"id": "itm-knit-polo", "user_id": 1, "name": "Textured Knit Polo", "category": "Top", "color": "Sage", "season": "Spring", "occasion": "Smart Casual", "fabric": "Cotton Knit", "pattern": "Rib", "image_hint": "soft knit polo", "image_url": None, "favorite": True, "times_worn": 6},
                {"id": "itm-sneaker", "user_id": 1, "name": "Retro Court Sneaker", "category": "Shoes", "color": "White", "season": "All Season", "occasion": "Casual", "fabric": "Leather", "pattern": "Solid", "image_hint": "low top sneaker", "image_url": None, "favorite": True, "times_worn": 13},
            ],
            "outfit_history": [
                {"id": "outfit-001", "user_id": 1, "name": "Airport Smart Casual", "occasion": "Travel", "weather": "Mild", "mood": "Relaxed", "items": ["Textured Knit Polo", "Tailored Pleated Trouser", "Retro Court Sneaker"], "score": 92, "liked": True, "date": "2026-04-05"},
                {"id": "outfit-002", "user_id": 1, "name": "Gallery Evening", "occasion": "Evening Event", "weather": "Warm", "mood": "Elevated", "items": ["Linen Camp Shirt", "Tailored Pleated Trouser", "Soft Structure Blazer"], "score": 88, "liked": True, "date": "2026-04-07"},
            ],
            "community_feed": [
                {"id": "feed-001", "creator": "Mila Studio", "title": "Quiet luxury with vacation energy", "style": "Resort Minimal", "likes": 248, "saves": 91, "trend": "Neutral layering"},
                {"id": "feed-002", "creator": "Noah Street", "title": "Tech utility remix", "style": "Urban Techwear", "likes": 191, "saves": 75, "trend": "Utility pockets"},
                {"id": "feed-003", "creator": "Asha Edit", "title": "Monochrome tailoring that still feels soft", "style": "Modern Tailored", "likes": 316, "saves": 134, "trend": "Relaxed suiting"},
            ],
        }

    def _ensure_json_storage(self) -> None:
        if not os.path.exists(self.json_state_path):
            self._write_json_state(self._base_seed())

    def _read_json_state(self) -> dict:
        with open(self.json_state_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write_json_state(self, state: dict) -> None:
        with open(self.json_state_path, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

    def _fallback_to_json(self) -> None:
        self.use_sqlite = False
        self._ensure_json_storage()

    def create_user(self, payload: dict) -> dict:
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        name = (payload.get("name") or "").strip() or "StyleSense User"
        if not email or not password:
            return {"error": "Email and password are required."}
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    cursor = connection.execute(
                        """
                        INSERT INTO users (
                            email, password_hash, name, style_personality, body_type, climate,
                            preferred_palette, style_dna
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            email,
                            generate_password_hash(password),
                            name,
                            "Emerging Personal Style",
                            payload.get("body_type", "Athletic"),
                            payload.get("climate", "Temperate"),
                            json.dumps(["Black", "White", "Stone", "Olive"]),
                            json.dumps(["clarity", "versatility", "modern basics"]),
                        ),
                    )
                    return self.get_user_by_id(cursor.lastrowid)
            except sqlite3.IntegrityError:
                return {"error": "That email is already registered."}
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        if any(user["email"] == email for user in state["users"]):
            return {"error": "That email is already registered."}
        next_id = max(user["id"] for user in state["users"]) + 1 if state["users"] else 1
        user = {
            "id": next_id,
            "email": email,
            "password_hash": generate_password_hash(password),
            "name": name,
            "style_personality": "Emerging Personal Style",
            "body_type": payload.get("body_type", "Athletic"),
            "climate": payload.get("climate", "Temperate"),
            "preferred_palette": ["Black", "White", "Stone", "Olive"],
            "style_dna": ["clarity", "versatility", "modern basics"],
        }
        state["users"].append(user)
        self._write_json_state(state)
        return self._public_user(user)

    def authenticate_user(self, email: str, password: str) -> dict | None:
        email = email.strip().lower()
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                if not row or not check_password_hash(row["password_hash"], password):
                    return None
                return self._serialize_user(row)
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        user = next((user for user in state["users"] if user["email"] == email), None)
        if not user or not check_password_hash(user["password_hash"], password):
            return None
        return self._public_user(user)

    def get_user_by_id(self, user_id: int | None) -> dict | None:
        if not user_id:
            return None
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                return self._serialize_user(row) if row else None
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        user = next((user for user in state["users"] if user["id"] == user_id), None)
        return self._public_user(user) if user else None

    def get_demo_user(self) -> dict:
        return self.get_user_by_id(1)

    def get_state(self, user_id: int) -> dict:
        user = self.get_user_by_id(user_id) or self.get_demo_user()
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    wardrobe_rows = connection.execute("SELECT * FROM wardrobe_items WHERE user_id = ? ORDER BY rowid DESC", (user["id"],)).fetchall()
                    history_rows = connection.execute("SELECT * FROM outfit_history WHERE user_id = ? ORDER BY date DESC, rowid DESC", (user["id"],)).fetchall()
                    feed_rows = connection.execute("SELECT * FROM community_feed ORDER BY likes DESC").fetchall()
                wardrobe_items = [self._serialize_wardrobe_item(row) for row in wardrobe_rows]
                outfit_history = [self._serialize_outfit(row) for row in history_rows]
                community_feed = [dict(row) for row in feed_rows]
            except sqlite3.Error:
                self._fallback_to_json()
                state = self._read_json_state()
                wardrobe_items = [deepcopy(item) for item in state["wardrobe_items"] if item["user_id"] == user["id"]]
                outfit_history = [deepcopy(item) for item in state["outfit_history"] if item["user_id"] == user["id"]]
                community_feed = deepcopy(state["community_feed"])
        else:
            state = self._read_json_state()
            wardrobe_items = [deepcopy(item) for item in state["wardrobe_items"] if item["user_id"] == user["id"]]
            outfit_history = [deepcopy(item) for item in state["outfit_history"] if item["user_id"] == user["id"]]
            community_feed = deepcopy(state["community_feed"])
        return {
            "user_profile": {
                "name": user["name"],
                "style_personality": user["style_personality"],
                "style_dna": user["style_dna"],
                "body_type": user["body_type"],
                "climate": user["climate"],
                "preferred_palette": user["preferred_palette"],
            },
            "wardrobe_items": wardrobe_items,
            "outfit_history": outfit_history,
            "community_feed": community_feed,
        }

    def add_wardrobe_item(self, user_id: int, payload: dict) -> dict:
        item = {
            "id": f"itm-{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "name": payload.get("name", "New Wardrobe Piece"),
            "category": payload.get("category", "Top"),
            "color": payload.get("color", "Neutral"),
            "season": payload.get("season", "All Season"),
            "occasion": payload.get("occasion", "Casual"),
            "fabric": payload.get("fabric", "Cotton"),
            "pattern": payload.get("pattern", "Solid"),
            "image_hint": payload.get("image_hint", "uploaded wardrobe item"),
            "image_url": payload.get("image_url"),
            "favorite": False,
            "times_worn": 0,
        }
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO wardrobe_items (
                            id, user_id, name, category, color, season, occasion, fabric, pattern,
                            image_hint, image_url, favorite, times_worn
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["id"], item["user_id"], item["name"], item["category"], item["color"],
                            item["season"], item["occasion"], item["fabric"], item["pattern"],
                            item["image_hint"], item["image_url"], 0, 0,
                        ),
                    )
                return item
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        state["wardrobe_items"].insert(0, item)
        self._write_json_state(state)
        return item

    def delete_wardrobe_item(self, user_id: int, item_id: str) -> dict:
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    row = connection.execute(
                        "SELECT id FROM wardrobe_items WHERE id = ? AND user_id = ?",
                        (item_id, user_id),
                    ).fetchone()
                    if not row:
                        return {"error": "Item not found.", "id": item_id}
                    connection.execute("DELETE FROM wardrobe_items WHERE id = ? AND user_id = ?", (item_id, user_id))
                return {"id": item_id, "deleted": True}
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        original = len(state["wardrobe_items"])
        state["wardrobe_items"] = [item for item in state["wardrobe_items"] if not (item["id"] == item_id and item["user_id"] == user_id)]
        if len(state["wardrobe_items"]) == original:
            return {"error": "Item not found.", "id": item_id}
        self._write_json_state(state)
        return {"id": item_id, "deleted": True}

    def toggle_favorite(self, user_id: int, item_id: str) -> dict:
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    row = connection.execute("SELECT * FROM wardrobe_items WHERE id = ? AND user_id = ?", (item_id, user_id)).fetchone()
                    if not row:
                        return {"id": item_id, "favorite": False, "error": "Item not found"}
                    new_value = 0 if row["favorite"] else 1
                    connection.execute("UPDATE wardrobe_items SET favorite = ? WHERE id = ? AND user_id = ?", (new_value, item_id, user_id))
                    updated = connection.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
                return self._serialize_wardrobe_item(updated)
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        for item in state["wardrobe_items"]:
            if item["id"] == item_id and item["user_id"] == user_id:
                item["favorite"] = not item.get("favorite", False)
                self._write_json_state(state)
                return item
        return {"id": item_id, "favorite": False, "error": "Item not found"}

    def save_outfit(self, user_id: int, outfit: dict) -> dict:
        entry = {
            "id": f"outfit-{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "name": outfit.get("name", "AI Outfit"),
            "occasion": outfit.get("occasion", "Casual"),
            "weather": outfit.get("weather", "Mild"),
            "mood": outfit.get("mood", "Balanced"),
            "items": outfit.get("items", []),
            "score": outfit.get("score", 80),
            "liked": bool(outfit.get("liked")),
            "date": outfit.get("date", "2026-04-09"),
            "style_request": outfit.get("style_request", ""),
        }
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO outfit_history (
                            id, user_id, name, occasion, weather, mood, items_json, score, liked, date, style_request
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry["id"], entry["user_id"], entry["name"], entry["occasion"], entry["weather"],
                            entry["mood"], json.dumps(entry["items"]), entry["score"], 1 if entry["liked"] else 0, entry["date"], entry["style_request"],
                        ),
                    )
                return entry
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        state["outfit_history"].insert(0, entry)
        self._write_json_state(state)
        return entry

    def add_outfit_to_wardrobe(self, user_id: int, outfit: dict) -> list[dict]:
        generated_items = []
        pieces = [
            ("Top", outfit.get("top")),
            ("Bottom", outfit.get("bottom")),
            ("Shoes", outfit.get("shoes")),
            ("Outerwear", outfit.get("layer")),
        ]
        accessories = outfit.get("accessories") or []
        pieces.extend(("Accessory", accessory) for accessory in accessories)

        for category, name in pieces:
            if not name or name in {"No extra layer", "Light Layer"}:
                continue
            generated_items.append(
                self.add_wardrobe_item(
                    user_id,
                    {
                        "name": name,
                        "category": category,
                        "color": outfit.get("color", "Neutral"),
                        "season": outfit.get("weather", "All Season"),
                        "occasion": outfit.get("occasion", "Casual"),
                        "fabric": outfit.get("preferred_fabric", outfit.get("fabric", "Cotton")),
                        "pattern": outfit.get("pattern", "Solid"),
                        "image_hint": f"Saved from AI look: {outfit.get('name', 'AI Outfit')}",
                    },
                )
            )
        return generated_items

    def clear_outfit_history(self, user_id: int) -> dict:
        if self.use_sqlite:
            try:
                with self._connect() as connection:
                    connection.execute("DELETE FROM outfit_history WHERE user_id = ?", (user_id,))
                return {"cleared": True}
            except sqlite3.Error:
                self._fallback_to_json()
        state = self._read_json_state()
        state["outfit_history"] = [item for item in state["outfit_history"] if item["user_id"] != user_id]
        self._write_json_state(state)
        return {"cleared": True}

    def save_upload(self, file_storage) -> str | None:
        if not file_storage or not file_storage.filename:
            return None
        extension = Path(file_storage.filename).suffix.lower()
        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            return None
        filename = f"{uuid.uuid4().hex}{extension}"
        destination = os.path.join(self.upload_dir, filename)
        file_storage.save(destination)
        return f"/static/uploads/{filename}"

    def _serialize_user(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "style_personality": row["style_personality"],
            "body_type": row["body_type"],
            "climate": row["climate"],
            "preferred_palette": json.loads(row["preferred_palette"]),
            "style_dna": json.loads(row["style_dna"]),
        }

    def _serialize_wardrobe_item(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "color": row["color"],
            "season": row["season"],
            "occasion": row["occasion"],
            "fabric": row["fabric"],
            "pattern": row["pattern"],
            "image_hint": row["image_hint"],
            "image_url": row["image_url"],
            "favorite": bool(row["favorite"]),
            "times_worn": row["times_worn"],
        }

    def _serialize_outfit(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "occasion": row["occasion"],
            "weather": row["weather"],
            "mood": row["mood"],
            "items": json.loads(row["items_json"]),
            "score": row["score"],
            "liked": bool(row["liked"]),
            "date": row["date"],
            "style_request": row["style_request"] if "style_request" in row.keys() else "",
        }

    def _public_user(self, user: dict | None) -> dict | None:
        if user is None:
            return None
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "style_personality": user["style_personality"],
            "body_type": user["body_type"],
            "climate": user["climate"],
            "preferred_palette": deepcopy(user["preferred_palette"]),
            "style_dna": deepcopy(user["style_dna"]),
        }
