from datetime import date as dt_date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.schemas.enums import OperationType

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.category import Category


class Operation(BaseModel):
    """Модель финансовой операции (доход/расход)"""
    __tablename__ = "operations"

    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    type: Mapped[OperationType] = mapped_column(
        Enum(OperationType, native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    date: Mapped[dt_date] = mapped_column(
        Date,
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="operations",
    )
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="operations",
    )
