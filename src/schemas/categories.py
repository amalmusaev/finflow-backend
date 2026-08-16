from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from src.schemas.enums import OperationType


class CategoryBase(BaseModel):
    """Базовая схема категории"""
    name: str = Field(..., min_length=1, max_length=128, description="Название категории")
    type: OperationType = Field(..., description="Тип категории (расход/доход)")


class CategoryCreate(CategoryBase):
    """Схема для создания категории"""
    pass


class CategoryResponse(CategoryBase):
    """Схема для ответа с категорией"""
    id: UUID = Field(..., description="ID категории")

    model_config = ConfigDict(from_attributes=True)


class CategoryUpdate(BaseModel):
    """Схема для обновления категории"""
    name: str | None = Field(default=None, min_length=1, max_length=128, description="Название категории")
    type: OperationType | None = Field(default=None, description="Тип категории")


class CategoryListResponse(BaseModel):
    """Схема для ответа со списком категорий"""
    categories: list[CategoryResponse] = Field(..., description="Список категорий")

