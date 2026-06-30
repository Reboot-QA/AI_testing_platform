from io import BytesIO
from typing import List, Tuple

ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".doc"}
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_TEXT_LENGTH = 15000


def validate_upload(filename: str, content: bytes) -> None:
    if not filename:
        raise ValueError("文件名不能为空")
    ext = _get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 .txt、.md、.docx 格式文档")
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("文件大小不能超过 5MB")
    if not content:
        raise ValueError("文件内容为空")


def extract_text_from_document(filename: str, content: bytes) -> Tuple[str, bool]:
    validate_upload(filename, content)
    ext = _get_extension(filename)
    if ext in {".txt", ".md"}:
        text = _decode_text(content)
    elif ext in {".docx", ".doc"}:
        text = _extract_docx_text(content)
    else:
        raise ValueError("不支持的文件格式")

    text = text.strip()
    if not text:
        raise ValueError("未能从文档中提取到文本内容")

    truncated = False
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]
        truncated = True
    return text, truncated


def split_document_chunks(text: str, chunk_size: int = 3500) -> List[str]:
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    if not paragraphs:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for paragraph in paragraphs:
        paragraph_len = len(paragraph) + 1
        if current and current_len + paragraph_len > chunk_size:
            chunks.append("\n".join(current))
            current = [paragraph]
            current_len = paragraph_len
        else:
            current.append(paragraph)
            current_len += paragraph_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def _get_extension(filename: str) -> str:
    dot_index = filename.rfind(".")
    if dot_index == -1:
        return ""
    return filename[dot_index:].lower()


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "gb2312"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _extract_docx_text(content: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("服务端未安装 docx 解析依赖，请上传 .txt 或 .md 文件") from exc

    document = Document(BytesIO(content))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)
