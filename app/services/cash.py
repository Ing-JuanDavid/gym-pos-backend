from app.database import Session, SessionDep
from sqlmodel import select, or_, between
from typing import List, Optional
from app.models.cash import CashSession
from datetime import datetime, time
from fastapi import Depends
from typing import Annotated
from app.utilities.exceptions import conflict, not_found


class CashSessionService:
    def __init__(self, session: Session):
        self.session = session

    # Crear sesión de caja
    def open(self, opening_balance: int = 0) -> CashSession:

        current_cash = self.get_current_cash()

        if current_cash:
            raise conflict(
                f"cash with id: {current_cash.session_id} alerady opened")

        session = CashSession(opening_balance=opening_balance)
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    # Obtener por ID
    def get(self, session_id: int) -> Optional[CashSession]:
        return self.session.get(CashSession, session_id)

    def get_current_cash(self) -> Optional[CashSession]:
        today = datetime.now().date()
        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)

        statement = (
            select(CashSession)
            .where(
                or_(
                    (
                        CashSession.opened_at >= start_of_day) & (
                        CashSession.opened_at <= end_of_day),
                    CashSession.closed_at == None
                )
            )
        )
        return self.session.exec(statement).first()

    # Listar todas las sesiones
    def read_all(self) -> List[CashSession]:
        statement = select(CashSession)
        return self.session.exec(statement).all()

    # Cerrar sesión de caja
    def close(self, session_id: int, closing_balance: int) -> Optional[CashSession]:
        session = self.get(session_id)
        if not session:
            raise not_found("session")

        if session.closed_at != None:
            raise conflict("cash alerady closed")
        session.closing_balance = closing_balance
        session.closed_at = datetime.now()
        session.total_balance = sum(m.amount for m in session.movements)
        session.difference = session.total_balance - session.closing_balance
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    # Eliminar sesión
    def delete(self, session_id: int) -> bool:
        session = self.get(session_id)
        if not session:
            return False
        self.session.delete(session)
        self.session.commit()
        return True


def get_cash_session_service(session: SessionDep) -> CashSessionService:
    return CashSessionService(session)


CashSessionServiceDep = Annotated[CashSessionService, Depends(
    get_cash_session_service)
]
