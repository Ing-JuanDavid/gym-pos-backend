from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import Session
from app.database import create_db_and_tables, boostrapt_db, engine
from app.routers import customers, plan, membership, attendance, sale, payment, cash
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.jobs import expire_memberships
from datetime import datetime


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
    scheduler.add_job(job_expire, "cron", hour=0, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)


app.include_router(customers.router)
app.include_router(plan.router)

app.include_router(membership.router)

app.include_router(attendance.router)

app.include_router(sale.router)

app.include_router(payment.router)

app.include_router(cash.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
