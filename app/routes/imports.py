import os
import json
from datetime import date, datetime
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, ExcelBatch, Student

bp = Blueprint("imports", __name__)

# Mapeo de columnas del Excel a campos del modelo
COLUMN_MAP = {
    "Doc": "doc_number",
    "Estudiante": "full_name",
    "Edad": "age",
    "Sexo": "sex",
    "Identidad de genero": "gender_identity",
    "Orientacion sexual": "sexual_orientation",
    "Ciudad": "city",
    "Departamento": "department",
    "Zona de residencia": "zone",
    "Estrato": "strata",
    "Estado civil": "marital_status",
    "Con quien vive actualmente": "lives_with",
    "Escuela": "school",
    "Programa": "program",
    "Con condicion medica": "has_medical_condition",
    "Cual condicion medica especifica": "medical_condition_detail",
    "Asiste a algún tipo de terapia": "attends_therapy",
    "Cual tipo de terapia": "therapy_type",
    "Alguna vez un profesional de la salud le ha dado un diagnostico relacionado con salud mental?": "has_psychiatric_diagnosis",
    "cuál fue el diagnostico recibido?": "psychiatric_diagnosis_detail",
    "De donde provienen los recursos economicos con los que usted estudiara en la UNAD": "economic_resources",
    "Usted depende economicamente de alguien": "depends_economically",
    "Recibe apoyo de su familia o entorno cercano en su proceso academico?": "family_support",
    "En terminos generales ¿esta satisfecho con quien es?": "life_satisfaction",
    "Con respecto a su actitud frente la vida ¿como se describiria?": "attitude_toward_life",
    "Que importancia le da al cuidado de su salud mental actualmente?": "importance_mental_health",
    "Le gustaria recibir acompañamiento psicosocial en la UNAD?": "wants_psychosocial_support",
}


def parse_excel(filepath):
    df = pd.read_excel(filepath, dtype=str)
    df = df.where(pd.notna(df), None)
    return df


@bp.route("/importar", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "preview":
            file = request.files.get("excel_file")
            if not file or not file.filename.endswith((".xlsx", ".xls")):
                flash("Selecciona un archivo Excel válido.", "danger")
                return redirect(url_for("imports.index"))

            upload_dir = current_app.config["UPLOAD_FOLDER"]
            filepath = os.path.join(upload_dir, file.filename)
            file.save(filepath)

            try:
                df = parse_excel(filepath)
                total = len(df)
                # Check for duplicates vs existing students
                existing_docs = set(
                    r[0] for r in db.session.query(Student.doc_number).all()
                )
                new_docs = []
                dup_docs = []
                for _, row in df.iterrows():
                    doc = str(row.get("Doc", "")).strip()
                    if doc in existing_docs:
                        dup_docs.append(doc)
                    else:
                        new_docs.append(doc)

                preview = df.head(5).to_dict(orient="records")
                return render_template(
                    "import.html",
                    step="confirm",
                    filename=file.filename,
                    filepath=filepath,
                    total=total,
                    new_count=len(new_docs),
                    dup_count=len(dup_docs),
                    columns=list(df.columns),
                    preview=preview,
                )
            except Exception as e:
                flash(f"Error al leer el archivo: {e}", "danger")
                return redirect(url_for("imports.index"))

        elif action == "confirm":
            filepath = request.form.get("filepath")
            filename = request.form.get("filename")
            validity_str = request.form.get("validity_date")
            notes = request.form.get("notes", "")

            if not validity_str:
                flash("Debes definir una fecha de vigencia.", "danger")
                return redirect(url_for("imports.index"))

            validity_date = datetime.strptime(validity_str, "%Y-%m-%d").date()

            batch = ExcelBatch(
                filename=filename,
                import_date=date.today(),
                validity_date=validity_date,
                notes=notes,
            )
            db.session.add(batch)
            db.session.flush()

            df = parse_excel(filepath)
            existing_docs = set(
                r[0] for r in db.session.query(Student.doc_number).all()
            )
            imported = 0
            skipped = 0

            for idx, row in df.iterrows():
                doc = str(row.get("Doc", "")).strip()
                if not doc or doc in existing_docs:
                    skipped += 1
                    continue

                raw = {k: (v if v is not None else None) for k, v in row.items()}
                kwargs = {"batch_id": batch.id, "row_order": idx, "raw_data": raw}

                for excel_col, field in COLUMN_MAP.items():
                    val = row.get(excel_col)
                    if val is not None:
                        val = str(val).strip()
                    if field == "age" and val:
                        try:
                            val = int(float(val))
                        except (ValueError, TypeError):
                            val = None
                    kwargs[field] = val

                if not kwargs.get("doc_number") or not kwargs.get("full_name"):
                    skipped += 1
                    continue

                student = Student(**kwargs)
                db.session.add(student)
                imported += 1

            db.session.commit()
            flash(f"Importación completada: {imported} estudiantes nuevos, {skipped} omitidos.", "success")
            return redirect(url_for("imports.index"))

    batches = ExcelBatch.query.order_by(ExcelBatch.import_date.desc()).all()
    return render_template("import.html", step="upload", batches=batches)
