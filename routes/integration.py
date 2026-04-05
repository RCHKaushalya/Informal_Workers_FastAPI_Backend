import requests
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from database import get_db
from models.user import UserCreate
import urllib.parse
import sqlite3

router = APIRouter(prefix="/integration", tags=["Integrations"])

SMS_GATEWAY_KEY = "121a66e53543e2230b8075688522be30180d477c"
SMS_GATEWAY_URL = "https://app.sms-gateway.app/services/send.php"

def send_sms_task(number: str, message: str):
    params = {
        "key": SMS_GATEWAY_KEY,
        "number": number,
        "message": message,
        "option": "1",
        "type": "sms",
        "prioritize": "0"
    }
    try:
        response = requests.get(SMS_GATEWAY_URL, params=params, timeout=10)
        print(f"SMS Sent to {number}: {response.text}")
    except Exception as e:
        print(f"Failed to send SMS to {number}: {e}")

@router.post("/sms/notify-job")
def notify_job(job_id: int, background_tasks: BackgroundTasks):
    with get_db() as db:
        job = db.execute("SELECT id, title, district FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        users = db.execute(
            """
            SELECT DISTINCT U.phone
            FROM users AS U
            JOIN user_skill_codes AS US ON U.nic = US.user_nic
            JOIN job_skill_codes AS JS ON US.skill_code = JS.skill_code
            WHERE JS.job_id = ? AND U.district = ?
            """,
            (job_id, job["district"]),
        ).fetchall()
        
        for user in users:
            message = f"New job available: {job['title']}. Login to Informal Workers to apply."
            background_tasks.add_task(send_sms_task, user["phone"], message)
            
        return {"status": "success", "recipients": len(users)}

@router.post("/google-forms/register")
async def google_forms_register(request: Request):
    # Mapping Google Form fields to UserCreate model
    # Expecting: nic, first_name, last_name, phone, language, district, ds_area, pin
    try:
        data = await request.form()
        user_nic = data.get("nic") or data.get("NIC")
        if not user_nic:
            # Try JSON if form data is not present
            data = await request.json()
            user_nic = data.get("nic")
            
        if not user_nic:
             raise HTTPException(status_code=400, detail="NIC is required for registration")

        with get_db() as db:
            existing = db.execute("SELECT nic FROM users WHERE nic = ?", (user_nic,)).fetchone()
            if existing:
                return {"message": "User already exists", "nic": user_nic}
                
            db.execute(
                """
                INSERT INTO users(nic, first_name, last_name, phone, language, district, ds_area, pin, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user')
                """,
                (
                    user_nic,
                    data.get("first_name", "Unknown"),
                    data.get("last_name", "Form"),
                    data.get("phone", "0000000000"),
                    data.get("language", "English"),
                    data.get("district", "Global"),
                    data.get("ds_area", "Global"),
                    data.get("pin", "123456"),
                ),
            )
            db.commit()
            return {"message": "Google Form registration complete", "nic": user_nic}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
