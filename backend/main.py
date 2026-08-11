from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import settings
from database.database import SessionLocal, engine
from database.models import Base, PacenoteFeedback
from geometry.classification_engine import train_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_db:
        Base.metadata.create_all(bind=engine)

    database = SessionLocal()
    try:
        feedbacks = database.query(PacenoteFeedback).all()
        feedbacks_by_driver: dict[str, list[PacenoteFeedback]] = {}
        for feedback in feedbacks:
            feedbacks_by_driver.setdefault(feedback.driver_id, []).append(feedback)
        for driver_id, driver_feedbacks in feedbacks_by_driver.items():
            if train_model(driver_feedbacks, driver_id):
                logger.info("Loaded personalized classifier for driver %s", driver_id)
    except Exception:
        logger.exception("Could not preload personalized classifiers")
    finally:
        database.close()
    yield


app = FastAPI(
    title="RecceMind API",
    description="Motor geométrico para generar borradores de notas de rally",
    version="0.3.0",
    lifespan=lifespan,
)

origins = list(settings.allowed_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-RecceMind-Token"],
)
app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "RecceMind API is running",
        "health": "/api/health",
        "docs": "/docs",
        "service_auth": "enabled" if settings.service_token else "disabled",
    }
