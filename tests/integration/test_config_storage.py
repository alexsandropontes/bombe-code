"""Integration F1 config-storage — filesystem REAL (análogo a "DB real"): zero mocks.

Cobre PRD F1: CA1 (descoberta/merge determinístico), CA2 (storage de sessão),
CA3 (lock anti-corrupção), RN1 (paths XDG), RN2 (descoberta subindo do cwd).
"""

import json
import threading
from pathlib import Path

import pytest

from bombe_code.config.loader import load_config
from bombe_code.config.paths import discover_config, get_paths
from bombe_code.storage.session_store import SessionStore

pytestmark = pytest.mark.integration


# --- RN2 / CA1: descoberta de config subindo do cwd ---


def test_descobre_config_em_diretorio_aninhado(tmp_path: Path):
    # Arrange
    project = tmp_path / "proj"
    nested = project / "src" / "pkg"
    nested.mkdir(parents=True)
    cfg = project / "bombe.json"
    cfg.write_text('{"model": "anthropic/claude"}', encoding="utf-8")

    # Act
    found = discover_config(nested)

    # Assert
    assert found == cfg


def test_descobre_ausente_retorna_none(tmp_path: Path):
    # Arrange
    empty = tmp_path / "sem-config"
    empty.mkdir()

    # Act & Assert
    assert discover_config(empty) is None


def test_load_config_sobe_ate_encontrar_e_retorna_valores(tmp_path: Path):
    # Arrange
    project = tmp_path / "proj"
    nested = project / "deep" / "nest"
    nested.mkdir(parents=True)
    (project / "bombe.json").write_text(
        '{"model": "openai/gpt-5", "server": {"port": 4096}}', encoding="utf-8"
    )

    # Act
    cfg = load_config(start=nested)

    # Assert
    assert cfg["model"] == "openai/gpt-5"
    assert cfg["server"]["port"] == 4096


# --- RN1: paths XDG ---


def test_paths_seguem_xdg_data_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    # Act
    paths = get_paths()

    # Assert
    assert paths.data.name == "bombe-code"
    assert str(tmp_path) in str(paths.data)
    assert paths.log == paths.data / "log"


# --- CA2: storage de sessão ---


def test_storage_cria_e_recupera_sessao_com_mensagens(tmp_path: Path):
    # Arrange
    store = SessionStore(root=tmp_path / "storage")

    # Act
    session = store.create_session(title="sessao teste", directory=str(tmp_path))
    store.save_message(
        session["id"], {"id": "msg_1", "role": "user", "session_id": session["id"]}
    )
    store.save_part(
        session["id"],
        {"id": "prt_1", "message_id": "msg_1", "type": "text", "text": "ola"},
    )

    # Assert — roundtrip com instância nova (lê do disco real)
    fresh = SessionStore(root=tmp_path / "storage")
    assert session["id"].startswith("ses_")
    assert fresh.get_session(session["id"]) == session
    assert fresh.list_messages(session["id"]) == [
        {"id": "msg_1", "role": "user", "session_id": session["id"]}
    ]
    assert fresh.list_parts(session["id"])[0]["text"] == "ola"

    # Layout parity com o original: storage/session/{info,message,part}/...
    base = tmp_path / "storage" / "session"
    assert (base / "info" / f"{session['id']}.json").exists()
    assert (base / "message" / session["id"] / "msg_1.json").exists()
    assert (base / "part" / session["id"] / "prt_1.json").exists()


# --- RN2: fallback ~/.bombe ---


def test_fallback_para_bombe_dir_do_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange — home FALSO fora da árvore do cwd
    fake_home = tmp_path / "home"
    home_config = fake_home / ".bombe"
    home_config.mkdir(parents=True)
    cfg_file = home_config / "bombe.json"
    cfg_file.write_text('{"model": "fallback/model"}', encoding="utf-8")
    monkeypatch.setenv("HOME", str(fake_home))

    workdir = tmp_path / "proj" / "deep"
    workdir.mkdir(parents=True)

    # Act
    found = discover_config(workdir)

    # Assert
    assert found == cfg_file


# --- CA3: lock anti-corrupção ---


def test_escrita_concorrente_no_mesmo_arquivo_nao_corrompe(tmp_path: Path):
    # Arrange
    store = SessionStore(root=tmp_path / "storage")
    sid = store.create_session(title="conc", directory=str(tmp_path))["id"]
    errors: list[Exception] = []

    def hammer():
        try:
            for seq in range(20):
                store.save_message(
                    sid,
                    {"id": "msg_same", "role": "user", "session_id": sid, "seq": seq},
                )
        except Exception as exc:  # noqa: BLE001 — captura para asserção
            errors.append(exc)

    threads = [threading.Thread(target=hammer) for _ in range(4)]

    # Act
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Assert — sem erros e arquivo final sempre JSON válido
    assert errors == []
    fresh = SessionStore(root=tmp_path / "storage")
    msgs = fresh.list_messages(sid)
    assert len(msgs) == 1
    raw = (tmp_path / "storage" / "session" / "message" / sid / "msg_same.json").read_text(
        encoding="utf-8"
    )
    assert isinstance(json.loads(raw), dict)
