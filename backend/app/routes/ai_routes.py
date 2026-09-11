import os
from flask import Blueprint, request, jsonify
from app.models import Content

try:
    from google import genai
except ImportError:  # google-genai not installed -> AI features degrade, app still boots
    genai = None

ai_bp = Blueprint("ai", __name__)

@ai_bp.route("/generate", methods=["POST"])
def generate_ai_text():
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    history = data.get("history", [])
    current_route = data.get("route", "/")

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    if genai is None:
        return jsonify({"error": "AI features unavailable: google-genai package is not installed (pip install google-genai)"}), 503

    api_key = os.getenv("GEMINI_API_KEY")
    # Treat the .env.example placeholder as "not configured yet" so the
    # auto-created .env (dev.sh copies the template) doesn't send
    # 'paste_your_gemini_key_here' to Google as a real key.
    if api_key and "paste_your" in api_key.lower():
        api_key = None
    if not api_key:
        return jsonify({
            "error": "GEMINI_API_KEY is not set yet. Open backend/.env and "
                     "replace the placeholder with a free key from "
                     "https://aistudio.google.com/apikey, then restart the backend."
        }), 500

    # 1. Fetch site posts context safely
    site_context = ""
    try:
        order_field = getattr(Content, 'id', None) or getattr(Content, 'content_id', None)
        query = Content.query.order_by(order_field.desc()) if order_field is not None else Content.query
        
        posts = query.limit(15).all()
        if posts:
            site_context = "Recent Posts on MoringaHub:\n"
            for p in posts:
                post_id = getattr(p, 'id', getattr(p, 'content_id', 'N/A'))
                title = getattr(p, 'title', 'Untitled')
                body = getattr(p, 'body', '')
                site_context += f"- ID: {post_id} | Title: '{title}' | Body: '{body}'\n"
    except Exception as db_err:
        print("Database context fetch notice:", db_err)

    # 2. System Instructions
    system_instruction = (
        "You are Moringa AI Assistant, an authoritative and helpful guide for MoringaHub.\n"
        f"The user is currently viewing the URL route: '{current_route}'\n\n"
        f"{site_context}\n"
        "Rules & Directives:\n"
        "- Help community members navigate MoringaHub, write articles, and answer questions.\n"
        "- When asked about site posts or articles, utilize the recent post data listed above.\n"
        "- Maintain a concise, friendly, and supportive tone."
    )

    # 3. Format history and conversation contents
    contents = []
    for msg in history:
        text = msg.get("text")
        if not text:
            continue
        role = "user" if msg.get("sender") == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": text}]
        })

    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    client = genai.Client(api_key=api_key)
    
    # 4. Dynamically discover models supported by your API key
    available_models = []
    try:
        for m in client.models.list():
            model_id = m.name.replace("models/", "") if hasattr(m, 'name') else str(m)
            if "gemini" in model_id.lower():
                available_models.append(model_id)
    except Exception as list_err:
        print("Model discovery error:", list_err)

    # Fallback list if dynamic listing fails
    if not available_models:
        available_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

    # Prioritize 'flash' models first for speed and higher quotas
    available_models.sort(key=lambda name: 0 if "flash" in name.lower() else 1)

    last_error = None

    # 5. Model Execution Loop
    for model_name in available_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config={"system_instruction": system_instruction}
            )
            if response and response.text:
                return jsonify({
                    "result": response.text,
                    "modelUsed": model_name
                }), 200
        except Exception as err:
            last_error = str(err)
            print(f"[AI Fallback] '{model_name}' failed: {last_error}. Retrying next model...")
            continue

    return jsonify({
        "error": f"All AI models failed for your API key. Details: {last_error}"
    }), 503