from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ExcelBatch(db.Model):
    __tablename__ = "excel_batch"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    import_date = db.Column(db.Date, nullable=False, default=date.today)
    validity_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    students = db.relationship("Student", back_populates="batch", lazy="dynamic")

    @property
    def is_active(self):
        return date.today() <= self.validity_date

    @property
    def student_count(self):
        return self.students.count()


class Student(db.Model):
    __tablename__ = "student"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("excel_batch.id"), nullable=False)
    batch = db.relationship("ExcelBatch", back_populates="students")

    # Identificación
    doc_number = db.Column(db.String(30), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(255), nullable=False)

    # Datos académicos
    school = db.Column(db.String(255))
    program = db.Column(db.String(255))

    # Datos personales
    age = db.Column(db.Integer)
    sex = db.Column(db.String(10))
    gender_identity = db.Column(db.String(50))
    sexual_orientation = db.Column(db.String(50))
    city = db.Column(db.String(100))
    department = db.Column(db.String(100))
    zone = db.Column(db.String(50))  # Urbana / Rural
    strata = db.Column(db.String(20))
    marital_status = db.Column(db.String(50))
    lives_with = db.Column(db.String(100))

    # Indicadores de riesgo clínicos
    has_medical_condition = db.Column(db.String(5))   # S/N
    medical_condition_detail = db.Column(db.Text)
    attends_therapy = db.Column(db.String(5))          # S/N
    therapy_type = db.Column(db.Text)
    has_psychiatric_diagnosis = db.Column(db.String(5))  # S/N/No
    psychiatric_diagnosis_detail = db.Column(db.Text)

    # Indicadores socioeconómicos
    economic_resources = db.Column(db.String(255))
    depends_economically = db.Column(db.String(5))
    family_support = db.Column(db.String(10))  # Si/No/etc
    enrollment_funding = db.Column(db.String(255))

    # Indicadores de bienestar / autopercepción
    life_satisfaction = db.Column(db.String(100))
    attitude_toward_life = db.Column(db.String(255))
    importance_mental_health = db.Column(db.String(100))
    wants_psychosocial_support = db.Column(db.String(50))

    # Contacto
    phone = db.Column(db.String(30))

    # Estado en el proceso de llamadas
    # not_marked | pending | in_progress | rescheduled |
    # closed_no_answer | closed_refused | closed_referred | closed_critical
    call_status = db.Column(db.String(30), nullable=False, default="not_marked")
    is_marked_for_call = db.Column(db.Boolean, nullable=False, default=False)
    marked_date = db.Column(db.Date)

    # Orden original en el Excel (para respetar el orden de llamadas)
    row_order = db.Column(db.Integer)

    # Todos los datos originales del Excel
    raw_data = db.Column(db.JSON)

    calls = db.relationship("Call", back_populates="student", lazy="dynamic",
                            order_by="Call.call_datetime")

    @property
    def is_active(self):
        return self.batch.is_active

    @property
    def call_count(self):
        return self.calls.count()

    @property
    def last_call(self):
        return self.calls.order_by(Call.call_datetime.desc()).first()

    @property
    def next_rescheduled_call(self):
        return (self.calls
                .filter(Call.rescheduled_to.isnot(None))
                .order_by(Call.rescheduled_to.asc())
                .first())

    def to_dict(self):
        return {
            "id": self.id,
            "doc_number": self.doc_number,
            "full_name": self.full_name,
            "school": self.school,
            "program": self.program,
            "age": self.age,
            "sex": self.sex,
            "city": self.city,
            "strata": self.strata,
            "phone": self.phone,
            "call_status": self.call_status,
            "is_marked_for_call": self.is_marked_for_call,
            "call_count": self.call_count,
            "is_active": self.is_active,
            "batch_filename": self.batch.filename,
            "batch_validity": self.batch.validity_date.isoformat(),
        }


class Call(db.Model):
    __tablename__ = "call"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    student = db.relationship("Student", back_populates="calls")

    call_number = db.Column(db.Integer, nullable=False)  # 1, 2 o 3
    call_datetime = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # no_answer | no_time | completed | critical
    outcome = db.Column(db.String(20), nullable=False)

    # Solo si outcome == 'no_time' y pidió reagendar con hora específica
    rescheduled_to = db.Column(db.DateTime)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    interview = db.relationship("CallInterview", back_populates="call",
                                uselist=False, cascade="all, delete-orphan")


class CallInterview(db.Model):
    __tablename__ = "call_interview"
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey("call.id"), nullable=False)
    call = db.relationship("Call", back_populates="interview")

    # Preguntas de la entrevista
    activity_besides_studying = db.Column(db.Text)
    daily_study_hours = db.Column(db.String(30))        # "1 hora" / "De 2 a 4 horas" / "Más de 4 horas"
    autonomy_virtuality = db.Column('difficulty_strategy', db.String(20))  # "Buena" / "Regular" / "Mala"
    virtual_most_difficult = db.Column('personal_issues', db.Text)
    virtual_most_easy = db.Column(db.Text)
    career_motivation = db.Column(db.Integer)            # 1-5

    # Acompañamiento psicosocial (ayuda administrativa puntual en la sesión)
    psychosocial_accompaniment = db.Column(db.Boolean, default=False)
    psychosocial_notes = db.Column(db.Text)

    # Acompañamiento psicoeducativo
    psychoeducational_accompaniment = db.Column(db.Boolean, default=False)
    psychoeducational_notes = db.Column(db.Text)

    # Seguimiento (texto libre para quien continúe el caso)
    follow_up = db.Column(db.Text)

    additional_comments = db.Column(db.Text)

    # Herramientas digitales
    has_teams_access = db.Column(db.Boolean)
    has_email_access = db.Column(db.Boolean)

    # Resultado de la llamada
    accepted_support = db.Column(db.Boolean)
    referred = db.Column(db.Boolean, default=False)
    is_critical = db.Column(db.Boolean, default=False)
