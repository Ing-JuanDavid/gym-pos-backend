from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import create_db_and_tables, boostrapt_db
from app.routers import customers, plan


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_db_and_tables()
    # boostrapt_db()
    yield

app = FastAPI(lifespan=lifespan)


app.include_router(customers.router)
app.include_router(plan.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
