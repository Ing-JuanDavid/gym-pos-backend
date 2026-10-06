from sqlmodel import SQLModel, Field, table
from datetime import date


class Customer(SQLModel, table=True):
    customer_id: int | None = Field(default=None, primary_key=True)
    nuip: int = Field(unique=True)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    phone: str = Field(max_length=15)
    email: str = Field(max_length=70, default='')
    sex: str = Field(max_length=1, default='N')
    birth: date | None = Field(default=None)
