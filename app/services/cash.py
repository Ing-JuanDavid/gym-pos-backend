from app.database import Session, SessionDep
from sqlmodel import select
from typing import List, Optional
from app.models.cash import CashSession
from datetime import datetime, time
from fastapi import Depends
from typing import Annotated


class CashSessionService:
    def __init__(self, session: Session):
        self.session = session

    # Crear sesión de caja
    def open(self, opening_balance: int = 0) -> CashSession:
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
                CashSession.opened_at >= start_of_day,
                CashSession.opened_at <= end_of_day
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
            return None
        session.closing_balance = closing_balance
        session.closed_at = datetime.now()
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
