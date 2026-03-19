from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

app = Flask(__name__)
app.secret_key = "udaan_secret_key"

# ================= DATABASE CONFIG =================
# Password updated to: Arnav@123 
# Note: @ is encoded as %40 to ensure the URI parses correctly
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Arnav%40123@localhost/udaan_project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ================= DATABASE MODELS =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100))
    contact = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    recommended_stream = db.Column(db.String(100), default="None")
    aptitude_label = db.Column(db.String(100), default="Test Not Taken")

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    rating = db.Column(db.String(10))
    message = db.Column(db.Text)

# ================= DATA LOADER =================
def get_roadmap_data():
    base_path = os.path.dirname(__file__)
    file_path = os.path.join(base_path, 'data.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return {}


def fetch_tts_audio(text, lang):
    query = urlencode({
        "ie": "UTF-8",
        "client": "tw-ob",
        "tl": lang,
        "q": text,
    })
    tts_url = f"https://translate.google.com/translate_tts?{query}"
    tts_request = Request(
        tts_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(tts_request, timeout=15) as tts_response:
        return tts_response.read()

# ================= AUTH ROUTES =================

@app.route("/tts")
def tts_proxy():
    text = (request.args.get("text") or "").strip()
    lang = (request.args.get("lang") or "en").strip().lower()

    if not text:
        return jsonify({"error": "Missing text"}), 400

    if len(text) > 500:
        return jsonify({"error": "Text too long"}), 400

    allowed_langs = {"en", "hi", "mr"}
    if lang not in allowed_langs:
        lang = "en"

    try:
        audio_bytes = fetch_tts_audio(text, lang)
    except Exception as e:
        return jsonify({"error": "TTS fetch failed", "details": str(e)}), 502

    return Response(
        audio_bytes,
        mimetype="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'inline; filename="speech.mp3"',
        },
    )

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        contact = request.form.get("contact")
        password = request.form.get("password")
        user = User.query.filter_by(contact=contact).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            session["logged_in"] = True
            session["user_id"] = user.id
            session["user_name"] = user.fullname
            
            if user.recommended_stream != "None":
                return redirect(url_for("dashboard"))
            return redirect(url_for("aptitude"))
        else:
            flash("Invalid Login Details!", "danger")
    return render_template("login.html")

@app.route("/signup", methods=["POST"])
def signup():
    fullname = request.form.get("fullname")
    contact = request.form.get("contact")
    password = request.form.get("password")
    
    if User.query.filter_by(contact=contact).first():
        flash("Email/Mobile already registered!", "warning")
        return redirect(url_for("login"))

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(fullname=fullname, contact=contact, password=hashed_pw)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        session["logged_in"] = True
        session["user_id"] = new_user.id
        session["user_name"] = new_user.fullname
        return redirect(url_for("aptitude"))
    except Exception as e:
        db.session.rollback()
        flash("Registration Error. Please try again.", "danger")
        return redirect(url_for("login"))

# ================= CORE APP ROUTES =================

@app.route("/aptitude")
def aptitude():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    return render_template("aptitude.html", user_name=session.get("user_name"))

@app.route("/submit_aptitude", methods=["POST"])
def submit_aptitude():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    
    result_label = request.form.get("aptitude_result")
    
    stream_map = {
        "Technology & Engineering": "Engineering",
        "Medical & Healthcare": "Medical",
        "Design & Creative Field": "Design",
        "Business & Management": "Management",
        "Government & Social Services": "Government"
    }
    
    user = User.query.get(session["user_id"])
    if user:
        user.aptitude_label = result_label
        user.recommended_stream = stream_map.get(result_label, "Engineering")
        db.session.commit()
    
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    return render_template("dashboard.html", user=user)

@app.route("/exams")
def exams():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    return render_template("exams.html", user_name=session.get("user_name"))

@app.route("/scholarships")
def scholarships():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    return render_template("scholarships.html", user_name=session.get("user_name"))

@app.route("/skills")
def skills():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    return render_template("skills.html", user_name=session.get("user_name"))

# ================= PARENT ROUTES =================

@app.route("/parent-guidance")
def parent_guidance():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    return render_template("parent_guidance.html", user_name=session.get("user_name"))

@app.route("/parent-feedback", methods=["GET", "POST"])
def parent_feedback():
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    
    if request.method == "POST":
        name = request.form.get("name")
        rating = request.form.get("rating")
        message = request.form.get("message")

        new_feedback = Feedback(name=name, rating=rating, message=message)
        db.session.add(new_feedback)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "success"}), 200

        flash("Feedback submitted successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("parent_feedback.html", user_name=session.get("user_name"))

# ================= ROADMAP LOGIC =================

@app.route("/roadmap/overview/<stream_id>")
def roadmap_overview(stream_id):
    if not session.get("logged_in"): 
        return redirect(url_for("login"))

    all_data = get_roadmap_data()
    stream_data = all_data.get(stream_id)
    
    if not stream_data:
        flash("Stream data not found.", "danger")
        return redirect(url_for("dashboard"))
    
    return render_template("roadmap_overview.html", 
                           stream=stream_id, 
                           data=stream_data, 
                           user_name=session.get("user_name"))

@app.route("/roadmap/streams")
def roadmap_streams():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    all_data = get_roadmap_data()
    sorted_streams = dict(sorted(all_data.items(), key=lambda kv: kv[0].lower()))

    return render_template("roadmap_streams.html", streams=sorted_streams, user_name=session.get("user_name"))

@app.route("/roadmap/detail/<branch_id>")
def roadmap_detail(branch_id):
    if not session.get("logged_in"): 
        return redirect(url_for("login"))
    
    all_data = get_roadmap_data()
    target_branch = None
    parent_stream = None

    for stream_name, stream_content in all_data.items():
        if "branches" in stream_content and branch_id in stream_content["branches"]:
            target_branch = stream_content["branches"][branch_id]
            parent_stream = stream_name
            break

    if not target_branch:
        flash("Detailed Roadmap not found.", "warning")
        return redirect(url_for("dashboard"))
    
    return render_template("roadmap_detail.html", 
                           branch=target_branch, 
                           stream=parent_stream, 
                           user_name=session.get("user_name"))

@app.route("/search")
def search():
    query = request.args.get('q', '').lower()
    if not query:
        return redirect(url_for('dashboard'))

    all_data = get_roadmap_data()
    results = []

    for stream_name, stream_content in all_data.items():
        if "branches" in stream_content:
            for branch_id, branch_info in stream_content["branches"].items():
                if query in branch_info['name'].lower() or query in branch_info.get('description', '').lower():
                    results.append({
                        'id': branch_id,
                        'name': branch_info['name'],
                        'stream': stream_name
                    })

    return render_template("search_results.html", results=results, query=query)

# --- ADMIN SECURITY CONFIG ---
ADMIN_SECRET_KEY = "udaan2006"

@app.route("/admin/health")
def admin_health():
    """Diagnostic endpoint updated with your credentials"""
    try:
        User.query.first()
        return {
            "status": "healthy",
            "database": "connected",
            "tables_exist": "True"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "next_steps": [
                "1. Check if MySQL is running",
                "2. Verify database 'udaan_project' exists",
                "3. Check credentials: User=root, Password=Arnav@123",
                "4. Ensure PyMySQL and Cryptography are installed: pip install pymysql cryptography"
            ]
        }, 500

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_authorized"):
        return redirect(url_for("admin_login"))
        
    try:
        users = User.query.all()
        feedbacks = Feedback.query.all()
        return render_template("admin_dashboard.html", users=users, feedbacks=feedbacks)
    except Exception as e:
        error_msg = str(e)
        if "Access denied" in error_msg:
            hint = "Check MySQL credentials: root / Arnav@123"
        elif "Unknown database" in error_msg:
            hint = "Database 'udaan_project' doesn't exist."
        else:
            hint = error_msg
            
        return f"<h3>Database Connection Error</h3><p>Issue: {hint}</p><p>Full Error: {error_msg}</p>"

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_authorized"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        entered_pass = request.form.get("admin_password")
        if entered_pass == ADMIN_SECRET_KEY:
            session["admin_authorized"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Incorrect Admin Access Key!", "danger")
            return redirect(url_for("admin_login"))
            
    return render_template("admin_login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all() 
    app.run(debug=True)
