from io import BytesIO
from typing import List, Tuple

ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".doc"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def validate_upload(filename: str, content: bytes) -> None:
    if not filename:
        raise ValueError("文件名不能为空")
    ext = _get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 .txt、.md、.docx 格式文档")
    if len(content) >= MAX_FILE_SIZE:
        raise ValueError("文件大小不能超过 50MB")
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

    return text, False


def split_document_chunks(text: str, chunk_size: int = 5200) -> List[str]:
    """按段落聚合；单段超长时按字数硬切，避免整篇一次送 LLM。"""
    stripped = text.strip()
    if not stripped:
        return []

    paragraphs = [part.strip() for part in stripped.split("\n") if part.strip()]
    if not paragraphs:
        return [stripped[i : i + chunk_size] for i in range(0, len(stripped), chunk_size)]

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            flush()
            for i in range(0, len(paragraph), chunk_size):
                chunks.append(paragraph[i : i + chunk_size])
            continue
        paragraph_len = len(paragraph) + 1
        if current and current_len + paragraph_len > chunk_size:
            flush()
        current.append(paragraph)
        current_len += paragraph_len
    flush()
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
