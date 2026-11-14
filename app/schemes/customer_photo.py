from pydantic import BaseModel


class CustomerPhotoCreate(BaseModel):
    url: str
    customer_id: int
