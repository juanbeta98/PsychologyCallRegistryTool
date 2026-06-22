from flask import Blueprint, render_template, request, jsonify
from models import db, Student, Call, CallInterview
from datetime import date, datetime

bp = Blueprint("calls", __name__)


def _serialize_call(c):
    entry = {
        "id": c.id,
        "call_number": c.call_number,
        "call_datetime": c.call_datetime.strftime("%d/%m/%Y %H:%M"),
        "outcome": c.outcome,
        "notes": c.notes or "",
        "rescheduled_to": c.rescheduled_to.strftime("%d/%m/%Y %H:%M") if c.rescheduled_to else None,
        "rescheduled_to_iso": c.rescheduled_to.strftime("%Y-%m-%dT%H:%M") if c.rescheduled_to else None,
        "interview": None,
    }
    if c.interview:
        iv = c.interview
        entry["interview"] = {
            "activity_besides_studying": iv.activity_besides_studying,
            "daily_study_hours": iv.daily_study_hours,
            "autonomy_virtuality": iv.autonomy_virtuality,
            "virtual_most_difficult": iv.virtual_most_difficult,
            "virtual_most_easy": iv.virtual_most_easy,
            "has_teams_access": iv.has_teams_access,
            "has_email_access": iv.has_email_access,
            "career_motivation": iv.career_motivation,
            "psychosocial_accompaniment": iv.psychosocial_accompaniment,
            "psychosocial_notes": iv.psychosocial_notes,
            "psychoeducational_accompaniment": iv.psychoeducational_accompaniment,
            "psychoeducational_notes": iv.psychoeducational_notes,
            "follow_up": iv.follow_up,
            "additional_comments": iv.additional_comments,
            "accepted_support": iv.accepted_support,
            "referred": iv.referred,
            "is_critical": iv.is_critical,
        }
    return entry

MAX_CALLS = 3


def _update_student_status(student):
    calls = list(student.calls.order_by(Call.call_datetime).all())
    total = len(calls)

    if total == 0:
        student.call_status = "pending"
        return

    last = calls[-1]

    if last.outcome == "critical":
        student.call_status = "closed_critical"
        return

    if last.outcome == "completed" and last.interview:
        iv = last.interview
        if iv.referred:
            student.call_status = "closed_referred"
        elif iv.accepted_support:
            student.call_status = "in_progress"
        elif iv.accepted_support is False:
            student.call_status = "closed_refused"
        return

    if last.outcome in ("no_answer", "no_time"):
        if total >= MAX_CALLS:
            student.call_status = "closed_no_answer"
        elif last.rescheduled_to:
            student.call_status = "rescheduled"
        else:
            student.call_status = "in_progress"
        return

    student.call_status = "in_progress"


@bp.route("/llamadas")
def index():
    return render_template("calls.html")


@bp.route("/api/calls/dashboard_counts")
def dashboard_counts():
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    rescheduled_today = (
        Student.query
        .join(Student.calls)
        .filter(
            Student.call_status == "rescheduled",
            Call.rescheduled_to >= today_start,
            Call.rescheduled_to <= today_end,
        ).count()
    )
    pending = Student.query.filter(
        Student.is_marked_for_call == True,
        Student.call_status.in_(["pending", "in_progress"]),
        Student.phone.isnot(None),
    ).count()
    no_phone = Student.query.filter(
        Student.is_marked_for_call == True,
        Student.phone.is_(None),
    ).count()
    closed_today = (
        Call.query
        .filter(
            Call.call_datetime >= today_start,
            Call.call_datetime <= today_end,
        ).count()
    )
    return jsonify({
        "rescheduled_today": rescheduled_today,
        "pending": pending,
        "no_phone": no_phone,
        "calls_today": closed_today,
    })


@bp.route("/api/calls/queue")
def queue():
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Section A: all rescheduled calls (past, today, future), ordered by date
    rescheduled = (
        Student.query
        .join(Student.calls)
        .filter(
            Student.call_status == "rescheduled",
            Call.rescheduled_to.isnot(None),
            Student.phone.isnot(None),
        )
        .order_by(Call.rescheduled_to)
        .all()
    )

    # Section B: normal pending queue (with phone, active batch)
    pending = (
        Student.query
        .filter(
            Student.is_marked_for_call == True,
            Student.call_status.in_(["pending", "in_progress"]),
            Student.phone.isnot(None),
        )
        .order_by(Student.row_order)
        .all()
    )

    def serialize(s):
        last = s.last_call
        next_reschedule = s.next_rescheduled_call
        return {
            "id": s.id,
            "doc_number": s.doc_number,
            "full_name": s.full_name,
            "phone": s.phone,
            "school": s.school or "",
            "program": s.program or "",
            "call_count": s.call_count,
            "call_status": s.call_status,
            "last_call_date": last.call_datetime.strftime("%d/%m/%Y %H:%M") if last else None,
            "rescheduled_to": next_reschedule.rescheduled_to.strftime("%d/%m/%Y %H:%M") if next_reschedule and next_reschedule.rescheduled_to else None,
            "rescheduled_date": next_reschedule.rescheduled_to.strftime("%Y-%m-%d") if next_reschedule and next_reschedule.rescheduled_to else None,
        }

    return jsonify({
        "rescheduled": [serialize(s) for s in rescheduled],
        "pending": [serialize(s) for s in pending],
    })


