import os
from datetime import date, datetime
from collections import Counter, defaultdict
from flask import Blueprint, render_template, jsonify, send_file, current_app, request
from models import db, Student, Call, CallInterview, ExcelBatch
import pandas as pd

bp = Blueprint("reports", __name__)

OUTCOME_LABELS = {
    "no_answer": "No contestó",
    "no_time": "No pudo hablar",
    "completed": "Conversación completa",
    "critical": "Caso crítico",
}

STATUS_LABELS = {
    "not_marked": "Sin marcar",
    "pending": "Pendiente",
    "in_progress": "En progreso",
    "rescheduled": "Reagendado",
    "closed_no_answer": "Cerrado – sin respuesta",
    "closed_refused": "Cerrado – rechazó apoyo",
    "closed_referred": "Cerrado – remitido",
    "closed_critical": "Cerrado – caso crítico",
}


@bp.route("/reportes")
def index():
    return render_template("reports.html")


@bp.route("/informe")
def informe():
    return render_template("informe.html")


@bp.route("/api/reports/summary")
def summary():
    today = date.today()
    total_students = Student.query.count()
    active_students = sum(1 for s in Student.query.all() if s.batch.validity_date >= today)
    marked = Student.query.filter_by(is_marked_for_call=True).count()
    total_calls = Call.query.count()

    status_counts = {}
    for status, label in STATUS_LABELS.items():
        count = Student.query.filter_by(call_status=status).count()
        if count > 0:
            status_counts[label] = count

    outcome_counts = {}
    for outcome, label in OUTCOME_LABELS.items():
        count = Call.query.filter_by(outcome=outcome).count()
        if count > 0:
            outcome_counts[label] = count

    batches = ExcelBatch.query.order_by(ExcelBatch.import_date.desc()).all()
    batch_summary = [{
        "filename": b.filename,
        "import_date": b.import_date.isoformat(),
        "validity_date": b.validity_date.isoformat(),
        "is_active": b.validity_date >= today,
        "student_count": b.student_count,
    } for b in batches]

    return jsonify({
        "total_students": total_students,
        "active_students": active_students,
        "marked_for_call": marked,
        "total_calls": total_calls,
        "status_counts": status_counts,
        "outcome_counts": outcome_counts,
        "batches": batch_summary,
    })


@bp.route("/api/reports/charts")
def charts():
    all_calls = Call.query.order_by(Call.call_datetime).all()

    contacted_ids = list({c.student_id for c in all_calls})
    contacted_students = Student.query.filter(Student.id.in_(contacted_ids)).all() if contacted_ids else []
    total_students = Student.query.count()
    students_with_interview = len({
        c.student_id for c in all_calls if c.outcome in ("completed", "critical")
    })

    outcome_counts = Counter(c.outcome for c in all_calls)

    calls_by_date = defaultdict(int)
    for c in all_calls:
        calls_by_date[c.call_datetime.strftime("%Y-%m-%d")] += 1

    sex_counts = Counter()
    strata_counts = Counter()
    city_counts = Counter()
    zone_counts = Counter()
    for s in contacted_students:
        if s.sex:
            sex_counts[s.sex] += 1
        if s.strata:
            strata_counts[str(s.strata)] += 1
        if s.city:
            city_counts[s.city] += 1
        if s.zone:
            zone_counts[s.zone] += 1

    interviews = CallInterview.query.all()
    total_interviews = len(interviews)

    study_hours_order = ["1 hora", "De 2 a 4 horas", "Más de 4 horas"]
    study_hours_raw = Counter(iv.daily_study_hours for iv in interviews if iv.daily_study_hours)
    autonomy_order = ["Buena", "Regular", "Mala"]
    autonomy_raw = Counter(iv.autonomy_virtuality for iv in interviews if iv.autonomy_virtuality)

    motivation_vals = [iv.career_motivation for iv in interviews if iv.career_motivation]
    motivation_dist = {str(i): motivation_vals.count(i) for i in range(1, 6)}

    teams_yes = sum(1 for iv in interviews if iv.has_teams_access is True)
    teams_no = sum(1 for iv in interviews if iv.has_teams_access is False)
    email_yes = sum(1 for iv in interviews if iv.has_email_access is True)
    email_no = sum(1 for iv in interviews if iv.has_email_access is False)

    accepted = sum(1 for iv in interviews if iv.accepted_support is True)
    refused = sum(1 for iv in interviews if iv.accepted_support is False)
    psychosocial = sum(1 for iv in interviews if iv.psychosocial_accompaniment)
    critical = sum(1 for iv in interviews if iv.is_critical)
    referred = sum(1 for iv in interviews if iv.referred)

    first_call = all_calls[0].call_datetime if all_calls else None
    last_call = all_calls[-1].call_datetime if all_calls else None

    return jsonify({
        "period": {
            "first_call": first_call.strftime("%d/%m/%Y") if first_call else None,
            "last_call": last_call.strftime("%d/%m/%Y") if last_call else None,
            "report_date": date.today().strftime("%d/%m/%Y"),
        },
        "funnel": {
            "total_students": total_students,
            "contacted": len(contacted_ids),
            "with_interview": students_with_interview,
            "accepted": accepted,
        },
        "calls": {
            "total": len(all_calls),
            "by_outcome": {OUTCOME_LABELS[k]: v for k, v in outcome_counts.items()},
            "by_date": [{"date": k, "count": v} for k, v in sorted(calls_by_date.items())],
        },
        "students": {
            "total_contacted": len(contacted_ids),
            "total_interviews": total_interviews,
        },
        "demographics": {
            "by_sex": dict(sex_counts),
            "by_strata": dict(sorted(strata_counts.items())),
            "top_cities": [{"city": k, "count": v} for k, v in city_counts.most_common(8)],
            "by_zone": dict(zone_counts),
        },
        "results": {
            "accepted_support": accepted,
            "refused_support": refused,
            "psychosocial_accompaniment": psychosocial,
            "critical_cases": critical,
            "referred": referred,
        },
        "interview_findings": {
            "study_hours": {k: study_hours_raw.get(k, 0) for k in study_hours_order},
            "autonomy": {k: autonomy_raw.get(k, 0) for k in autonomy_order},
            "motivation_dist": motivation_dist,
            "motivation_avg": round(sum(motivation_vals) / len(motivation_vals), 1) if motivation_vals else None,
            "teams": {"Sí": teams_yes, "No": teams_no},
            "email": {"Sí": email_yes, "No": email_no},
        },
    })


