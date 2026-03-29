from fastapi import FastAPI
from database import get_db, init_db
from models.user import UserCreate
from models.skill import SkillCreate
from models.job import JobCreate

app = FastAPI()

@app.on_event('startup')
def startup():
    init_db()

@app.get('/')
def home():
    return {'message': 'API running'}

@app.post('/register')
def register_user(user: UserCreate):
    db = get_db()

    db.execute(
        "INSERT INTO users(nic, first_name, last_name, phone, language) VALUES (?, ?, ?, ?, ?)",
        (
            user.nic,
            user.first_name,
            user.last_name,
            user.phone,
            user.language,
        )
    )

    db.commit()

    return {'message': 'User registered'}

@app.get('/user/{nic}')
def get_user(nic: str):
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE nic = ?",
        (nic,)
    ).fetchone()

    if not user:
        return {'error': 'User not found'}
    
    return dict(user)

@app.get('/user/{nic}/completed-jobs')
def completed_jobs(nic: str):
    db = get_db()

    count = db.execute(
        "SELECT COUNT(*) AS total FROM applications WHERE user_nic = ? AND status = 'completed'",
        (nic,)
    ).fetchone()['total']

    return {'completed jobs': count}

@app.get('/user/{nic}/profile')
def full_profile(nic: str):
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE nic = ?",
        (nic,)
    ).fetchone()

    if not user:
        return {'error': 'User not found'}
    
    skills = db.execute(
        """
            SELECT skills.id, skills.name
            FROM skills
            JOIN user_skills On skills.id = user_skills.skill_id
            WHERE user_skills.user_nic = ?
        """,
        (nic,)
    ).fetchall()
    
    completed_jobs = db.execute(
        "SELECT COUNT(*) AS total FROM applications WHERE user_nic = ? AND status = 'completed'",
        (nic,)
    ).fetchone()['total']

    return {
        'user': user,
        'skills': [skill['name'] for skill in skills],
        'completed_jobs': completed_jobs
    }

@app.post('/skills')
def add_skill(skill: SkillCreate):
    db = get_db()

    try:
        db.execute(
            'INSERT INTO skills (name) VALUES (?)',
            (skill.name,)
        )
        db.commit()
        return {'message': 'Skill added'}
    except:
        return {'error': 'Skill already added'}

@app.post('/user/{nic}/skills/{skill_id}')
def add_skill_to_user(nic: str, skill_id: int):
    db = get_db()

    try:
        db.execute(
            "INSERT INTO user_skills (user_nic, skill_id) VALUES (?, ?)",
            (nic, skill_id)
        )
        db.commit()
        return {'message': 'Skill assigned'}
    except:
        return {'error': 'Skill already assigned'}
    
@app.get('/user/{nic}/skills')
def get_user_skills(nic: str):
    db = get_db()

    skills = db.execute(
        """
            SELECT skills.id, skills.name
            FROM skills
            JOIN user_skills On skills.id = user_skills.skill_id
            WHERE user_skills.user_nic = ?
        """,
        (nic,)
    ).fetchall()

    return [dict(skill) for skill in skills]

@app.post('/jobs')
def create_job(job: JobCreate):
    db = get_db()

    user = db.execute(
        """
            SELECT district, ds FROM users
            WHERE nic = ?
        """,
        (job.employer_nic,)
    ).fetchone()

    cursor = db.execute(
        """
            INSERT INTO jobs(title, description, district, ds, employer_id, status) VALUES
                (?, ?, ?, ?, ?, ?, 'open')
        """,
        (job.title, job.description, user['district'], user['ds'], job.employer_nic)
    )

    db.commit()

    job_id = cursor.lastrowid

    send_notification(job_id)

    return {'message': 'Job Created', 'job_id': job_id}

@app.get('/jobs')
def get_jobs():
    db =  get_db()

    jobs = db.execute(
        """
            SELECT * FROM jobs
            WHERE status = 'open'
        """
    ).fetchall()

    return [dict(job) for job in jobs]

@app.post('/jobs/{job_id}/apply/{nic}')
def apply_job(job_id: int, nic: str):
    db = get_db()

    db.execute(
        """
            INSERT INTO applications (job_id, user_nic, status) VALUES
            (?, ?, 'applied')
        """,
        (job_id, nic)
    )
    db.commit()

    return {'message': 'Applied successfully'}


@app.get('/jobs/{job_id}/applications')
def get_applications(job_id: int):
    db = get_db()

    applications = db.execute(
        """
            SELECT U.first_name, U.last_name, A.status
            FROM users AS U
            JOIN applications AS A ON U.nic = A.user_nic
            WHERE A.job_id = ?
        """,
        (job_id,)
    ).fetchall()

    return [dict(application) for application in applications]

@app.post('/applications/{job_id}/{nic}/status')
def update_applications(job_id: int, nic: str, status: str):
    db = get_db()

    db.execute(
        """
            UPDATE applications
            SET status = ?
            WHERE job_id = ? AND user_nic = ?
        """,
        (status, job_id, nic)
    )
    db.commit()

    return {'message': 'Status updated'}

@app.post('/applications/{job_id}/{nic}/completed')
def update_applications(job_id: int, nic: str):
    db = get_db()

    db.execute(
        """
            UPDATE applications
            SET status = 'completed'
            WHERE job_id = ? AND user_nic = ?
        """,
        (job_id, nic)
    )
    db.commit()

    return {'message': 'Job marked as completed'}

@app.post('/jobs/{job_id}/skills/{skill_id}')
def add_skill_to_job(job_id: int, skill_id: int):
    db = get_db()

    try:
        db.execute(
            "INSERT INTO job_skills (job_id, skill_id) VALUES (?, ?)",
            (job_id, skill_id)
        )
        db.commit()
        return {'message': 'Skill assigned to job'}
    except:
        return {'error': 'Skill already assigned'}
    
@app.get('/job/{nic}/skills')
def get_job_skills(job_id: int):
    db = get_db()

    skills = db.execute(
        """
            SELECT skills.id, skills.name
            FROM skills
            JOIN job_skills On skills.id = job_skills.skill_id
            WHERE job_skills.job_id = ?
        """,
        (job_id,)
    ).fetchall()

    return [dict(skill) for skill in skills]

def find_matching_users(job_id: int):
    db = get_db()

    job = db.execute(
        """
            SELECT district FROM jobs WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    users = db.execute(
        """
            SELECT DISTINCT U.nic, U.phone
            FROM users AS U
            JOIN user_skills AS US ON U.nic = US.user_nic
            JOIN job_skills AS JS ON US.skill_id = AS.skill_id
            WHERE JS.job_id = ?
            AND U.district = ?
        """,
        (job_id, job['district'])
    ).fetchall()

    return users

def send_notification(job_id: int):
    users = find_matching_users(job_id)

    for user in users:
        phone = user['phone']
        print(f"📩 SMS to {phone}: New job available! Check app.")

@app.post('/jobs/{job_id}/notify')
def notify(job_id: int):
    send_notification(job_id)
    return {'message': 'Notification Sent'}