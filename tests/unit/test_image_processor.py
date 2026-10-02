"""Testes unitários para a Feature 23: image-processor (RED phase)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bombe_code.images.processor import (
    ImageAttachment,
    build_anthropic_image_part,
    build_openai_image_part,
    process_image,
)


def test_process_image_png(tmp_path: Path):
    img_file = tmp_path / "sample.png"
    # Cabeçalho mínimo válido PNG (8 bytes) + dados
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01")

    attachment = process_image(img_file)
    assert isinstance(attachment, ImageAttachment)
    assert attachment.mime_type == "image/png"
    assert attachment.file_name == "sample.png"
    assert len(attachment.base64_data) > 0


def test_process_image_formats_payload(tmp_path: Path):
    img_file = tmp_path / "diagram.jpeg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00")

    attachment = process_image(img_file)

    # Payload para OpenAI
    oai_part = build_openai_image_part(attachment)
    assert oai_part["type"] == "image_url"
    assert oai_part["image_url"]["url"].startswith("data:image/jpeg;base64,")

    # Payload para Anthropic
    ant_part = build_anthropic_image_part(attachment)
    assert ant_part["type"] == "image"
    assert ant_part["source"]["type"] == "base64"
    assert ant_part["source"]["media_type"] == "image/jpeg"
    assert ant_part["source"]["data"] == attachment.base64_data


def test_process_image_size_limit(tmp_path: Path):
    big_file = tmp_path / "heavy.png"
    big_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024 + 10))

    with pytest.raises(ValueError, match="excede o limite"):
        process_image(big_file, max_size_mb=1.0)


def test_part_widget_renders_image():
    from bombe_code.tui.widgets.parts_view import PartWidget

    widget = PartWidget({"type": "image", "file_name": "foto.png", "mime_type": "image/png"})
    rendered = widget.render()
    assert "foto.png" in str(rendered.renderable)

