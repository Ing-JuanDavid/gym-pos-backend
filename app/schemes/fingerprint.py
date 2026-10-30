from pydantic import BaseModel


class FingerPrintCreate(BaseModel):

    print_id: int
    customer_id: int
