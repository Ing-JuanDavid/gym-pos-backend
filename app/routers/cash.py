from fastapi import APIRouter, HTTPException
from typing import List
from app.models.cash import CashSession
from app.services.cash import CashSessionServiceDep
from app.services.cash_movement import CashMovementServiceDep, CashMovement

router = APIRouter(prefix="/cash", tags=["cash"])


# Abrir sesión de caja
@router.post("/", response_model=CashSession)
def open_cash_session(
    service: CashSessionServiceDep,
    opening_balance: int = 0
):
    return service.open(opening_balance)


# Obtener la sesión actual (del día)
@router.get("/current", response_model=CashSession)
def get_current_cash_session(
    service: CashSessionServiceDep
):
    db_session = service.get_current_cash()
    if not db_session:
        raise HTTPException(
            status_code=404, detail="No cash session opened today")
    return db_session


# Obtener sesión por ID
@router.get("/{session_id}", response_model=CashSession)
def get_cash_session(
    session_id: int,
    service: CashSessionServiceDep
):
    db_session = service.get(session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Cash session not found")
    return db_session

# Listar todas las sesiones


@router.get("/", response_model=List[CashSession])
def list_cash_sessions(
    service: CashSessionServiceDep
):
    return service.read_all()


@router.get("/{session_id}/movements", response_model=List[CashMovement])
def list_cash_movements(
    session_id: int,
    service: CashMovementServiceDep
):
    return service.read_movement_by_cash(session_id)


# Cerrar sesión de caja
@router.post("/{session_id}/close", response_model=CashSession)
def close_cash_session(
    session_id: int,
    closing_balance: int,
    service: CashSessionServiceDep
):
    db_session = service.close(session_id, closing_balance)
    if not db_session:
        raise HTTPException(status_code=404, detail="Cash session not found")
    return db_session


# Eliminar sesión de caja
@router.delete("/{session_id}")
def delete_cash_session(
    session_id: int,
    service: CashSessionServiceDep
):
    success = service.delete(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cash session not found")
    return {"ok": True}
