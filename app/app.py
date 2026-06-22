import os
from flask import Flask, redirect, url_for
from models import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(__name__)
    app.secret_key = "psicologia-unad-2025"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'psicologia.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")
    app.config["REPORT_FOLDER"] = os.path.join(BASE_DIR, "reports")
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB

    db.init_app(app)

    from routes import students, phones, calls, reports, imports
    app.register_blueprint(students.bp)
    app.register_blueprint(phones.bp)
    app.register_blueprint(calls.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(imports.bp)

    @app.route("/")
    def index():
        return redirect(url_for("calls.index"))

    @app.route("/dashboard")
    def dashboard():
        from flask import render_template
        return render_template("dashboard.html")

    with app.app_context():
        db.create_all()
        # Add columns introduced after initial deploy
        from sqlalchemy import text, inspect as sa_inspect
        inspector = sa_inspect(db.engine)
        existing = {c["name"] for c in inspector.get_columns("call_interview")}
        new_cols = [
            ("virtual_most_easy", "TEXT"),
            ("has_teams_access", "BOOLEAN"),
            ("has_email_access", "BOOLEAN"),
            ("psychoeducational_accompaniment", "BOOLEAN"),
            ("psychoeducational_notes", "TEXT"),
        ]
        with db.engine.begin() as conn:
            for col, col_type in new_cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE call_interview ADD COLUMN {col} {col_type}"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False, host="127.0.0.1", port=5050)
