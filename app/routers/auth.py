from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
)

router = APIRouter()


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
        password_hash=hash_password(credentials.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "user_id": new_user.id
    }


@router.post("/login")
async def login(credentials: UserCredentials, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(
        credentials.password,
        user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.username})

    return {"token": token, "user_id": user.id}