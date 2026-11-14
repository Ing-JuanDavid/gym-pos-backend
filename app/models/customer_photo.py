from datetime import datetime
from sqlalchemy import Column, DateTime

from sqlmodel import SQLModel, Field, Relationship


# ---------------------------------------------------------------
# MODELO (tabla). Colócalo junto a tu modelo Fingerprint.
# ---------------------------------------------------------------
class CustomerPhoto(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    url: str  # solo la URL relativa, p. ej. /media/captures/archivo.jpg
    captured_at: datetime | None = Field(
        default_factory=datetime.now, sa_column=Column(DateTime(timezone=False)))
    customer_id: int = Field(
        foreign_key="customer.customer_id", ondelete="CASCADE")

    customer: "Customer" = Relationship()
