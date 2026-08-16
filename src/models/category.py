from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.schemas.enums import OperationType

if TYPE_CHECKING:
    from src.models.operation import Operation


class Category(BaseModel):
    """Модель категории доходов/расходов"""
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    type: Mapped[OperationType] = mapped_column(
        Enum(OperationType, native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )

    operations: Mapped[list["Operation"]] = relationship(
        "Operation",
        back_populates="category",
        cascade="all, delete-orphan",
    )
