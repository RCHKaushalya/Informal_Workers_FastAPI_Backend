from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from models.skill import SkillCreate
import sqlite3

router = APIRouter(prefix="/admin", tags=["Administrator"])

@router.get("/stats")
def get_system_stats():
    with get_db() as db:
        user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        job_count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        app_count = db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        volunteer_count = db.execute("SELECT COUNT(*) FROM users WHERE role = 'volunteer'").fetchone()[0]
        
        return {
            "total_users": user_count,
            "total_jobs": job_count,
            "total_applications": app_count,
            "total_volunteers": volunteer_count
        }

@router.get("/skills")
def get_system_skills():
    with get_db() as db:
        skills = db.execute("SELECT * FROM system_skills").fetchall()
        return [dict(s) for s in skills]

@router.post("/skills")
def add_system_skill(skill: SkillCreate):
    code = skill.name.lower().replace(" ", "_")
    with get_db() as db:
        try:
            db.execute(
                "INSERT INTO system_skills(code, name) VALUES (?, ?)",
                (code, skill.name)
            )
            db.commit()
            return {"code": code, "name": skill.name}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Skill already exists")

@router.delete("/skills/{code}")
def delete_system_skill(code: str):
    with get_db() as db:
        db.execute("DELETE FROM system_skills WHERE code = ?", (code,))
        db.commit()
        return {"message": "Skill deleted"}

@router.get("/reports/user-growth")
def user_growth_report():
    # Placeholder for a real report
    return [
        {"date": "2026-03-25", "count": 10},
        {"date": "2026-04-01", "count": 25},
        {"date": "2026-04-05", "count": 42},
    ]
