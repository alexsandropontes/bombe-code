"""Testes unitários para o TuringWaiter (3-Tier Cascade Intent Dispatcher)."""

from __future__ import annotations

import pytest

from bombe_code.turing.waiter import TuringAction, TuringWaiter


@pytest.mark.anyio
async def test_waiter_tier_1_literal_slash():
    waiter = TuringWaiter()
    action = await waiter.attend("/wave status")
    assert isinstance(action, TuringAction)
    assert action.tier == 1
    assert action.command == "/wave status"
    assert not action.needs_llm


@pytest.mark.anyio
async def test_waiter_tier_2_briefing_start_discuss():
    waiter = TuringWaiter()
    briefing = """# BRIEFING — DROPS MVP
## 1. Visão do produto
Drops é um aplicativo de microconteúdo diário voltado a bem-estar.
## 2. Escopo do MVP
Uma dose por momento.
"""
    action = await waiter.attend(briefing, stage="DISCUSS", is_greenfield=True)
    assert action.tier == 2
    assert action.intention == "start_discuss"
    assert action.action_type == "run_discuss"
    assert action.action_args["topic"] == briefing.strip()
    assert "/wave discuss" in str(action.command)
    assert not action.needs_llm


@pytest.mark.anyio
async def test_waiter_tier_2_wave_status():
    waiter = TuringWaiter()
    action = await waiter.attend("como está o progresso da onda atual?")
    assert action.tier == 2
    assert action.intention == "wave_status"
    assert action.command == "/wave status"
    assert not action.needs_llm


@pytest.mark.anyio
async def test_waiter_tier_2_plan():
    waiter = TuringWaiter()
    action = await waiter.attend("vamos planejar a arquitetura e backlog")
    assert action.tier == 2
    assert action.intention == "start_plan"
    assert action.command == "/wave plan"
    assert not action.needs_llm


@pytest.mark.anyio
async def test_waiter_tier_2_cycle_story():
    waiter = TuringWaiter()
    action = await waiter.attend("executar ciclo da story ST-003")
    assert action.tier == 2
    assert action.intention == "start_cycle"
    assert action.slots.get("story_id") == "ST-003"
    assert action.command == "/wave execute ST-003"
    assert not action.needs_llm


@pytest.mark.anyio
async def test_waiter_tier_2_resume():
    waiter = TuringWaiter()
    action = await waiter.attend("continue de onde parou por favor")
    assert action.tier == 2
    assert action.intention == "workflow_resume"
    assert action.command == "/wave resume"
    assert not action.needs_llm
