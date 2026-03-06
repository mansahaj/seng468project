from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import jwt
from app.database import get_db
from app.models.user import User

router = APIRouter()

SECRET_KEY = "my_super_secret_key"

class UserCredentials(BaseModel):
    username: str
    password: str

@router.post("/signup")
async def signup(credentials: UserCredentials, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == credentials.username).first()
    if db_user:
        raise HTTPException(status_code=409, detail="Username already exists")
    
    new_user = User(
        username=credentials.username, 
        password_hash=credentials.password # In production, this MUST be hashed
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user_id": new_user.id}

@router.post("/login")
async def login(credentials: UserCredentials, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or user.password_hash != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = jwt.encode({"sub": credentials.username}, SECRET_KEY, algorithm="HS256")
    
    return {"token": token, "user_id": user.id}
