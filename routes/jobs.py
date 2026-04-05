from fastapi import APIRouter, HTTPException, Query
from database import get_db
from models.job import JobCreate, JobStatusUpdate
from datetime import datetime
import json
import sqlite3

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("")
def create_job(job: JobCreate):
    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO jobs(title, description, district, ds_area, location, date, time, employer_nic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            for skill_code in job.skill_codes:
                db.execute(
                    "INSERT INTO job_skill_codes(job_id, skill_code) VALUES (?, ?)",
                    (job_id, skill_code),
                )
        db.commit()
        return {"id": job_id, "message": "Job created"}

@router.get("")
def search_jobs(
    district: str | None = None,
    skill: str | None = None,
    status: str = "open"
):
    with get_db() as db:
        query = "SELECT * FROM jobs WHERE status = ?"
        params = [status]
        
        if district:
            query += " AND district = ?"
            params.append(district)
            
        if skill:
            query += """ AND id IN (
                SELECT job_id FROM job_skill_codes WHERE skill_code = ?
            )"""
            params.append(skill)
            
        jobs = db.execute(query, params).fetchall()
        return [dict(j) for j in jobs]

@router.get("/suitable")
def get_suitable_jobs(user_nic: str = Query(...)):
    with get_db() as db:
        # Get user skills and district
        user = db.execute("SELECT district FROM users WHERE nic = ?", (user_nic,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_skills = db.execute(
            "SELECT skill_code FROM user_skill_codes WHERE user_nic = ?",
            (user_nic,)
        ).fetchall()
        skill_codes = [s["skill_code"] for s in user_skills]
        
        if not skill_codes:
            return []
            
        # Find jobs in same district with matching skills
        placeholders = ", ".join("?" for _ in skill_codes)
        query = f"""
            SELECT DISTINCT J.*, 
            (SELECT COUNT(*) FROM job_skill_codes JS WHERE JS.job_id = J.id AND JS.skill_code IN ({placeholders})) as match_count
            FROM jobs J
            JOIN job_skill_codes JS ON J.id = JS.job_id
            WHERE J.status = 'open' 
            AND J.district = ?
            AND JS.skill_code IN ({placeholders})
            ORDER BY match_count DESC, J.created_at DESC
        """
        params = skill_codes + [user["district"]] + skill_codes
        jobs = db.execute(query, params).fetchall()
        return [dict(j) for j in jobs]


@router.get("/{job_id}")
def get_job_details(job_id: int):
    with get_db() as db:
        job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        job_dict = dict(job)
        skills = db.execute(
            "SELECT skill_code FROM job_skill_codes WHERE job_id = ?",
            (job_id,)
        ).fetchall()
        job_dict["skills"] = [s["skill_code"] for s in skills]
        return job_dict

@router.post("/{job_id}/apply")
def apply_for_job(job_id: int, worker_nic: str = Query(...)):
    with get_db() as db:
        # Verify job exists and worker exists
        job = db.execute("SELECT id, status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job or job["status"] != "open":
            raise HTTPException(status_code=400, detail="Job not available")
            
        try:
            db.execute(
                "INSERT INTO applications(job_id, worker_nic, status) VALUES (?, ?, 'applied')",
                (job_id, worker_nic)
            )
            db.commit()
            return {"message": "Application successful"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Already applied")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
