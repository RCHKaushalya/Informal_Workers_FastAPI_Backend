from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from models.user import UserCreate, UserLogin
import sqlite3

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
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

@router.post("/register")
def register_user(user: UserCreate):
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

@router.post("/register/volunteer")
def register_volunteer(user: UserCreate):
    with get_db() as db:
        existing = db.execute("SELECT nic FROM users WHERE nic = ?", (user.nic,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")
        
        try:
            db.execute(
                """
                INSERT INTO users(nic, first_name, last_name, phone, language, district, ds_area, pin, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'volunteer')
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
            return {"message": "Volunteer registered", "nic": user.nic, "role": "volunteer"}
        except sqlite3.Error as e:
            raise HTTPException(status_code=500, detail=str(e))
