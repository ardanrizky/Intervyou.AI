import os
import sqlite3
from io import BytesIO
from math import ceil
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    send_file,
)
import pandas as pd

from questions import get_questions_for_role, ROLES
from answer_keys import get_ideal_answers
from text_scoring import (
    evaluate_interview_answer,
    tfidf_cosine_score,
    similarity_to_score,
    analyze_keyword_gap,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "intervyou-dev-secret-key-2026")
DB_PATH = os.path.join(os.path.dirname(__file__), "intervyou.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                role TEXT NOT NULL,
                average_score REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interview_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                question_index INTEGER,
                question TEXT,
                user_answer TEXT,
                score INTEGER,
                feedback TEXT,
                matched_keywords TEXT,
                missing_keywords TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)
        conn.commit()

init_db()

def get_dashboard_stats(user_name=None):
    with get_db() as conn:
        if user_name:
            cur = conn.execute(
                "SELECT average_score FROM sessions WHERE user_name = ? ORDER BY id ASC",
                (user_name,),
            )
        else:
            cur = conn.execute("SELECT average_score FROM sessions ORDER BY id ASC")
        rows = cur.fetchall()
        
    scores = [r["average_score"] for r in rows]
    total_sessions = len(scores)
    avg_score = round(sum(scores) / total_sessions, 1) if total_sessions > 0 else 0.0
    best_score = round(max(scores), 1) if total_sessions > 0 else 0.0

    return {
        "total_sessions": total_sessions,
        "avg_score": avg_score,
        "best_score": best_score,
        "streak_days": total_sessions,
        "progress_scores": scores[-8:] if scores else [],
    }

@app.context_processor
def inject_user():
    return dict(
        user_name=session.get("user_name"),
        user_role=session.get("user_role"),
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()

        if not name or not role:
            error = "Silakan isi nama dan pilih role yang diinginkan."
        else:
            session["user_name"] = name
            session["user_role"] = role
            session.pop("current_session_scores", None)
            return redirect(url_for("dashboard"))

    return render_template("login.html", roles=ROLES, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def dashboard():
    if "user_name" not in session or "user_role" not in session:
        return redirect(url_for("login"))

    stats = get_dashboard_stats(session.get("user_name"))
    return render_template(
        "dashboard.html",
        stats=stats,
        scores=stats["progress_scores"],
        title="Dashboard - Intervyou.AI",
    )

@app.route("/interview")
def interview():
    if "user_name" not in session or "user_role" not in session:
        return redirect(url_for("login"))

    role = session.get("user_role", "")
    questions = get_questions_for_role(role)
    if not questions:
        questions = get_questions_for_role("default")

    session["current_session_scores"] = []
    session["total_questions"] = len(questions)

    return render_template(
        "interview.html",
        question=questions[0],
        total_questions=len(questions),
        title=f"Wawancara {role} - Intervyou.AI",
    )

@app.route("/api/evaluate", methods=["POST"])
def evaluate_answer():
    if "user_role" not in session:
        return jsonify({"success": False, "message": "Sesi telah berakhir, silakan login kembali."})

    data = request.get_json() or {}
    answer_text = data.get("answer", "").strip()
    question_index = int(data.get("question_index", 0))

    if not answer_text:
        return jsonify({"success": False, "message": "Jawaban masih kosong."})

    role = session.get("user_role", "")
    user_name = session.get("user_name", "Anonymous")
    questions = get_questions_for_role(role)
    total_questions = len(questions)

    if question_index < 0:
        question_index = 0
    if question_index >= total_questions:
        question_index = total_questions - 1

    current_q_text = questions[question_index]
    ideal_answers = get_ideal_answers(role, question_index)
    eval_result = evaluate_interview_answer(answer_text, ideal_answers, current_q_text)
    
    score = eval_result["score"]
    feedback = eval_result["feedback"]
    matched_keywords = eval_result["matched_keywords"]
    missing_keywords = eval_result["missing_keywords"]

    scores = session.get("current_session_scores", [])
    scores.append(score)
    session["current_session_scores"] = scores

    next_idx = question_index + 1
    has_next = next_idx < total_questions
    next_question = questions[next_idx] if has_next else None

    is_finished = not has_next
    final_avg = None
    overall_feedback = None

    if is_finished:
        final_avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db() as conn:
            conn.execute(
                "INSERT INTO sessions (user_name, role, average_score, created_at) VALUES (?, ?, ?, ?)",
                (user_name, role, final_avg, now_str),
            )
            conn.commit()

        if final_avg < 60:
            overall_feedback = (
                "Performa awal yang bagus untuk memulai! Disarankan untuk memperdalam pemahaman "
                "terminologi teknis dan latihan menyampaikan solusi secara terstruktur."
            )
        elif final_avg < 80:
            overall_feedback = (
                "Hasil simulasi memuaskan! Kamu memahami konsep utama peran ini. "
                "Tambahkan detail metrik atau hasil akhir dari proyekmu saat menjawab."
            )
        else:
            overall_feedback = (
                "Luar biasa! Pemahaman teknis dan penyampaianmu sangat solid. "
                "Kamu sudah siap menghadapi wawancara teknis sungguhan."
            )

    return jsonify({
        "success": True,
        "score": score,
        "feedback": feedback,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "has_next": has_next,
        "next_question": next_question,
        "next_question_index": next_idx,
        "is_finished": is_finished,
        "final_avg_score": final_avg,
        "overall_feedback": overall_feedback,
    })

@app.route("/history")
def history():
    if "user_name" not in session or "user_role" not in session:
        return redirect(url_for("login"))

    per_page = 6
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    with get_db() as conn:
        cur_total = conn.execute("SELECT COUNT(*) as cnt FROM sessions")
        total = cur_total.fetchone()["cnt"]

        total_pages = ceil(total / per_page) if total > 0 else 1
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page
        cur_sessions = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        )
        sessions_list = cur_sessions.fetchall()

    return render_template(
        "history.html",
        sessions=sessions_list,
        page=page,
        total_pages=total_pages,
        total_sessions=total,
        title="Riwayat Simulasi - Intervyou.AI",
    )

@app.route("/history/export")
def history_export():
    if "user_name" not in session or "user_role" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        cur = conn.execute("SELECT user_name, role, average_score, created_at FROM sessions ORDER BY id DESC")
        rows = cur.fetchall()

    data = [
        {
            "Nama": r["user_name"],
            "Role": r["role"],
            "Rata-rata Skor": r["average_score"],
            "Waktu": r["created_at"],
        }
        for r in rows
    ]

    df = pd.DataFrame(data if data else [], columns=["Nama", "Role", "Rata-rata Skor", "Waktu"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Riwayat Simulasi")

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="riwayat_simulasi_intervyou.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7070, debug=True)
