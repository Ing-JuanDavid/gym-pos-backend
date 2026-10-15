from sqlmodel import SQLModel, table, Field


class Product(SQLModel, table=True):
    product_id: int | None = Field(default=None, primary_key=True)
    name: str
    price: int
    stock: int = 0
