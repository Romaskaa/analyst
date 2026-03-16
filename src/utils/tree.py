"""Модуль для построения дерева структуры сайта"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator
from usp.objects.page import SitemapPage
from usp.tree import sitemap_tree_for_homepage

PRIORITY_KEYWORDS: tuple[str, ...] = (
    "product",
    "services",
    "catalog",
    "category",
    "shop",
    "blog",
    "article",
    "news",
    "post",
    "about",
    "contact",
    "price",
    "buy",
    "order",
    "cases",
)
# Запрещённые endpoints
DENIED_EXTENSIONS: tuple[str, ...] = (
    ".php",
    ".asp",
    ".aspx",
    ".jsp",
    ".cgi",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".rar",
    ".tar",
    ".gz",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".svg",
    ".webp",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".mp3",
    ".wav",
    ".ogg",
    ".css",
    ".js",
    ".json",
    ".xml",
)


def parse_url_path(url: str) -> list[str]:
    """Разбивает URL на части.

    Пример: "http://site.com/folder/page" -> ["folder", "page"]
    """
    path = urlparse(url).path
    return [segment for segment in path.strip("/").split("/") if segment]


class TreeNode(BaseModel):
    """Узел дерева структуры страниц сайта"""

    name: str
    url: HttpUrl
    priority: float | None = None
    last_modified: datetime | None = None
    children: list[TreeNode] = Field(default_factory=list)

    @field_validator("last_modified", mode="before")
    @classmethod
    def validate_last_modified(cls, value: str | None) -> datetime | None:
        if not value or value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                return None
        return value

    @property
    def sections(self) -> list[str]:
        """Секции внутри которых находится страница"""
        url = str(self.url)
        domain = urlparse(url).netloc
        url = url.replace(domain, "").replace("http://", "").replace("https://", "")
        return url.split("/")

    @property
    def is_leaf(self) -> bool:
        """Является ли узел листом"""
        return len(self.children) == 0

    def max_depth(self) -> int:
        """Максимальная глубина дерева"""
        if not self.children:
            return 0
        return max(child.max_depth() for child in self.children) + 1

    def count_nodes(self) -> int:
        """Подсчитывает общее количество узлов в дереве"""
        count = 1
        for child in self.children:
            count += child.count_nodes()
        return count

    def iter_nodes(self) -> Iterator[TreeNode]:
        """Итерация по всем узлам дерева"""
        yield self
        for child in self.children:
            yield from child.iter_nodes()

    def iter_leaves(self) -> Iterator[TreeNode]:
        """Итерация по листьям дерева"""
        for node in self.iter_nodes():
            if node.is_leaf:
                yield node

    def find_node(self, url: str) -> TreeNode | None:
        """Рекурсивный поиск страницы по её URL"""
        if self.url == url:
            return self
        for child in self.children:
            found = child.find_node(url)
            if found:
                return found
        return None

    def to_string(self, max_depth: int | None = None) -> str:
        """Представление дерева в человеко-читаемом формате"""
        lines: list[str] = []
        self.draw_tree_lines(lines, max_depth=max_depth)
        return "\n".join(lines)

    def draw_tree_lines(
        self,
        lines: list[str],
        max_depth: int | None = None,
        current_depth: int = 0,
        prefix: str = "",
        is_last: bool = True,
    ) -> None:
        """Формирует строковое представление для отображения дерева"""
        if max_depth is not None and current_depth >= max_depth:
            return
        meta_parts: list[str] = []
        if self.priority is not None:
            meta_parts.append(f"Приоритет: {self.priority}")
        if self.last_modified:
            meta_parts.append(f"Последнее изменение: {self.last_modified.strftime('%d.%m.%Y')}")
        meta_str = " [" + ", ".join(meta_parts) + "]" if meta_parts else ""
        if current_depth == 0:
            icon = "🌐"
            line = f"{icon} {self.name} ({self.url}){meta_str}"
            lines.append(line)
        else:
            icon = "📄" if self.is_leaf else "📁"
            connector = "└── " if is_last else "├── "
            line = f"{prefix}{connector}{icon} {self.name}{meta_str}"
            lines.append(line)
        new_prefix = prefix if current_depth == 0 else prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(self.children):
            is_last_child = i == len(self.children) - 1
            child.draw_tree_lines(lines, max_depth, current_depth + 1, new_prefix, is_last_child)

    def last_site_change(self) -> datetime | None:
        """Последнее изменение на сайте"""
        latest = self.last_modified
        for node in self.iter_nodes():
            if node.last_modified and (latest is None or node.last_modified > latest):
                latest = node.last_modified
        return latest

    def last_changed_node(self) -> TreeNode | None:
        """Последняя изменённая страница"""
        nodes: list[TreeNode] = [
            node for node in self.iter_nodes() if node.last_modified is not None
        ]
        return max(nodes, key=lambda x: x.last_modified, default=None)  # type: ignore  # noqa: PGH003

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TreeNode):
            return False
        return self.url == other.url


def add_page_to_tree(
    base_url: HttpUrl,
    root: TreeNode,
    page: SitemapPage,
    segments: list[str],
    current_depth: int = 0,
) -> None:
    if current_depth >= len(segments):
        return
    current_segment = segments[current_depth]
    node: TreeNode | None = next(
        (child for child in root.children if child.name == current_segment), None
    )
    if node is None:
        path_part = "/".join(segments[: current_depth + 1])
        full_url = f"{str(base_url).rstrip('/')}/{path_part}"
        node = TreeNode.model_validate({
            "name": current_segment,
            "url": full_url,
            "priority": page.priority,
            "last_modified": page.last_modified,
        })
        root.children.append(node)
    add_page_to_tree(base_url, node, page, segments, current_depth + 1)


def build_site_tree(url: HttpUrl) -> TreeNode:
    """Рекурсивно строит дерево сайта по страницам из sitemap.xml.

    :param url: URL адрес сайта.
    :return Построенное дерево структуры сайта.
    """
    name = str(url).replace("http://", "").replace("https://", "").replace("/", "")
    root = TreeNode(name=name, url=url)
    sitemap = sitemap_tree_for_homepage(str(url), use_robots=False)
    for page in sitemap.all_pages():
        segments = parse_url_path(page.url)
        add_page_to_tree(url, root, page, segments)
    return root


def _get_path_segments(url: HttpUrl) -> list[str]:
    """Получение сегментов URL адреса,
    пример: 'http://example.ru/services/3' -> ['services', '3']

    :param url: Адрес страницы для разбиения.
    :return Секции на странице.
    """
    parsed = urlparse(str(url))
    return [section for section in parsed.path.strip("/").split("/") if section]


def _sort_by_last_modified(nodes: list[TreeNode]) -> list[TreeNode]:
    """Сортировка по последней дате изменений"""
    with_dates: list[TreeNode] = []
    without_dates: list[TreeNode] = []
    for node in nodes:
        if node.last_modified is None:
            without_dates.append(node)
        else:
            with_dates.append(node)
    with_dates.sort(key=lambda node: node.last_modified, reverse=True)  # type: ignore  # noqa: PGH003
    return with_dates + without_dates


def _is_denied_url(url: HttpUrl) -> bool:
    """Проверка URL на запрещённый, True если запрещён, False если разрешён"""
    return not any(
        str(url).split(".")[-1].lower().endswith(extension) for extension in DENIED_EXTENSIONS
    )


def _get_node_sort_key(node: TreeNode) -> tuple[float, float, float]:
    """Сортировка узлов
    - Высокий приоритет из sitemap.xml (если есть)
    - Дата изменения (сначала новые)
    - Глубина узла (малая глубина сначала)
    """
    priority_score = node.priority if node.priority is not None else 0.5
    date_score = node.last_modified.timestamp() if node.last_modified else 0
    depth_penalty = len(_get_path_segments(node.url)) * 0.01
    return -priority_score, -date_score, depth_penalty


def extract_key_pages(  # noqa: C901
    tree: TreeNode, key_segments: list[str], max_result: int = 15
) -> list[HttpUrl]:
    """Извлекает URL ключевых страниц сайта.

    :param tree: Дерево сайта.
    :param key_segments: Ключевые секции сайта которые нужно посетить.
    :param max_result: Максимальное количество извлекаемых страниц.
    :return Уникальные ключевые URL адреса сайта.
    """
    key_pages: set[HttpUrl] = {tree.url}  # Добавление главной страницы сайта
    nodes_with_key_segments: list[TreeNode] = []  # Узлы содержащие ключевые сегменты
    used_segments: set[str] = set()  # Использованные сегменты для избежания двойной обработки
    # Добавление последней изменённой страницы
    last_changed_node = tree.last_changed_node()
    if last_changed_node is not None:
        key_pages.add(last_changed_node.url)
    for node in tree.iter_nodes():
        if len(key_pages) > max_result:
            break
        segments = _get_path_segments(node.url)
        # Проверка наличия ключевых сегментов в пути
        has_key_segment = any(key_segment in segments for key_segment in key_segments)
        if has_key_segment and _is_denied_url(node.url):
            nodes_with_key_segments.append(node)
    nodes_with_key_segments.sort(key=_get_node_sort_key)
    for node_with_key_segment in nodes_with_key_segments:
        if len(key_pages) >= max_result:
            break
        segments = _get_path_segments(node_with_key_segment.url)
        # Нахождение ключевого сегмента в узле
        found_key_segment = next(
            (key_segment for key_segment in key_segments if key_segment in segments), None
        )
        if found_key_segment is not None and found_key_segment not in used_segments:
            key_pages.add(node_with_key_segment.url)
            used_segments.add(found_key_segment)
            # Добавление свежих дочерних страниц из текущей директории
            if not node_with_key_segment.is_leaf:
                children = _sort_by_last_modified(node_with_key_segment.children)
                for child in children:
                    if len(key_pages) < max_result and _is_denied_url(child.url):
                        key_pages.add(child.url)
    # Если не набрано достаточное количество страниц, то добавляются популярные листья
    if len(key_pages) < max_result:
        leaves = list(tree.iter_leaves())
        leaves.sort(key=_get_node_sort_key)
        key_pages.update(leaf.url for leaf in leaves[: max_result - len(key_pages)])
    return list(key_pages)
