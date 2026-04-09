from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

    documents = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan",
    )
