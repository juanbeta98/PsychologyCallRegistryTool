from flask import Blueprint, render_template, request, jsonify
from models import db, Student
from datetime import date

bp = Blueprint("phones", __name__)


@bp.route("/telefonos")
def index():
    return render_template("phones.html")


@bp.route("/api/phones/pending")
def pending():
    today = date.today()
    students = (
        Student.query
        .filter(Student.is_marked_for_call == True)
        .filter(Student.phone.is_(None))
        .join(Student.batch)
        .order_by(Student.row_order)
        .all()
    )
    result = []
    for s in students:
        if s.batch.validity_date >= today:
            result.append({
                "id": s.id,
                "doc_number": s.doc_number,
                "full_name": s.full_name,
                "school": s.school or "",
                "program": s.program or "",
            })
    return jsonify(result)


@bp.route("/api/phones/<int:student_id>", methods=["POST"])
def save_phone(student_id):
    student = Student.query.get_or_404(student_id)
    data = request.get_json()
    phone = (data.get("phone") or "").strip()
    if not phone:
        return jsonify({"error": "Teléfono no puede estar vacío."}), 400
    student.phone = phone
    db.session.commit()
    return jsonify({"ok": True, "phone": student.phone})


@bp.route("/api/phones/<int:student_id>", methods=["DELETE"])
def delete_phone(student_id):
    student = Student.query.get_or_404(student_id)
    student.phone = None
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/api/phones/registered")
def registered():
    today = date.today()
    students = (
        Student.query
        .filter(Student.is_marked_for_call == True)
        .filter(Student.phone.isnot(None))
        .join(Student.batch)
        .order_by(Student.row_order)
        .all()
    )
    result = []
    for s in students:
        if s.batch.validity_date >= today:
            result.append({
                "id": s.id,
                "doc_number": s.doc_number,
                "full_name": s.full_name,
                "phone": s.phone,
                "school": s.school or "",
            })
    return jsonify(result)
