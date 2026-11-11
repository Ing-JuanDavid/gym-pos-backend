from app.database import Session, SessionDep
from sqlmodel import select, desc
from app.models.fingerprint import Fingerprint
from app.utilities.exceptions import conflict
from app.schemes.fingerprint import FingerPrintCreate
from fastapi import Depends
from typing import Annotated
from sqlmodel import select


class FingerPrintService:
    def __init__(self, session: Session):
        self.session = session

    def create_fingerprint(self, fingerprint: FingerPrintCreate) -> Fingerprint:
        db_fingerprint = self.get_fingerprint(fingerprint.customer_id)

        if db_fingerprint:
            raise conflict("customer's print already enrolled")

        db_fingerprint = Fingerprint.model_validate(fingerprint)

        self.session.add(db_fingerprint)
        self.session.commit()
        self.session.refresh(db_fingerprint)
        return db_fingerprint

    def get_fingerprint(self, customer_id: int) -> Fingerprint | None:
        statement = select(Fingerprint).where(
            Fingerprint.customer_id == customer_id)
        return self.session.exec(statement).first()

    def get_fingerprint_id(self) -> int:
        statement = select(Fingerprint.print_id).order_by(
            desc(Fingerprint.print_id)).limit(1)

        fingerprint_id = self.session.exec(statement).first()

        if fingerprint_id is None:
            return 1

        if fingerprint_id == 300:
            raise conflict("prints full")

        return fingerprint_id + 1

    def get_fingerprint_by_print_id(
        self,
        print_id: int,
    ) -> Fingerprint | None:

        statement = (
            select(Fingerprint)
            .where(
                Fingerprint.print_id == print_id
            )
        )

        return self.session.exec(
            statement
        ).first()

    def delete_fingerprint(self, fingerprint: Fingerprint) -> None:
        self.session.delete(fingerprint)
        self.session.commit()


def get_fingerprint_service(session: SessionDep):
    return FingerPrintService(session=session)


FingerPrintServiceDep = Annotated[FingerPrintService, Depends(
    get_fingerprint_service)]
