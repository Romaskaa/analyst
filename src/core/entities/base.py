import abc
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ...utils.commons import current_datetime


class Entity(BaseModel, abc.ABC):
    """Базовая модель бизнес сущности, определяет базовые поля.
    Сущность - модель обладающая идентичностью.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
