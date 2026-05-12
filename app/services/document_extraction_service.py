from io import BytesIO

from docx import Document as DocxDocument
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def get_file_extension(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower()


def extract_text_from_upload(filename: str, file_bytes: bytes) -> str:
    """
    Extract text from a supported uploaded document.
    """
    extension = get_file_extension(filename)

    if extension == ".txt":
        return extract_text_from_txt(file_bytes)

    if extension == ".pdf":
        return extract_text_from_pdf(file_bytes)

    if extension == ".docx":
        return extract_text_from_docx(file_bytes)

    supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    raise ValueError(f"Unsupported file type. Please upload one of: {supported}.")


def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(page.strip() for page in pages if page.strip())


def extract_text_from_docx(file_bytes: bytes) -> str:
    document = DocxDocument(BytesIO(file_bytes))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
