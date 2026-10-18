from pydantic import BaseModel, Field
from app.models.cash_movement import PaymentMethod, MovementType


# class CashMovementCreate(BaseModel):
#     amount: int = Field(gt=0)
#     payment_type: PaymentMethod
#     movement_type: MovementType
#     session_id: int = Field(gt=0)
