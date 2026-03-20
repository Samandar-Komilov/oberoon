from typing import Annotated

from oberoon import Model, Field, Request, Router


class CreateUser(Model):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: str
    age: Annotated[int, Field(ge=0, le=150)] = 0


class UserResponse(Model):
    id: int
    name: str
    email: str
    age: int


router = Router(prefix="/users")


@router.get("/{id}/")
async def get_user(request: Request, id: int) -> UserResponse:
    return UserResponse(id=id, name="Alice", email="alice@example.com", age=30)


@router.post("/")
async def create_user(request: Request, body: CreateUser) -> UserResponse:
    return UserResponse(id=1, name=body.name, email=body.email, age=body.age)
