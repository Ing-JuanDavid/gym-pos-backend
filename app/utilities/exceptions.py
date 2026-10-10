from fastapi import HTTPException, status


def not_found(entity: str):
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} not found"
    )


def invalid(entity: str):
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"{entity} invalid"
    )


def confict(msj: str):
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=msj
    )
