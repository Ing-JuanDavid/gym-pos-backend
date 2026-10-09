from fastapi import APIRouter, Path
from app.services.plan import PlanService, PlanServiceDep
from app.schemes.plan import PlanCreate, PlanUpdate, PlanPublic

router = APIRouter(prefix="/plans", tags=["plan"])


@router.get("", response_model=list[PlanPublic])
async def read_all(service: PlanServiceDep):
    return service.list_plans()


@router.post("", response_model=PlanPublic)
async def create_plan(service: PlanServiceDep, plan: PlanCreate):
    return service.create_plan(plan)


@router.patch("/{plan_id}", response_model=PlanUpdate)
async def update_plan(service: PlanServiceDep, customer: PlanUpdate, plan_id: int = Path(gt=0)):
    return service.update_plan(plan_id, customer)


@router.delete("/{plan_id}", response_model=dict[str, str])
async def delete_customer(service: PlanServiceDep, plan_id: int = Path(gt=0)):
    if service.delete_plan(plan_id):
        return {"messaje": "ok"}
    return {"message": "error"}