@bp.route("/api/calls/register", methods=["POST"])
def register_call():
    data = request.get_json()
    student_id = data.get("student_id")
    student = Student.query.get_or_404(student_id)

    if not student.is_active:
        return jsonify({"error": "Lista vencida."}), 400

    call_count = student.call_count
    if call_count >= MAX_CALLS and student.call_status not in ("in_progress", "rescheduled"):
        return jsonify({"error": "Este estudiante ya tiene 3 llamadas registradas."}), 400

    outcome = data.get("outcome")  # no_answer | no_time | completed | critical
    notes = data.get("notes", "")
    rescheduled_to = data.get("rescheduled_to")  # ISO string or None

    call = Call(
        student_id=student.id,
        call_number=call_count + 1,
        call_datetime=datetime.now(),
        outcome=outcome,
        notes=notes,
    )

    if rescheduled_to:
        try:
            call.rescheduled_to = datetime.fromisoformat(rescheduled_to)
        except ValueError:
            pass

    db.session.add(call)
    db.session.flush()

    # Attach interview if call was completed or critical
    if outcome in ("completed", "critical"):
        iv_data = data.get("interview", {})
        iv = CallInterview(
            call_id=call.id,
            activity_besides_studying=iv_data.get("activity_besides_studying"),
            daily_study_hours=iv_data.get("daily_study_hours"),
            autonomy_virtuality=iv_data.get("autonomy_virtuality"),
            virtual_most_difficult=iv_data.get("virtual_most_difficult"),
            virtual_most_easy=iv_data.get("virtual_most_easy"),
            has_teams_access=iv_data.get("has_teams_access"),
            has_email_access=iv_data.get("has_email_access"),
            career_motivation=iv_data.get("career_motivation"),
            psychosocial_accompaniment=bool(iv_data.get("psychosocial_accompaniment")),
            psychosocial_notes=iv_data.get("psychosocial_notes"),
            psychoeducational_accompaniment=bool(iv_data.get("psychoeducational_accompaniment")),
            psychoeducational_notes=iv_data.get("psychoeducational_notes"),
            follow_up=iv_data.get("follow_up"),
            additional_comments=iv_data.get("additional_comments"),
            accepted_support=iv_data.get("accepted_support"),
            referred=bool(iv_data.get("referred")),
            is_critical=(outcome == "critical"),
        )
        db.session.add(iv)

    _update_student_status(student)
    db.session.commit()

    return jsonify({"ok": True, "call_status": student.call_status, "call_number": call.call_number})


@bp.route("/api/calls/history/<int:student_id>")
def history(student_id):
    student = Student.query.get_or_404(student_id)
    calls = student.calls.order_by(Call.call_datetime).all()
    return jsonify([_serialize_call(c) for c in calls])


@bp.route("/historico")
def historico_page():
    return render_template("history.html")


@bp.route("/api/calls/historico")
def historico_api():
    student_ids = [row[0] for row in db.session.query(Call.student_id).distinct().all()]
    students = (
        Student.query
        .filter(Student.id.in_(student_ids))
        .order_by(Student.full_name)
        .all()
    )
    result = []
    for s in students:
        calls = s.calls.order_by(Call.call_datetime).all()
        last = calls[-1] if calls else None
        result.append({
            "id": s.id,
            "doc_number": s.doc_number,
            "full_name": s.full_name,
            "program": s.program or "",
            "call_status": s.call_status,
            "call_count": len(calls),
            "last_call_date": last.call_datetime.strftime("%d/%m/%Y") if last else None,
            "calls": [_serialize_call(c) for c in calls],
        })
    return jsonify(result)


@bp.route("/api/calls/<int:call_id>", methods=["PUT"])
def update_call(call_id):
    data = request.get_json()
    call = Call.query.get_or_404(call_id)

    call.outcome = data.get("outcome", call.outcome)
    call.notes = data.get("notes", call.notes)
    rescheduled_to = data.get("rescheduled_to")
    if rescheduled_to:
        try:
            call.rescheduled_to = datetime.fromisoformat(rescheduled_to)
        except ValueError:
            pass
    else:
        call.rescheduled_to = None

    if call.interview and "interview" in data:
        iv = call.interview
        iv_data = data["interview"]
        iv.activity_besides_studying = iv_data.get("activity_besides_studying")
        iv.daily_study_hours = iv_data.get("daily_study_hours")
        iv.autonomy_virtuality = iv_data.get("autonomy_virtuality")
        iv.virtual_most_difficult = iv_data.get("virtual_most_difficult")
        iv.virtual_most_easy = iv_data.get("virtual_most_easy")
        iv.has_teams_access = iv_data.get("has_teams_access")
        iv.has_email_access = iv_data.get("has_email_access")
        iv.career_motivation = iv_data.get("career_motivation")
        iv.psychosocial_accompaniment = bool(iv_data.get("psychosocial_accompaniment", False))
        iv.psychosocial_notes = iv_data.get("psychosocial_notes")
        iv.psychoeducational_accompaniment = bool(iv_data.get("psychoeducational_accompaniment", False))
        iv.psychoeducational_notes = iv_data.get("psychoeducational_notes")
        iv.follow_up = iv_data.get("follow_up")
        iv.additional_comments = iv_data.get("additional_comments")
        iv.accepted_support = iv_data.get("accepted_support")

    db.session.commit()
    return jsonify({"ok": True})
