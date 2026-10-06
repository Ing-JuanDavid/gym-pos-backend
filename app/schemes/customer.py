from pydantic import BaseModel, Field
from datetime import date


class CustomerCreate(BaseModel):
    nuip: int
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    phone: str = Field(max_length=15)
    email: str | None = Field(max_length=70, default='')
    sex: str | None = Field(max_length=1, default='N')
    birth: date | None = Field(default=None)


class CustomerUpdate(BaseModel):
    first_name: str | None = Field(max_length=50, default=None)
    last_name: str | None = Field(max_length=50, default=None)
    phone: str | None = Field(max_length=15, default=None)
    email: str | None = Field(max_length=70, default=None)
    sex: str | None = Field(max_length=1, default=None)
    birth: date | None = Field(default=None)


class CustomerPublic(CustomerCreate):
    customer_id: int
