from app.database import Session, SessionDep
from sqlmodel import select
from app.models.cash_movement import CashMovement, MovementType
from app.models.payment import PaymentMethod
from typing import List, Optional, Annotated
from app.services.cash import CashSessionService, CashSessionServiceDep
from app.utilities.exceptions import conflict
from fastapi import Depends


class CashMovementService:
    def __init__(self, session: Session, cash_service: CashSessionService):
        self.session = session
        self.cash_service = cash_service

    # Crear movimiento
    def create_movement(self, amount: int, method: PaymentMethod, movement_type: MovementType) -> CashMovement:

        cash = self.cash_service.get_current_cash()

        if not cash:
            raise conflict("there's no cash opened")

        movement = CashMovement(
            amount=amount,
            payment_type=method,
            movement_type=movement_type,
            session_id=cash.session_id
        )

        self.session.add(movement)
        self.session.commit()
        self.session.refresh(movement)
        return movement

    # Obtener por ID
    def get(self, movement_id: int) -> Optional[CashMovement]:
        return self.session.get(CashMovement, movement_id)

    # Listar todos
    def read_all(self) -> List[CashMovement]:
        statement = select(CashMovement)
        return self.session.exec(statement).all()

    # Actualizar
    def update(self, movement_id: int, **kwargs) -> Optional[CashMovement]:
        movement = self.get(movement_id)
        if not movement:
            return None
        for key, value in kwargs.items():
            setattr(movement, key, value)
        self.session.add(movement)
        self.session.commit()
        self.session.refresh(movement)
        return movement

    # Eliminar
    def delete(self, movement_id: int) -> bool:
        movement = self.get(movement_id)
        if not movement:
            return False
        self.session.delete(movement)
        self.session.commit()
        return True

    def read_movement_by_cash(self, cash_id: int) -> list[CashMovement]:
        statement = select(CashMovement).where(
            CashMovement.session_id == cash_id)
        return self.session.exec(statement).all()


def get_cash_movement_Service(session: SessionDep, cash_Service: CashSessionServiceDep) -> CashMovementService:
    return CashMovementService(session, cash_Service)


CashMovementServiceDep = Annotated[CashMovementService, Depends(
    get_cash_movement_Service)]
