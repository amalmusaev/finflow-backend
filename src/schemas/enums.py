from enum import StrEnum

class OperationType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    BYN = "BYN"
    KZT = "KZT"
    CNY = "CNY"


class AccountType(StrEnum):
    CASH = "cash"
    CARD = "card"
    BANK = "bank"
    DEPOSIT = "deposit"