from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid
import jwt

router = APIRouter()

# Mock database
users_db = {}
SECRET_KEY = "my_super_secret_key"

class UserCredentials(BaseModel):
    username: str
    password: str

@router.post("/signup")
async def signup(credentials: UserCredentials):
    if credentials.username in users_db:
        raise HTTPException(status_code=409, detail="Username already exists")
    
    user_id = str(uuid.uuid4())
    users_db[credentials.username] = {
        "password": credentials.password,
        "user_id": user_id
    }
    
    return {"message": "User created successfully", "user_id": user_id}

@router.post("/login")
async def login(credentials: UserCredentials):
    user = users_db.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = jwt.encode({"sub": credentials.username}, SECRET_KEY, algorithm="HS256")
    
    return {"token": token, "user_id": user["user_id"]}
