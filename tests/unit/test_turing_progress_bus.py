"""Testes do TuringProgressBus — publicação thread-safe para subscribers asyncio."""

import asyncio
import threading

import pytest

from bombe_code.turing.progress import BUS, ProgressEvent, TuringProgressBus


@pytest.fixture(autouse=True)
def _reset_globals():
    BUS.set_verbosity("verbose")
    yield
    BUS.set_verbosity("verbose")


def test_publish_verbose_entrega_todos_os_eventos():
    bus = TuringProgressBus()
    recebidos: list[ProgressEvent] = []

    async def cenario():
        task = asyncio.create_task(_consumir(bus, recebidos, esperados=3))
        await asyncio.sleep(0.05)
        bus.publish("text_delta", agent="@meira", text="olá")
        bus.publish("thinking_delta", agent="@meira", text="pensando")
        bus.publish("announcement", text="Etapa concluída")
        await task

    asyncio.run(cenario())
    assert [e.type for e in recebidos] == ["text_delta", "thinking_delta", "announcement"]
    assert recebidos[0].text == "olá"
    assert recebidos[0].agent == "@meira"


def test_publish_quiet_filtra_deltas_e_mantem_anuncios():
    bus = TuringProgressBus()
    bus.set_verbosity("quiet")
    recebidos: list[ProgressEvent] = []

    async def cenario():
        task = asyncio.create_task(_consumir(bus, recebidos, esperados=2))
        await asyncio.sleep(0.05)
        bus.publish("text_delta", text="ignorado")
        bus.publish("tool_call", agent="@edith")
        bus.publish("stage_end", text="VALIDATE concluída")
        bus.publish("veto_rework", text="retrabalho")
        await task

    asyncio.run(cenario())
    assert [e.type for e in recebidos] == ["stage_end", "veto_rework"]


def test_publicacao_de_thread_externa_chega_no_loop():
    bus = TuringProgressBus()
    recebidos: list[ProgressEvent] = []

    async def cenario():
        task = asyncio.create_task(_consumir(bus, recebidos, esperados=1))
        await asyncio.sleep(0.05)
        thread = threading.Thread(
            target=bus.publish, args=("stage_start",), kwargs={"text": "de outra thread"}
        )
        thread.start()
        thread.join()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(cenario())
    assert recebidos[0].type == "stage_start"
    assert recebidos[0].text == "de outra thread"


def test_unsubscribe_para_o_stream():
    bus = TuringProgressBus()

    async def cenario():
        queue, unsubscribe = bus.subscribe()
        assert bus.subscriber_count() == 1
        unsubscribe()
        assert bus.subscriber_count() == 0
        assert await asyncio.wait_for(queue.get(), timeout=1) is None

    asyncio.run(cenario())


def test_announce_e_evento_canonico_em_ambos_os_modos():
    bus = TuringProgressBus()
    for modo in ("verbose", "quiet"):
        bus.set_verbosity(modo)
        recebidos: list[ProgressEvent] = []

        async def cenario(destino: list[ProgressEvent]) -> None:
            task = asyncio.create_task(_consumir(bus, destino, esperados=1))
            await asyncio.sleep(0.05)
            bus.announce("🌊 ONDA-000 iniciada")
            await task

        asyncio.run(cenario(recebidos))
        assert recebidos[0].type == "announcement"
        assert "ONDA-000" in recebidos[0].text


async def _consumir(bus: TuringProgressBus, destino: list, esperados: int) -> None:
    async for evento in bus.stream():
        destino.append(evento)
        if len(destino) >= esperados:
            break
