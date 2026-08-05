from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()
from api.routes import router
from database import models
from database.database import engine

models.Base.metadata.create_all(bind=engine)
from contextlib import asynccontextmanager
from database.database import SessionLocal

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Loading ML models from database...")
    from database.models import PacenoteFeedback
    from geometry.classification_engine import train_model
    
    db = SessionLocal()
    try:
        all_feedbacks = db.query(PacenoteFeedback).all()
        # Group by driver
        driver_feedbacks = {}
        for fb in all_feedbacks:
            driver_feedbacks.setdefault(fb.driver_id, []).append(fb)
            
        for driver_id, feedbacks in driver_feedbacks.items():
            success = train_model(feedbacks, driver_id)
            if success:
                print(f"Loaded and trained ML model for driver: {driver_id}")
    except Exception as e:
        print(f"Error loading models: {e}")
    finally:
        db.close()
    yield
    # Shutdown logic
    print("Shutting down...")

app = FastAPI(
    title="RecceMind MVP",
    description="Motor geométrico para notas de rally",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "RecceMind API is running. Geometry engine initialized."}
