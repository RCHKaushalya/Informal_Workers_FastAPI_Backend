from fastapi import APIRouter, HTTPException, Query
from database import get_db
from models.job import JobCreate, JobStatusUpdate
from datetime import datetime
import json

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
        
        if job.skills:
            for skill_code in job.skills:
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

@router.patch("/{job_id}/status")
def update_job_status(job_id: int, payload: JobStatusUpdate):
    with get_db() as db:
        job = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        db.execute("UPDATE jobs SET status = ? WHERE id = ?", (payload.status, job_id))
        db.commit()
        return {"message": "Job status updated"}
