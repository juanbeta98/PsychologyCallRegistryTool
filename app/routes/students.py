from flask import Blueprint, render_template, request, jsonify
from models import db, Student, ExcelBatch
from datetime import date
import json

bp = Blueprint("students", __name__)

RISK_FIELDS = [
    ("has_medical_condition", "Condición médica"),
    ("medical_condition_detail", "Detalle condición médica"),
    ("attends_therapy", "Asiste a terapia"),
    ("therapy_type", "Tipo de terapia"),
    ("has_psychiatric_diagnosis", "Diagnóstico psiquiátrico"),
    ("psychiatric_diagnosis_detail", "Detalle diagnóstico"),
    ("family_support", "Apoyo familiar"),
    ("depends_economically", "Dependencia económica"),
    ("economic_resources", "Recursos económicos"),
    ("life_satisfaction", "Satisfacción con la vida"),
    ("attitude_toward_life", "Actitud frente a la vida"),
    ("importance_mental_health", "Importancia salud mental"),
    ("wants_psychosocial_support", "Desea acompañamiento psicosocial"),
    ("sexual_orientation", "Orientación sexual"),
    ("strata", "Estrato"),
    ("zone", "Zona"),
    ("lives_with", "Vive con"),
]


@bp.route("/estudiantes")
def index():
    batches = ExcelBatch.query.order_by(ExcelBatch.import_date.desc()).all()
    return render_template("students.html", batches=batches, risk_fields=RISK_FIELDS)


@bp.route("/api/students")
def api_list():
    query = Student.query
    batch_id = request.args.get("batch_id")
    if batch_id:
        query = query.filter_by(batch_id=batch_id)

    students = query.order_by(Student.row_order).all()
    today = date.today()

    result = []
    for s in students:
        batch_active = s.batch.validity_date >= today
        result.append({
            "id": s.id,
            "doc_number": s.doc_number,
            "full_name": s.full_name,
            "school": s.school or "",
            "program": s.program or "",
            "age": s.age,
            "sex": s.sex or "",
            "sexual_orientation": s.sexual_orientation or "",
            "city": s.city or "",
            "department": s.department or "",
            "strata": s.strata or "",
            "zone": s.zone or "",
            "lives_with": s.lives_with or "",
            "phone": s.phone or "",
            "call_status": s.call_status,
            "is_marked": s.is_marked_for_call,
            "call_count": s.call_count,
            "batch_active": batch_active,
            "batch_filename": s.batch.filename,
            "has_medical_condition": s.has_medical_condition or "",
            "has_psychiatric_diagnosis": s.has_psychiatric_diagnosis or "",
            "attends_therapy": s.attends_therapy or "",
            "family_support": s.family_support or "",
            "life_satisfaction": s.life_satisfaction or "",
            "economic_resources": s.economic_resources or "",
        })
    return jsonify(result)


@bp.route("/api/students/<int:student_id>/toggle_mark", methods=["POST"])
def toggle_mark(student_id):
    student = Student.query.get_or_404(student_id)
    if not student.is_active:
        return jsonify({"error": "Lista vencida, no se puede marcar."}), 400

    student.is_marked_for_call = not student.is_marked_for_call
    if student.is_marked_for_call:
        student.marked_date = date.today()
        if student.call_status == "not_marked":
            student.call_status = "pending"
    else:
        student.marked_date = None
        if student.call_status == "pending":
            student.call_status = "not_marked"
    db.session.commit()
    return jsonify({"is_marked": student.is_marked_for_call, "call_status": student.call_status})


@bp.route("/api/students/<int:student_id>/risk_profile")
def risk_profile(student_id):
    student = Student.query.get_or_404(student_id)
    profile = {}
    for field, label in RISK_FIELDS:
        profile[label] = getattr(student, field) or "—"
    return jsonify({
        "id": student.id,
        "full_name": student.full_name,
        "doc_number": student.doc_number,
        "school": student.school,
        "program": student.program,
        "age": student.age,
        "sex": student.sex,
        "phone": student.phone,
        "call_status": student.call_status,
        "call_count": student.call_count,
        "risk_profile": profile,
    })
