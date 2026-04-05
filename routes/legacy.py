from fastapi import APIRouter, HTTPException, Body
from database import get_db
from models.user import UserCreate
import sqlite3

router = APIRouter(tags=["Legacy Compatibility"])

@router.post("/register")
def legacy_register(user: UserCreate):
    # This route provides compatibility for the original mobile app registration path.
    with get_db() as db:
        existing = db.execute("SELECT nic FROM users WHERE nic = ?", (user.nic,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")
        
        try:
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
            return {"message": "User registered", "nic": user.nic}
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{nic}/skills")
def legacy_get_skills(nic: str):
    with get_db() as db:
        skills = db.execute(
            """
            SELECT S.code
            FROM system_skills S
            JOIN user_skill_codes US ON S.code = US.skill_code
            WHERE US.user_nic = ?
            """,
            (nic,),
        ).fetchall()
        return [s["code"] for s in skills]

@router.put("/user/{nic}/skills")
def legacy_update_skills(nic: str, skills: list[str]):
    with get_db() as db:
        db.execute("DELETE FROM user_skill_codes WHERE user_nic = ?", (nic,))
        for skill_code in skills:
            db.execute(
                "INSERT INTO user_skill_codes(user_nic, skill_code) VALUES (?, ?)",
                (nic, skill_code),
            )
        db.commit()
        return {"message": "Skills updated"}

@router.patch("/user/{nic}")
def legacy_update_profile(nic: str, payload: dict = Body(...)):
    with get_db() as db:
        user = db.execute("SELECT nic FROM users WHERE nic = ?", (nic,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not payload:
            return {"message": "No changes"}
            
        fields = ", ".join(f"{k} = ?" for k in payload.keys())
        values = list(payload.values())
        values.append(nic)
        
        db.execute(f"UPDATE users SET {fields} WHERE nic = ?", values)
        db.commit()
        
        # Return updated user as expected by the app
        updated = db.execute("SELECT * FROM users WHERE nic = ?", (nic,)).fetchone()
        return dict(updated)
