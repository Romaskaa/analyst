import logging
import mimetypes

from bs4 import BeautifulSoup
from langchain.messages import AIMessage

from ...core.depends import (
    yandex_gpt,
)
from ...utils.layout_structure import find_seo_issues

logger = logging.getLogger(__name__)


async def get_mime(url: str, data: bytes) -> str:
    """Определяет MIME-тип изображения по URL и содержимому."""
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type:
        return mime_type

    # Проверка сигнатур
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    # Неизвестный тип
    raise ValueError(f"Не удалось определить MIME-тип для {url}")


async def count_tokens_with_ai_message(request: str, result: AIMessage) -> int:
    count_request = yandex_gpt.get_num_tokens(request)
    count_result = yandex_gpt.get_num_tokens(str(result.content))
    return count_request + count_result


async def count_tokens(request: str, result: str) -> int:
    count_request = yandex_gpt.get_num_tokens(request)
    count_result = yandex_gpt.get_num_tokens(result)
    return count_request + count_result


async def get_seo_issues(html: str) -> list:
    bs = BeautifulSoup(html, "html.parser")
    issue = find_seo_issues(bs)
    return [i.model_dump() for i in issue]


ab_queries = [
    "1с комплексная автоматизация цена",
    "сопровождение 1с архитектор бизнеса",
    "1с:зарплата и управление персоналом",
    "обучение 1с архитектор бизнеса",
    "1с",
    "архитектор бизнеса",
    "1с управление небольшой фирмой",
    "1с бухгалтерия архитектор",
    "внедрение 1с архитектор",
    "1с строительство архитектор",
    "обновление 1с архитектор бизнеса",
    "1с архитектор бизнеса",
    "1с камин архитектор",
    "1с документооборот архитектор",
    "купить 1с у архитектора",
    "отзывы архитектор бизнеса",
    "переход на 1с с архитектором",
    "1с отчетность архитектор",
]

one_bit_queries = [
    "1с документооборот первый бит",
    "внедрение 1с первый бит",
    "обновление 1с первый бит",
    "отзывы о первом бите",
    "1с первый бит",
    "цена 1с бухгалтерия базовая",
    "1с бухгалтерия цена",
    "переход на 1с с первого бита",
    "первый бит",
    "1с отчетность первый бит",
    "аренда 1с в облаке первый бит",
    "купить 1с в первом бите",
    "1с управление торговлей",
    "1с комплексная автоматизация первый бит",
    "курсы 1с первый бит",
    "1с",
    "1с:предприятие",
    "обслуживание 1с первый бит",
]
