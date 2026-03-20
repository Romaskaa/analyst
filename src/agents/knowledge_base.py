from __future__ import annotations

from pathlib import Path

import docx
import pandas as pd
import pytesseract
from fastapi import UploadFile
from PIL import Image
from pypdf import PdfReader
from pptx import Presentation

UPLOAD_DIR = Path("storage/uploads")

def save_file(file: UploadFile) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / (file.filename or "uploaded_file")

    with path.open("wb") as f:
        f.write(file.file.read())

    return str(path)


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf(path: Path) -> str:
    text: list[str] = []
    reader = PdfReader(path)

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return "\n".join(text)


def read_docx(path: Path) -> str:
    document = docx.Document(path)
    text: list[str] = []

    for paragraph in document.paragraphs:
        text.append(paragraph.text)

    return "\n".join(text)


def read_pptx(path: Path) -> str:
    prs = Presentation(path)
    text: list[str] = []

    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)

    return "\n".join(text)


def read_xlsx(path: Path) -> str:
    df = pd.read_excel(path)
    return df.to_string()


def read_image(path: Path) -> str:
    img = Image.open(path)
    return pytesseract.image_to_string(img)


def extract_text_from_file(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")

    try:
        if ext == "txt":
            return read_txt(path)
        if ext == "pdf":
            return read_pdf(path)
        if ext == "docx":
            return read_docx(path)
        if ext == "pptx":
            return read_pptx(path)
        if ext in {"xls", "xlsx"}:
            return read_xlsx(path)
        if ext in {"png", "jpg", "jpeg"}:
            return read_image(path)
        return ""
    except Exception as exc:
        print("Ошибка чтения файла:", path, exc)
        return ""


def load_knowledge_base() -> str:
    texts: list[str] = []

    if not UPLOAD_DIR.exists():
        return ""

    for path in UPLOAD_DIR.iterdir():
        if path.is_file():
            text = extract_text_from_file(path)
            if text:
                texts.append(text)

    return "\n\n".join(texts)

def list_uploaded_files() -> list[dict[str, str]]:
    if not UPLOAD_DIR.exists():
        return []

    files: list[dict[str, str]] = []
    for path in sorted(UPLOAD_DIR.iterdir()):
        if path.is_file():
            files.append({"name": path.name, "path": str(path)})

    return files

def load_knowledge_base_documents() -> list[tuple[str, str]]:
    documents: list[tuple[str, str]] = []

    if not UPLOAD_DIR.exists():
        return documents

    for path in UPLOAD_DIR.iterdir():
        if path.is_file():
            text = extract_text_from_file(path)
            if text:
                documents.append((path.name, text))

    return documents