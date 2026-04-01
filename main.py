from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import get_db, init_db
from models.user import UserCreate, UserLogin, UserUpdate
from models.job import JobCreate, JobStatusUpdate

app = FastAPI(title="Informal Workers API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def home():
    return {"message": "API running"}


@app.post("/auth/login")
def login(payload: UserLogin):
    with get_db() as db:
        user = db.execute(
            """
            SELECT nic, first_name, last_name, district, ds_area, phone, language, pin, role, rating
            FROM users
            WHERE nic = ? AND pin = ?
            """,
            (payload.nic, payload.pin),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid NIC or PIN")
        return dict(user)


@app.post("/register")
def register_user(user: UserCreate):
    with get_db() as db:
        existing = db.execute("SELECT nic FROM users WHERE nic = ?", (user.nic,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")
        db.execute(
            """
            INSERT INTO users(nic, first_name, last_name, phone, language, district, ds_area, pin, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user')
            """,
            (
                user.nic,
                user.first_name,
                user.last_name,
                user.phone,
                user.language,
                user.district,
                user.ds_area,
                user.pin,
            ),
        )
        db.commit()
        created = db.execute(
            """
            SELECT nic, first_name, last_name, district, ds_area, phone, language, pin, role, rating
            FROM users WHERE nic = ?
            """,
            (user.nic,),
        ).fetchone()
        return dict(created)


@app.get("/user/{nic}")
def get_user(nic: str):
    with get_db() as db:
        user = db.execute(
            """
            SELECT nic, first_name, last_name, district, ds_area, phone, language, role, rating
            FROM users WHERE nic = ?
            """,
            (nic,),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user)


@app.patch("/user/{nic}")
def update_user(nic: str, payload: UserUpdate):
    updates: dict[str, object] = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"message": "No changes"}

    allowed = {"first_name", "last_name", "phone", "language", "district", "ds_area", "pin", "role"}
    if any(k not in allowed for k in updates):
        raise HTTPException(status_code=400, detail="Invalid fields")

    with get_db() as db:
        row = db.execute("SELECT nic FROM users WHERE nic = ?", (nic,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        sets = ", ".join([f"{k} = ?" for k in updates.keys()])
        db.execute(f"UPDATE users SET {sets} WHERE nic = ?", (*updates.values(), nic))
        db.commit()
        user = db.execute(
            """
            SELECT nic, first_name, last_name, district, ds_area, phone, language, role, rating
            FROM users WHERE nic = ?
            """,
            (nic,),
        ).fetchone()
        return dict(user)


@app.get("/user/{nic}/skills")
def get_user_skill_codes(nic: str):
    with get_db() as db:
        rows = db.execute(
            "SELECT skill_code FROM user_skill_codes WHERE user_nic = ? ORDER BY skill_code",
            (nic,),
        ).fetchall()
        return [r["skill_code"] for r in rows]


@app.put("/user/{nic}/skills")
def replace_user_skill_codes(nic: str, skill_codes: list[str]):
    with get_db() as db:
        user = db.execute("SELECT nic FROM users WHERE nic = ?", (nic,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.execute("DELETE FROM user_skill_codes WHERE user_nic = ?", (nic,))
        for code in skill_codes:
            db.execute(
                "INSERT OR IGNORE INTO user_skill_codes(user_nic, skill_code) VALUES (?, ?)",
                (nic, code),
            )
        db.commit()
        return {"message": "Skills updated", "skills": skill_codes}


@app.post("/jobs")
def create_job(job: JobCreate):
    with get_db() as db:
        employer = db.execute("SELECT nic FROM users WHERE nic = ?", (job.employer_nic,)).fetchone()
        if not employer:
            raise HTTPException(status_code=404, detail="Employer not found")

        cursor = db.execute(
            """
            INSERT INTO jobs(title, description, district, ds_area, location, date, time, status, employer_nic)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                job.title,
                job.description,
                job.district,
                job.ds_area,
                job.location,
                job.date,
                job.time,
                job.employer_nic,
            ),
        )
        job_id = cursor.lastrowid

        if job.skill_codes:
            for code in job.skill_codes:
                db.execute(
                    "INSERT OR IGNORE INTO job_skill_codes(job_id, skill_code) VALUES (?, ?)",
                    (job_id, code),
                )
        db.commit()
        return {"message": "Job created", "job_id": job_id}


@app.get("/jobs")
def get_jobs(
    status: str = Query(default="open"),
    district: str | None = None,
    ds_area: str | None = None,
):
    query = "SELECT * FROM jobs WHERE status = ?"
    params: list[object] = [status]
    if district:
        query += " AND district = ?"
        params.append(district)
    if ds_area:
        query += " AND ds_area = ?"
        params.append(ds_area)
    query += " ORDER BY created_at DESC, id DESC"

    with get_db() as db:
        jobs = db.execute(query, tuple(params)).fetchall()
        return [dict(job) for job in jobs]


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    with get_db() as db:
        job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        skills = db.execute(
            "SELECT skill_code FROM job_skill_codes WHERE job_id = ? ORDER BY skill_code",
            (job_id,),
        ).fetchall()
        return {**dict(job), "skill_codes": [r["skill_code"] for r in skills]}


@app.post("/jobs/{job_id}/apply")
def apply_job(job_id: int, worker_nic: str):
    with get_db() as db:
        job = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        user = db.execute("SELECT nic FROM users WHERE nic = ?", (worker_nic,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Worker not found")
        try:
            db.execute(
                "INSERT INTO applications(job_id, worker_nic, status) VALUES (?, ?, 'applied')",
                (job_id, worker_nic),
            )
            db.commit()
        except Exception:
            raise HTTPException(status_code=409, detail="Already applied")
        return {"message": "Applied successfully"}


@app.get("/jobs/{job_id}/applications")
def get_applications(job_id: int):
    with get_db() as db:
        applications = db.execute(
            """
            SELECT A.worker_nic, U.first_name, U.last_name, U.phone, A.status, A.created_at
            FROM applications AS A
            JOIN users AS U ON U.nic = A.worker_nic
            WHERE A.job_id = ?
            ORDER BY A.created_at DESC
            """,
            (job_id,),
        ).fetchall()
        return [dict(row) for row in applications]


@app.patch("/jobs/{job_id}/applications/{worker_nic}")
def update_application_status(job_id: int, worker_nic: str, payload: JobStatusUpdate):
    with get_db() as db:
        row = db.execute(
            "SELECT id FROM applications WHERE job_id = ? AND worker_nic = ?",
            (job_id, worker_nic),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Application not found")
        db.execute(
            "UPDATE applications SET status = ? WHERE job_id = ? AND worker_nic = ?",
            (payload.status, job_id, worker_nic),
        )
        db.commit()
        return {"message": "Status updated"}


@app.post("/jobs/{job_id}/reviews")
def create_review(job_id: int, worker_nic: str, employer_nic: str, rating: int, comment: str | None = None):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1..5")
    with get_db() as db:
        try:
            db.execute(
                """
                INSERT INTO reviews(job_id, worker_nic, employer_nic, rating, comment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, worker_nic, employer_nic, rating, comment),
            )
            db.commit()
        except Exception:
            raise HTTPException(status_code=409, detail="Review already exists")
        return {"message": "Review created"}


@app.get("/admin/users")
def admin_list_users(role: str | None = None):
    query = "SELECT nic, first_name, last_name, phone, language, district, ds_area, role, rating FROM users"
    params: list[object] = []
    if role:
        query += " WHERE role = ?"
        params.append(role)
    query += " ORDER BY first_name, last_name"
    with get_db() as db:
        rows = db.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]


@app.get("/admin/jobs")
def admin_list_jobs(status: str | None = None):
    query = "SELECT * FROM jobs"
    params: list[object] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC, id DESC"
    with get_db() as db:
        rows = db.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]


def _send_notification_placeholder(phone: str, message: str) -> None:
    # Integrate with your phone SMS gateway app here.
    print(f"SMS to {phone}: {message}")


@app.post("/jobs/{job_id}/notify")
def notify(job_id: int):
    with get_db() as db:
        job = db.execute("SELECT id, title, district FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        users = db.execute(
            """
            SELECT DISTINCT U.nic, U.phone
            FROM users AS U
            JOIN user_skill_codes AS US ON U.nic = US.user_nic
            JOIN job_skill_codes AS JS ON US.skill_code = JS.skill_code
            WHERE JS.job_id = ?
            AND U.district = ?
            """,
            (job_id, job["district"]),
        ).fetchall()
        for user in users:
            _send_notification_placeholder(user["phone"], f"New job available: {job['title']}")
        return {"message": "Notification triggered", "recipients": len(users)}