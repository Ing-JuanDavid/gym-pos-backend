
from app.database import Session, SessionDep
from sqlmodel import select
from app.models.plan import Plan  # tu modelo SQLModel
from app.schemes.plan import PlanCreate, PlanPublic, PlanUpdate
from app.utilities.exceptions import not_found

from fastapi import Depends
from typing import Annotated


class PlanService:
    def __init__(self, session: Session):
        self.session = session

    # CREATE
    def create_plan(self, plan: PlanCreate) -> PlanPublic:
        db_plan = Plan.model_validate(plan)
        self.session.add(db_plan)
        self.session.commit()
        self.session.refresh(db_plan)
        return db_plan

    # READ (por id)
    def get_plan(self, plan_id: int) -> Plan | None:
        return self.session.get(Plan, plan_id)

    # READ (todos)
    def list_plans(self) -> list[PlanPublic]:
        statement = select(Plan)
        return list(self.session.exec(statement))

    # UPDATE
    def update_plan(self, plan_id: int, plan: PlanUpdate) -> PlanPublic | None:
        db_plan = self.get_plan(plan_id)

        if not db_plan:
            raise not_found("plan")
        plan_data = plan.model_dump(exclude_unset=True)

        db_plan.sqlmodel_update(plan_data)
        self.session.add(db_plan)
        self.session.commit()
        self.session.refresh(db_plan)
        return db_plan

    # DELETE
    def delete_plan(self, plan_id: int) -> bool:
        db_plan = self.get_plan(plan_id)
        if not db_plan:
            return False
        self.session.delete(db_plan)
        self.session.commit()
        return True


def get_plan_service(session: SessionDep):
    return PlanService(session=session)


PlanServiceDep = Annotated[PlanService, Depends(get_plan_service)]
