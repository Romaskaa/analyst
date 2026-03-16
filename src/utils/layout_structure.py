import re
from enum import StrEnum

from bs4 import BeautifulSoup
from pydantic import BaseModel

OPTIMAL_TITLE_LENGTH = 55
OPTIMAL_TITLE_DELTA = 10
MAX_DESCRIPTION_LENGTH = 160
MIN_DESCRIPTION_LENGTH = 120
SEMANTIC_TAGS = {"header", "nav", "main", "article", "section", "aside", "footer"}


class IssueLevel(StrEnum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Issue(BaseModel):
    level: IssueLevel
    message: str
    category: str
    element: str


def validate_title(soup: BeautifulSoup) -> list[Issue]:
    title_tag = soup.find("title")
    if title_tag.text is None:  # type: ignore  # noqa: PGH003
        return [
            Issue(
                level=IssueLevel.CRITICAL,
                message="Title tag is missing",
                category="meta",
                element="title",
            )
        ]
    title = title_tag.get_text().strip()  # type: ignore  # noqa: PGH003
    if not title:
        return [
            Issue(
                level=IssueLevel.CRITICAL,
                message="Title tag is empty",
                category="meta",
                element="title",
            )
        ]
    if len(title) < OPTIMAL_TITLE_LENGTH - OPTIMAL_TITLE_DELTA:
        return [
            Issue(
                level=IssueLevel.WARNING,
                message=f"""Title is too short ({len(title)} characters)!
            Optimal length must be from {OPTIMAL_TITLE_LENGTH - OPTIMAL_TITLE_DELTA}
            to {OPTIMAL_TITLE_LENGTH + OPTIMAL_TITLE_DELTA}.""",
                category="meta",
                element="title",
            )
        ]
    if len(title) > OPTIMAL_TITLE_LENGTH + OPTIMAL_TITLE_DELTA:
        return [
            Issue(
                level=IssueLevel.WARNING,
                message=f"""Title is too long ({len(title)} characters)!
            Optimal length must be from {OPTIMAL_TITLE_LENGTH - OPTIMAL_TITLE_DELTA}
            to {OPTIMAL_TITLE_LENGTH + OPTIMAL_TITLE_DELTA}.""",
                category="meta",
                element="title",
            )
        ]
    return []


def validate_description(soup: BeautifulSoup) -> list[Issue]:
    description_element = soup.find("meta", attrs={"name": "description"})
    if not description_element:
        return [
            Issue(
                level=IssueLevel.CRITICAL,
                message="Meta description is missing",
                category="meta",
                element="description",
            )
        ]
    description = description_element.get("content", "").strip()  # type: ignore  # noqa: PGH003
    if not description:
        return [
            Issue(
                level=IssueLevel.CRITICAL,
                message="Meta description is empty",
                category="meta",
                element="description",
            )
        ]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return [
            Issue(
                level=IssueLevel.WARNING,
                message=f"Meta description too long ({len(description)} characters)! "
                f"Recommended length should be from {MIN_DESCRIPTION_LENGTH} "
                f"to {MAX_DESCRIPTION_LENGTH} characters.",
                category="meta",
                element="description",
            )
        ]
    if len(description) < MIN_DESCRIPTION_LENGTH:
        return [
            Issue(
                level=IssueLevel.WARNING,
                message=f"Meta description too short ({len(description)} characters)! "
                f"Recommended length should be from {MIN_DESCRIPTION_LENGTH} "
                f"to {MAX_DESCRIPTION_LENGTH} characters.",
                category="meta",
                element="description",
            )
        ]
    return []


def validate_heading(soup: BeautifulSoup) -> list[Issue]:
    issues = []
    h1_tags = soup.find_all("h1")
    if len(h1_tags) == 0:
        issues.append(
            Issue(
                level=IssueLevel.CRITICAL,
                message="H1 tag is missing",
                category="heading",
                element="h1",
            )
        )
    elif len(h1_tags) > 1:
        issues.append(
            Issue(
                level=IssueLevel.WARNING,
                message=f"Found {len(h1_tags)} H1 tags. Only one H1 per page is recommended",
                category="heading",
                element="h1",
            )
        )
    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    last_level = 0
    for heading in headings:
        level = int(heading.name[1])
        if level > last_level + 1:
            issues.append(
                Issue(
                    level=IssueLevel.WARNING,
                    message=f"The heading hierarchy is broken: H{level} after H{last_level}",
                    category="heading",
                    element=heading.name,
                )
            )
        last_level = level
    return issues


def validate_semantic_tags(soup: BeautifulSoup) -> list[Issue]:
    issues = []
    used_semantic_tags = []
    unused_semantic_tags = []
    for semantic_tag in SEMANTIC_TAGS:
        elements = soup.find_all(semantic_tag)
        if not elements:
            unused_semantic_tags.append(semantic_tag)
        else:
            used_semantic_tags.append(semantic_tag)
    if unused_semantic_tags:
        issues.append(
            Issue(
                level=IssueLevel.INFO,
                message=f"Unused semantic tags: {', '.join(unused_semantic_tags)}",
                category="semantic tags",
                element=";".join(unused_semantic_tags),
            )
        )
    if used_semantic_tags:
        issues.append(
            Issue(
                level=IssueLevel.INFO,
                message=f"Used semantic tags: {', '.join(used_semantic_tags)}",
                category="semantic tags",
                element=";".join(used_semantic_tags),
            )
        )
    return issues


def validate_images(soup: BeautifulSoup) -> list[Issue]:
    """Проверка SEO оптимизации изображений"""

    issues: list[Issue] = []
    images = soup.find_all("img")
    if not images:
        return [
            Issue(
                level=IssueLevel.INFO,
                message="Images not found in page",
                category="image",
                element="img",
            )
        ]
    images_with_alt = 0  # Количество изображений с описанием
    images_without_alt = 0  # Количество изображений без атрибута alt
    images_without_description = 0  # Изображения без описания в названии файла

    for image in images:
        alt, src = image.get("alt", ""), image.get("src", "")
        if not alt:
            images_without_alt += 1
        else:
            images_with_alt += 1
        if (src and any(type in src.lower() for type in ["image", "img", "picture"])) and not any(  # noqa: A001, PGH003, RUF100
            extension in src.lower()  # type: ignore  # noqa: PGH003
            for extension in [".jpg", ".jpeg", ".png", ".webp"]  # type: ignore  # noqa: PGH003
        ):
            images_without_description += 1
    # Добавляем один лог для изображений без alt
    if images_without_alt > 0:
        issues.append(
            Issue(
                level=IssueLevel.WARNING,
                message=f"Found {images_without_alt} images without 'alt' attribute",
                category="image",
                element="img",
            )
        )

    # Добавляем лог для изображений с alt (опционально, для информации)
    if images_with_alt > 0:
        issues.append(
            Issue(
                level=IssueLevel.INFO,
                message=f"Found {images_with_alt} images with 'alt' attribute",
                category="image",
                element="img",
            )
        )

    if images_without_description > 0:
        issues.append(
            Issue(
                level=IssueLevel.WARNING,
                message=f"Missing description in image files {images_without_description}!",
                category="image",
                element="img",
            )
        )

    return issues


def find_seo_issues(soup: BeautifulSoup) -> list[Issue]:
    """Нахождение замечаний касаемо SEO оптимизации разметки страницы"""

    return [
        *validate_title(soup),
        *validate_description(soup),
        *validate_heading(soup),
        *validate_images(soup),
        *validate_semantic_tags(soup),
    ]
