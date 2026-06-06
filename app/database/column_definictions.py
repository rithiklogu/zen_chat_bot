
from sqlmodel import Field
from app.database.mixins import BaseMixin, TimestampMixin, UUIDMixin
from pydantic import EmailStr

class User_cols(TimestampMixin, BaseMixin, UUIDMixin):
    user_name:str
    user_email:EmailStr
    Field(
    unique=True,
    index=True
)
    user_contact: str = Field(
        min_length=10,
        max_length=15
    )

