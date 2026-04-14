# DentaMap — Diagnostic Tool Cloud
# Radiant Dental Care | Dr. Jay Siddiqui
# Deploy: Render (PostgreSQL) or local (SQLite)
import psycopg2
import psycopg2.extras
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS exams (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id          TEXT    UNIQUE NOT NULL,
    patient_id       TEXT,
    patient_name    TEXT    NOT NULL,
    responses_json  TEXT    NOT NULL,
    overall_score    REAL,
    overall_assessment TEXT,
    category_scores_json TEXT,
    treatment_areas_json TEXT,
    implant_risk_json    TEXT,
    dentist_notes   TEXT,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS auth (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL   -- bcrypt hash
);
"""

_auth_checked = False

def q(sql_s, pg_s):
    """Return SQLite or PostgreSQL query based on DB in use."""
    return pg_s if _use_pg else sql_s

def _ensure_db():
    with get_db() as db:
        if _use_pg:
            db.execute(SCHEMA_SQL)
        else:
            db.executescript(SCHEMA_SQL)
    _init_default_auth()

@contextmanager
def get_db():
    if _use_pg:
        conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require",
                               cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = False
    else:
        conn = sqlite3.connect(DATABASE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def _init_default_auth():
    """Create default admin user if no users exist."""
def _init_default_auth():
    import bcrypt
    with get_db() as db:
        cur = db.execute("SELECT id FROM auth LIMIT 1")
        row = cur.fetchone()
        if not row:
            pw_hash = bcrypt.hashpw(b"RDC-KOIS-2026!", bcrypt.gensalt())
            if _use_pg:
                db.execute("INSERT INTO auth (username, password) VALUES (%s, %s)", ("admin", pw_hash))
            else:
                db.execute("INSERT INTO auth (username, password) VALUES (?, ?)", ("admin", pw_hash))
            logger.info("Default admin user created")

# ── Auth helpers ────────────────────────────────────────────────────────────────
def verify_password(username: str, password: str) -> bool:
    import bcrypt
    with get_db() as db:
        if _use_pg:
            cur = db.execute("SELECT password FROM auth WHERE username = %s", (username,))
        else:
            cur = db.execute("SELECT password FROM auth WHERE username = ?", (username,))
        row = cur.fetchone()
    if not row:
        return False
    pwd_stored = bytes(row[0]) if _use_pg else bytes(row["password"])
    return bcrypt.checkpw(password.encode(), pwd_stored)

def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# ── Pydantic models ─────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class ExamSubmission(BaseModel):
    patient_name: str
    patient_id: Optional[str] = "WALK-IN"
    responses: Dict[str, int]
    include_implant: bool = False
    implant_responses: Optional[Dict[str, int]] = None
    dentist_notes: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

# ── KOIS scoring logic (mirrors kois_diagnostic_wizard_v3.py) ──────────────────
KOIS_CATEGORIES = [
    "biomechanical", "functional", "periodontal", "dentofacial"
]

QUESTION_MAP = {
    "biomechanical": [
        {"id":"biom_1","text":"Caries risk and active disease presence"},
        {"id":"biom_2","text":"Existing restoration quality and marginal integrity"},
        {"id":"biom_3","text":"Root health and structural integrity"},
        {"id":"biom_4","text":"Endodontic status and treatment outcome"},
        {"id":"biom_5","text":"Secondary decay around restorations"},
        {"id":"biom_6","text":"Tooth fracture risk and existing cracks"},
    ],
    "functional": [
        {"id":"func_1","text":"Centric relation — premature contacts and stability"},
        {"id":"func_2","text":"Lateral guidance — canine and group function quality"},
        {"id":"func_3","text":"Posterior interferences during excursions"},
        {"id":"func_4","text":"Vertical dimension of occlusion — loss or collapse"},
        {"id":"func_5","text":"Tooth mobility — assessed instrumentally"},
        {"id":"func_6","text":"TMD symptoms — pain, clicking, limited opening"},
    ],
    "periodontal": [
        {"id":"perio_1","text":"Probing depths — pocket severity"},
        {"id":"perio_2","text":"Bleeding on probing (BOP) — inflammatory response"},
        {"id":"perio_3","text":"Gingival recession — extent and severity"},
        {"id":"perio_4","text":"Alveolar bone levels — radiographic assessment"},
        {"id":"perio_5","text":"Furcation involvement — Glickman classification"},
        {"id":"perio_6","text":"Gingival health — color, texture, inflammation"},
    ],
    "dentofacial": [
        {"id":"dento_1","text":"Anterior tooth position — vertical and horizontal alignment"},
        {"id":"dento_2","text":"Midline alignment — maxillary/mandibular relationship"},
        {"id":"dento_3","text":"Buccal corridors — space and symmetry"},
        {"id":"dento_4","text":"Tooth color and shade match"},
        {"id":"dento_5","text":"Gingival contours — symmetry and zenith positions"},
        {"id":"dento_6","text":"Smile design — overall esthetic harmony"},
    ],
}

IMPLANT_QUESTIONS = {
    "impl_bone_volume":   "Bone volume — sufficient for implant placement without augmentation?",
    "impl_bone_density":  "Bone density — Misch D1-D4 classification",
    "impl_systemic_health":"Systemic health — includes smoking, diabetes, radiation, bisphosphonates",
    "impl_bruxism":       "Bruxism/clenching habits — implant fatigue risk",
    "impl_healing":       "Healing capacity — age, medications, previous implant experience",
}

INTERPRETATIONS = {
    (4.5, 5.0):  "Optimal — No treatment needed",
    (3.5, 4.49): "Good — Monitor/maintain, minor improvements possible",
    (2.5, 3.49): "Fair — Treatment consideration recommended",
    (1.5, 2.49): "Poor — Treatment recommended",
    (0.0, 1.49): "Critical — Immediate treatment necessary",
}

def interpret(score: float) -> str:
    for (lo, hi), text in INTERPRETATIONS.items():
        if lo <= score <= hi:
            return text
    return "Unknown"

def score_category(cat: str, responses: Dict[str, int]) -> dict:
    qs = QUESTION_MAP[cat]
    vals = []
    for q in qs:
        v = responses.get(q["id"])
        if v is None:
            raise HTTPException(400, f"Missing answer for: {q['text']}")
        if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= 5):
            raise HTTPException(400, f"Invalid score {v} for {q['text']} (must be 1-5)")
        vals.append(v)
    avg = round(sum(vals) / len(vals) * 2) / 2
    avg = max(1.0, min(5.0, avg))
    return {"score": avg, "interpretation": interpret(avg), "questions_answered": len(vals)}

def assess_implant(responses: Dict[str, int]) -> dict:
    required = ["impl_bone_volume","impl_bone_density","impl_systemic_health","impl_bruxism","impl_healing"]
    vals = {}
    for k in required:
        v = responses.get(k)
        if v is None:
            raise HTTPException(400, f"Missing: {k}")
        if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= 5):
            raise HTTPException(400, f"Invalid implant score {v}")
        vals[k] = v

    overall = round(sum(vals.values()) / 5 * 2) / 2
    if vals["impl_systemic_health"] <= 2:
        rating = "POOR"
    elif overall >= 4.5:
        rating = "EXCELLENT"
    elif overall >= 3.5:
        rating = "GOOD"
    elif overall >= 2.5:
        rating = "FAIR"
    else:
        rating = "POOR"

    recs = []
    if vals["impl_bone_volume"] <= 2:
        recs.append("Augmentation likely needed before implant placement")
    if vals["impl_bone_density"] <= 2:
        recs.append("Plan for slower osseointegration timeline (6-8 months)")
    if vals["impl_systemic_health"] <= 2:
        recs.append("Medical clearance and/or specialist consultation required")
    if vals["impl_bruxism"] >= 4:
        recs.append("Occlusal guard recommended post-implant")
    if vals["impl_healing"] <= 2:
        recs.append("Extended healing protocol and close monitoring")

    return {
        "overall_rating": rating,
        "overall_score": overall,
        "bone_volume": vals["impl_bone_volume"],
        "bone_density": vals["impl_bone_density"],
        "systemic_health": vals["impl_systemic_health"],
        "bruxism_risk": vals["impl_bruxism"],
        "healing_capacity": vals["impl_healing"],
        "recommendations": recs,
    }

def overall_interpretation(score: float) -> str:
    if score >= 4.5: return "Excellent risk profile — focus on maintenance and optimization"
    if score >= 3.5: return "Good overall health — targeted improvements recommended"
    if score >= 2.5: return "Fair condition — treatment planning needed across multiple areas"
    return "Poor overall health — comprehensive treatment planning essential"

# ── FastAPI app ────────────────────────────────────────────────────────────────
_ensure_db()

app = FastAPI(title="DentaMap API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Lock down to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple bearer-token auth (set via DETA_SECRET env var — see main.py)
AUTHORIZED_TOKEN = os.environ.get("KOIS_SECRET", "")

def require_auth(Authorization: str = ""):
    if not AUTHORIZED_TOKEN:
        return
    if not Authorization or Authorization != f"Bearer {AUTHORIZED_TOKEN}":
        raise HTTPException(401, "Unauthorized")

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/api/questions")
def get_questions():
    return {
        "categories": [
            {"key": k, "label": k.title(), "questions": QUESTION_MAP[k]}
            for k in KOIS_CATEGORIES
        ],
        "implant_questions": [
            {"id": kid, "text": txt}
            for kid, txt in IMPLANT_QUESTIONS.items()
        ],
    }

@app.post("/api/exam")
def submit_exam(sub: ExamSubmission):
    require_auth()
    if not sub.patient_name.strip():
        raise HTTPException(400, "Patient name required")

    # Score each category
    cat_scores = {}
    cat_vals = []
    for cat in KOIS_CATEGORIES:
        cs = score_category(cat, sub.responses)
        cat_scores[cat] = cs
        cat_vals.append(cs["score"])

    overall = round(sum(cat_vals) / len(cat_vals) * 2) / 2
    overall = max(1.0, min(5.0, overall))

    # Implant risk
    implant_risk = None
    if sub.include_implant and sub.implant_responses:
        implant_risk = assess_implant(sub.implant_responses)

    # Treatment areas (simplified)
    treatment = []
    for cat in KOIS_CATEGORIES:
        score = cat_scores[cat]["score"]
        if score < 4.5:
            treatment.append(f"**{cat.title()}:** {interpret(score)}")

    exam_id = f"EXAM-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    with get_db() as db:
        db.execute("""
            INSERT INTO exams
              (exam_id, patient_id, patient_name, responses_json,
               overall_score, overall_assessment, category_scores_json,
               treatment_areas_json, implant_risk_json, dentist_notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exam_id,
            sub.patient_id or "WALK-IN",
            sub.patient_name,
            json.dumps(sub.responses),
            overall,
            overall_interpretation(overall),
            json.dumps(cat_scores),
            json.dumps(treatment),
            json.dumps(implant_risk) if implant_risk else None,
            sub.dentist_notes or None,
            created_at,
        ))

    return {
        "exam_id": exam_id,
        "patient_name": sub.patient_name,
        "created_at": created_at,
        "overall_score": overall,
        "overall_assessment": overall_interpretation(overall),
        "category_scores": cat_scores,
        "treatment_areas": treatment,
        "implant_risk": implant_risk,
    }

