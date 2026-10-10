from fastapi import APIRouter, Depends
from app.database import get_session
from app.services.membership import MembershipService, MembershipServiceDep
from app.schemes.membership import MembershipCreate, MembershipUpdate, MembershipPublic
from app.utilities.exceptions import not_found

router = APIRouter(prefix="/memberships", tags=["memberships"])

# CREATE


@router.post("", response_model=MembershipPublic)
def create_membership(
    membership: MembershipCreate,
    service: MembershipServiceDep
):
    return service.create_membership(membership)

# READ (por id)


@router.get("/{membership_id}", response_model=MembershipPublic)
def get_membership(
    membership_id: int,
    service: MembershipServiceDep
):

    db_membership = service.get_membership(membership_id)

    if not db_membership:
        raise not_found("membership")

    return db_membership

# READ (por nuip del cliente)


@router.get("/customer/{nuip}", response_model=MembershipPublic | None)
def get_customer_membership(
    nuip: int,
    service: MembershipServiceDep
):
    return service.get_customer_membership(nuip)

# READ (todos)


@router.get("/", response_model=list[MembershipPublic])
def list_memberships(
    service: MembershipServiceDep
):
    return service.list_memberships()

# UPDATE


@router.put("/{membership_id}", response_model=MembershipPublic)
def update_membership(
    membership_id: int,
    membership: MembershipUpdate,
    service: MembershipServiceDep
):
    return service.update_membership(membership_id, membership)

# DELETE


@router.delete("/{membership_id}", response_model=dict[str, str])
def delete_membership(
    membership_id: int,
    service: MembershipServiceDep
):

    if not service.delete_membership(membership_id):
        return {"mesage": "error"}

    return {"mesage": "ok"}
