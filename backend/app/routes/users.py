from fastapi import APIRouter

from app.schemas.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[User])
def list_users() -> list[User]:
    return []