from typing import Annotated

from fastapi import Depends
from sqlmodel import select

# Ajusta estos imports a como los tengas en tus otros servicios
# (por ejemplo FingerPrintService): la dependencia de sesión y el modelo.
from app.database import SessionDep, Session                      # <-- ajustar
from app.models.customer_photo import CustomerPhoto      # <-- ajustar
from app.schemes.customer_photo import CustomerPhotoCreate  # <-- ajustar


class CustomerPhotoService:
    def __init__(self, session: Session):
        self.session = session

    def create_photo(self, data: CustomerPhotoCreate) -> CustomerPhoto:
        db_photo = CustomerPhoto.model_validate(data)
        self.session.add(db_photo)
        self.session.commit()
        self.session.refresh(db_photo)
        return db_photo

    def get_by_customer_id(self, customer_id: int) -> list[CustomerPhoto]:
        statement = (
            select(CustomerPhoto)
            .where(CustomerPhoto.customer_id == customer_id)
            .order_by(CustomerPhoto.captured_at.desc())
        )
        return self.session.exec(statement).all()


# Si tus otros servicios se inyectan con otro patrón
# (por ejemplo Depends(get_x_service)), usa el mismo aquí.


def get_customer_photo_service(session: SessionDep) -> CustomerPhotoService:
    return CustomerPhotoService(session)


CustomerPhotoServiceDep = Annotated[CustomerPhotoService, Depends(
    get_customer_photo_service)]
