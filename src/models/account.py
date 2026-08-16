from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel
from src.schemas.enums import AccountType, Currency

if TYPE_CHECKING:
    from src.models.operation import Operation


class Account(BaseModel):
    """Модель счета пользователя"""
    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        default=Currency.RUB,
        nullable=False,
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    operations: Mapped[list["Operation"]] = relationship(
        "Operation",
        back_populates="account",
        cascade="all, delete-orphan",
    )