@app.get("/api/exams")
def list_exams(limit: int = 30):
    require_auth()
    with get_db() as db:
        rows = db.execute(q(
            "SELECT exam_id, patient_id, patient_name, created_at, overall_score, overall_assessment FROM exams ORDER BY id DESC LIMIT ?",
            "SELECT exam_id, patient_id, patient_name, created_at, overall_score, overall_assessment FROM exams ORDER BY id DESC LIMIT %s"
        ), (limit,)).fetchall()
    return {
        "exams": [
            {
                "exam_id": r["exam_id"],
                "patient_id": r["patient_id"],
                "patient_name": r["patient_name"],
                "created_at": r["created_at"],
                "overall_score": r["overall_score"],
                "overall_assessment": r["overall_assessment"],
            }
            for r in rows
        ]
    }

@app.get("/api/exam/{exam_id}")
def get_exam(exam_id: str):
    require_auth()
    with get_db() as db:
        row = db.execute(q(
            "SELECT * FROM exams WHERE exam_id = ?",
            "SELECT * FROM exams WHERE exam_id = %s"
        ), (exam_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Exam not found")
    return {
        "exam_id": row["exam_id"],
        "patient_id": row["patient_id"],
        "patient_name": row["patient_name"],
        "created_at": row["created_at"],
        "overall_score": row["overall_score"],
        "overall_assessment": row["overall_assessment"],
        "category_scores": json.loads(row["category_scores_json"]),
        "treatment_areas": json.loads(row["treatment_areas_json"]),
        "implant_risk": json.loads(row["implant_risk_json"]) if row["implant_risk_json"] else None,
        "dentist_notes": row["dentist_notes"],
    }

@app.post("/api/auth/login")
def login(req: LoginRequest):
    ok = verify_password(req.username, req.password)
    if not ok:
        raise HTTPException(401, "Invalid credentials")
    token = AUTHORIZED_TOKEN or "dev-token"
    return {"token": token, "username": req.username}

@app.post("/api/auth/change-password")
def change_password(req: ChangePasswordRequest):
    require_auth()
    if not verify_password(req.username, req.old_password):
        raise HTTPException(401, "Old password incorrect")
    import bcrypt
    hashed = bcrypt.hashpw(req.new_password.encode(), bcrypt.gensalt())
    with get_db() as db:
        db.execute(q(
            "UPDATE auth SET password = ? WHERE username = ?",
            "UPDATE auth SET password = %s WHERE username = %s"
        ), (hashed, req.username))
    return {"status": "ok"}

# ── Health ──────────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

# EOF
