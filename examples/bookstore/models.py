from typing import Annotated

from oberoon import BaseModel, Field


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: int
    genre: str
    rating: float
    available: bool


class CreateBook(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    author: Annotated[str, Field(min_length=1, max_length=100)]
    year: Annotated[int, Field(ge=1450, le=2030)]
    genre: Annotated[str, Field(min_length=1, max_length=50)]
    rating: Annotated[float, Field(ge=0.0, le=5.0)] = 0.0


class UpdateBook(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)] = ""
    author: Annotated[str, Field(min_length=1, max_length=100)] = ""
    year: Annotated[int, Field(ge=1450, le=2030)] = 0
    genre: Annotated[str, Field(min_length=1, max_length=50)] = ""
    rating: Annotated[float, Field(ge=0.0, le=5.0)] = -1.0


class Review(BaseModel):
    id: int
    book_id: int
    reviewer: str
    text: str
    stars: int


class CreateReview(BaseModel):
    reviewer: Annotated[str, Field(min_length=1, max_length=100)]
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    stars: Annotated[int, Field(ge=1, le=5)]
