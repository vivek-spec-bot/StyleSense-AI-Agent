import os
from flask import Flask, jsonify, render_template, request, session

from recommender import StyleSenseEngine
from storage import DataStore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_file(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"").strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(os.path.join(BASE_DIR, ".env"))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "stylesense-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

store = DataStore(BASE_DIR)
engine = StyleSenseEngine(store)


def current_user():
    user = store.get_user_by_id(session.get("user_id"))
    return user or store.get_demo_user()


@app.route("/")
def home():
    return render_template("index.html", current_user=current_user())


@app.route("/wardrobe")
def wardrobe():
    return render_template("wardrobe.html", current_user=current_user())


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", current_user=current_user())


@app.get("/api/auth/status")
def auth_status():
    user = current_user()
    return jsonify({"authenticated": "user_id" in session, "user": user})


@app.post("/api/auth/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    user = store.create_user(payload)
    if user.get("error"):
        return jsonify(user), 400
    session["user_id"] = user["id"]
    return jsonify({"authenticated": True, "user": user})


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    user = store.authenticate_user(payload.get("email", ""), payload.get("password", ""))
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    session["user_id"] = user["id"]
    return jsonify({"authenticated": True, "user": user})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"authenticated": False, "user": store.get_demo_user()})


@app.get("/api/platform-summary")
def platform_summary():
    return jsonify(engine.get_platform_summary(current_user()["id"]))


@app.get("/api/wardrobe")
def get_wardrobe():
    return jsonify(store.get_state(current_user()["id"])["wardrobe_items"])


@app.post("/api/wardrobe")
def create_wardrobe_item():
    payload = request.get_json(silent=True) or {}
    return jsonify(store.add_wardrobe_item(current_user()["id"], payload))


@app.post("/api/wardrobe/upload")
def upload_wardrobe_item():
    image_url = store.save_upload(request.files.get("image"))
    if request.files.get("image") and not image_url:
        return jsonify({"error": "Upload must be a png, jpg, jpeg, or webp image."}), 400
    payload = dict(request.form)
    payload["image_url"] = image_url
    payload["image_hint"] = payload.get("image_hint") or "uploaded wardrobe photo"
    return jsonify(store.add_wardrobe_item(current_user()["id"], payload))


@app.post("/api/wardrobe/<item_id>/favorite")
def favorite_wardrobe_item(item_id):
    return jsonify(store.toggle_favorite(current_user()["id"], item_id))


@app.delete("/api/wardrobe/<item_id>")
def delete_wardrobe_item(item_id):
    result = store.delete_wardrobe_item(current_user()["id"], item_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result)


@app.get("/api/outfits/history")
def outfit_history():
    return jsonify(store.get_state(current_user()["id"])["outfit_history"])


@app.delete("/api/outfits/history")
def clear_outfit_history():
    return jsonify(store.clear_outfit_history(current_user()["id"]))


@app.post("/api/recommend")
def recommend():
    if request.form:
        payload = dict(request.form)
        reference_image = request.files.get("reference_image")
        reference_image_url = store.save_upload(reference_image)
        if reference_image and not reference_image_url:
            return jsonify({"error": "Reference image must be a png, jpg, jpeg, or webp image."}), 400
        if reference_image_url:
            payload["reference_image_url"] = reference_image_url
            payload["reference_image_name"] = reference_image.filename
    else:
        payload = request.get_json(silent=True) or {}
    return jsonify(engine.recommend(current_user()["id"], payload))


@app.post("/api/recommend/save-to-wardrobe")
def save_recommendation_to_wardrobe():
    payload = request.get_json(silent=True) or {}
    outfit = payload.get("outfit") or {}
    if not outfit:
        return jsonify({"error": "Outfit payload is required."}), 400
    return jsonify({"added_items": store.add_outfit_to_wardrobe(current_user()["id"], outfit)})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    return jsonify(engine.chat(current_user()["id"], payload))


@app.post("/api/try-on")
def try_on():
    payload = request.get_json(silent=True) or {}
    return jsonify(engine.try_on(current_user()["id"], payload))


@app.post("/api/discover")
def discover():
    payload = request.get_json(silent=True) or {}
    return jsonify(engine.discover(current_user()["id"], payload))


@app.post("/api/lookbook")
def lookbook():
    payload = request.get_json(silent=True) or {}
    return jsonify(engine.generate_lookbook(current_user()["id"], payload))


@app.post("/api/weather-outfit")
def weather_outfit():
    payload = request.get_json(silent=True) or {}
    if payload.get("lat") is None or payload.get("lon") is None:
        return jsonify({"error": "Latitude and longitude are required."}), 400
    return jsonify(engine.weather_report_outfit(current_user()["id"], payload))


@app.get("/api/analytics")
def analytics():
    return jsonify(engine.analytics(current_user()["id"]))


if __name__ == "__main__":
    app.run(debug=True)
