from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers import auth, documents, search
from .database import engine, Base
from .models import chunk, document, user

# Create database tables
import time
time.sleep(5)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Semantic Retrieval API")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(search.router, prefix="/search", tags=["Search"])

# Serve static files for the frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def root():
    return FileResponse("app/static/index.html")
