
from typing import Annotated
from fastapi import Depends
from sqlmodel import create_engine, SQLModel, Session
import app.models
from app.config import settings


# engine creation
engine = create_engine(settings.database_url, echo=True)


# create tables.
# creates all of thouses wich have 'table = true'
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def init_data(session: Session):

    # menues
    customer = Customer(
        first_name='Juan David',
        last_name='Salgado Romero',
        nuip=106455658,
        phone='3023685456',
        sex='M'
    )
    session.add(customer)
    session.commit()


def boostrapt_db():
    with Session(engine) as session:
        init_data(session)
