from fastapi import APIRouter, HTTPException
from database import get_db
from models.user import UserUpdate
import sqlite3

router = APIRouter(prefix="/user", tags=["Users"])

@router.get("/{nic}/profile")
def get_full_profile(nic: str):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE nic = ?", (nic,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_dict = dict(user)
        if "pin" in user_dict:
            del user_dict["pin"]

        # Skills
        skills = db.execute(
            """
            SELECT S.name
            FROM system_skills S
            JOIN user_skill_codes US ON S.code = US.skill_code
            WHERE US.user_nic = ?
            """,
            (nic,),
        ).fetchall()
        user_dict["skills"] = [s["name"] for s in skills]

        # Stats
        completed = db.execute(
            "SELECT COUNT(*) as count FROM applications WHERE worker_nic = ? AND status = 'completed'",
            (nic,),
        ).fetchone()
        posted = db.execute("SELECT COUNT(*) as count FROM jobs WHERE employer_nic = ?", (nic,)).fetchone()
        user_dict["stats"] = {"completed_jobs": completed["count"], "posted_jobs": posted["count"]}

        # Reviews
        reviews = db.execute("SELECT * FROM reviews WHERE worker_nic = ?", (nic,)).fetchall()
        user_dict["reviews"] = [dict(r) for r in reviews]

        return user_dict

@router.put("/{nic}/profile")
def update_profile(nic: str, payload: UserUpdate):
    with get_db() as db:
        user = db.execute("SELECT nic FROM users WHERE nic = ?", (nic,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        updates = payload.dict(exclude_unset=True)
        if not updates:
            return {"message": "No changes"}
            
        fields = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values())
        values.append(nic)
        
        db.execute(f"UPDATE users SET {fields} WHERE nic = ?", values)
        db.commit()
        return {"message": "Profile updated"}

@router.get("/registry")
def get_user_registry():
    with get_db() as db:
        users = db.execute("SELECT nic, first_name, last_name, role, district, rating FROM users").fetchall()
        return [dict(u) for u in users]

@router.post("/{nic}/upgrade-to-volunteer")
def upgrade_user_to_volunteer(nic: str):
    with get_db() as db:
        user = db.execute("SELECT nic FROM users WHERE nic = ?", (nic,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        db.execute("UPDATE users SET role = 'volunteer' WHERE nic = ?", (nic,))
        db.commit()
        
        updated = db.execute("SELECT * FROM users WHERE nic = ?", (nic,)).fetchone()
        res = dict(updated)
        if "pin" in res:
            del res["pin"]
        return res