@bp.route("/api/reports/export")
def export():
    from_date_str = request.args.get("from_date")
    to_date_str = request.args.get("to_date")

    query = Call.query.order_by(Call.call_datetime)
    if from_date_str:
        try:
            from_dt = datetime.strptime(from_date_str, "%Y-%m-%d")
            query = query.filter(Call.call_datetime >= from_dt)
        except ValueError:
            pass
    if to_date_str:
        try:
            to_dt = datetime.strptime(to_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Call.call_datetime <= to_dt)
        except ValueError:
            pass

    rows = []
    for c in query.all():
        s = c.student
        iv = c.interview
        row = {
            "Documento": s.doc_number,
            "Estudiante": s.full_name,
            "Escuela": s.school or "",
            "Programa": s.program or "",
            "Edad": s.age,
            "Sexo": s.sex or "",
            "Ciudad": s.city or "",
            "Estrato": s.strata or "",
            "Teléfono": s.phone or "",
            "Lista": s.batch.filename,
            "Vigencia lista": s.batch.validity_date.isoformat(),
            "Estado actual": STATUS_LABELS.get(s.call_status, s.call_status),
            "N° llamada": c.call_number,
            "Fecha llamada": c.call_datetime.strftime("%d/%m/%Y"),
            "Hora llamada": c.call_datetime.strftime("%H:%M"),
            "Resultado": OUTCOME_LABELS.get(c.outcome, c.outcome),
            "Reagendado para": c.rescheduled_to.strftime("%d/%m/%Y %H:%M") if c.rescheduled_to else "",
            "Notas llamada": c.notes or "",
        }
        if iv:
            row.update({
                "Actividad además de estudiar": iv.activity_besides_studying or "",
                "Horas de estudio por día": iv.daily_study_hours or "",
                "Autonomía en virtualidad": iv.autonomy_virtuality or "",
                "Lo más difícil (virtual)": iv.virtual_most_difficult or "",
                "Lo más fácil (virtual)": iv.virtual_most_easy or "",
                "¿Accedió a Teams?": "Sí" if iv.has_teams_access else ("No" if iv.has_teams_access is False else ""),
                "¿Accedió al correo inst.?": "Sí" if iv.has_email_access else ("No" if iv.has_email_access is False else ""),
                "Motivación semestre (1-5)": iv.career_motivation or "",
                "Acompañamiento psicosocial": "Sí" if iv.psychosocial_accompaniment else "No",
                "Notas psicosocial": iv.psychosocial_notes or "",
                "Acompañamiento psicoeducativo": "Sí" if iv.psychoeducational_accompaniment else "No",
                "Notas psicoeducativo": iv.psychoeducational_notes or "",
                "Seguimiento": iv.follow_up or "",
                "Comentarios adicionales": iv.additional_comments or "",
                "Aceptó seguimiento": "Sí" if iv.accepted_support else ("No" if iv.accepted_support is False else ""),
                "Caso crítico": "Sí" if iv.is_critical else "No",
            })
        rows.append(row)

    df = pd.DataFrame(rows)
    report_dir = current_app.config["REPORT_FOLDER"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"reporte_llamadas_{timestamp}.xlsx"
    filepath = os.path.join(report_dir, filename)

    with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Detalle Llamadas")
        workbook = writer.book
        worksheet = writer.sheets["Detalle Llamadas"]
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#4472C4", "font_color": "white",
            "border": 1, "text_wrap": True
        })
        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_fmt)
            worksheet.set_column(col_num, col_num, max(15, len(col_name) + 2))

    return send_file(filepath, as_attachment=True, download_name=filename)
