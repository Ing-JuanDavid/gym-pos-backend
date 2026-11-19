from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import Session
from app.database import create_db_and_tables, boostrapt_db, engine
from app.routers import customers, devices_ws, plan, membership, attendance, sale, payment, cash, fingerprint, capture, events
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.jobs import expire_memberships
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from fastapi.staticfiles import StaticFiles

Path("media/captures").mkdir(parents=True, exist_ok=True)


scheduler = BackgroundScheduler()


def job_expire():
    try:
        with Session(engine) as session:
            expire_memberships(session)
            print(f"[{datetime.now()}] Job ejecutado: membresías revisadas")
    except Exception as e:
        print(f"[{datetime.now()}] Error en job_expire: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_db_and_tables()
    # boostrapt_db()
    # Job 1: expira membresías cada día a medianoche
    # scheduler.add_job(job_expire, "cron", hour=6, minute=00)
    # scheduler.start()
    job_expire()
    yield
    # scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(customers.router)
app.include_router(plan.router)

app.include_router(membership.router)

app.include_router(attendance.router)

app.include_router(sale.router)

app.include_router(payment.router)

app.include_router(cash.router)

app.include_router(events.router)


app.include_router(devices_ws.router)
app.include_router(fingerprint.router)

app.include_router(capture.router)

(Path("media") / "captures").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")


@app.get("/")
async def root():
    return {"message": "Hello World"}
