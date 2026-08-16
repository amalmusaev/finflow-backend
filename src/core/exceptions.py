from uuid import UUID


class FinFlowError(Exception):
    """Базовое исключение приложения FinFlow"""
    pass


class EntityNotFoundError(FinFlowError):
    """Исключение: сущность не найдена"""

    def __init__(self, entity_name: str, entity_id: UUID | str) -> None:
        self.entity_name = entity_name
        self.entity_id = str(entity_id)
        super().__init__(f"{entity_name} с ID {self.entity_id} не найден(а)")


class AccountNotFoundError(EntityNotFoundError):
    def __init__(self, account_id: UUID | str) -> None:
        super().__init__("Счет", account_id)


class CategoryNotFoundError(EntityNotFoundError):
    def __init__(self, category_id: UUID | str) -> None:
        super().__init__("Категория", category_id)


class OperationNotFoundError(EntityNotFoundError):
    def __init__(self, operation_id: UUID | str) -> None:
        super().__init__("Операция", operation_id)


class ValidationError(FinFlowError):
    """Исключение бизнес-валидации"""
    pass
