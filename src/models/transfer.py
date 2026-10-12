from datetime import date as dt_date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.account import Account


class Transfer(BaseModel):
    """Модель перевода средств между счетами (включая обналичивание)"""
    __tablename__ = "transfers"

    from_account_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_account_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    to_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    date: Mapped[dt_date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    from_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[from_account_id],
        back_populates="transfers_from",
    )
    to_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[to_account_id],
        back_populates="transfers_to",
    )
