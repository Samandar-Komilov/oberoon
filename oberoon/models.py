import msgspec
import msgspec.structs


class Model(msgspec.Struct):
    """Base model for request/response schemas.

    A friendly wrapper around msgspec.Struct with convenience methods.

    Usage::

        from oberoon import Model, Field
        from typing import Annotated

        class CreateUser(Model):
            name: Annotated[str, Field(min_length=1, max_length=100)]
            email: str
            age: Annotated[int, Field(ge=0, le=150)] = 0

    Use ``Annotated[type, Field(...)]`` for constraints (min_length, max_length,
    ge, le, gt, lt, pattern, title, description).
    """

    def to_dict(self) -> dict:
        """Convert this model instance to a plain dictionary."""
        return msgspec.structs.asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create a validated model instance from a dictionary."""
        return msgspec.convert(data, cls)
