from datetime import date, datetime
from sqlmodel import select
from app.models import Membership, CashSession


def expire_memberships(session):
    """
    Job 1: Expira membresías vencidas.
    """
    memberships = session.exec(
        select(Membership).where(Membership.status == True)).all()
    for m in memberships:
        if m.end_date and m.end_date < date.today():
            m.status = False
            session.add(m)
    session.commit()

# def check_open_cash(session):
#     """
#     Job 2: Revisa si hay una caja abierta y registra alerta/log.
#     """
#     open_cash = session.exec(select(CashSession).where(CashSession.closed_at == None)).all()
#     if open_cash:
#         print(f"[{datetime.now()}] Hay {len(open_cash)} caja(s) abierta(s).")
