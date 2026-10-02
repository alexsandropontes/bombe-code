"""Módulo de processamento de imagens e anexos multimodais."""

from .processor import (
    ImageAttachment,
    build_anthropic_image_part,
    build_openai_image_part,
    process_image,
)

__all__ = [
    "ImageAttachment",
    "build_anthropic_image_part",
    "build_openai_image_part",
    "process_image",
]
