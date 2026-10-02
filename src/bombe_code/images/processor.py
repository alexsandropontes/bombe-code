"""Processamento determinístico de imagens e serialização multimodal."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from pydantic import BaseModel

MIME_FALLBACK: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class ImageAttachment(BaseModel):
    """Anexo de imagem processado com codificação base64."""

    file_name: str
    file_path: str
    mime_type: str
    base64_data: str
    size_bytes: int


def process_image(file_path: str | Path, max_size_mb: float = 10.0) -> ImageAttachment:
    """Lê uma imagem local, valida formato e tamanho e converte para base64."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de imagem não encontrado: {path}")

    raw_bytes = path.read_bytes()
    size = len(raw_bytes)
    max_bytes = int(max_size_mb * 1024 * 1024)
    if size > max_bytes:
        raise ValueError(
            f"Imagem excede o limite de {max_size_mb}MB (tamanho: {size / (1024 * 1024):.1f}MB)"
        )

    ext = path.suffix.lower()
    mime, _ = mimetypes.guess_type(path.name)
    if not mime:
        mime = MIME_FALLBACK.get(ext, "image/png")

    encoded = base64.b64encode(raw_bytes).decode("ascii")

    return ImageAttachment(
        file_name=path.name,
        file_path=str(path),
        mime_type=mime,
        base64_data=encoded,
        size_bytes=size,
    )


def build_openai_image_part(attachment: ImageAttachment) -> dict[str, object]:
    """Constrói o bloco de imagem compatível com a API da OpenAI."""
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{attachment.mime_type};base64,{attachment.base64_data}",
        },
    }


def build_anthropic_image_part(attachment: ImageAttachment) -> dict[str, object]:
    """Constrói o bloco de imagem compatível com a API da Anthropic."""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": attachment.mime_type,
            "data": attachment.base64_data,
        },
    }
