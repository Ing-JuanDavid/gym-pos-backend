from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import create_db_and_tables, boostrapt_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    boostrapt_db()
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}
