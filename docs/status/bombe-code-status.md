# Status — Bombe Code

> Versão atual: **v0.1.19+dev** (`pyproject.toml` mantém a tag v0.1.19; a `dev` contém refactor DDD `4e3cbef`, workspace governance `d84b00e`, **verbosidade + Ciclo Autônomo de Vetos + RESUME de checkpoint + web obrigatória + LICENSE/NOTICE + lint 0** — aguardando bump de release).
> Atualizado em: 2026-10-05 (3ª auditoria as-is: suíte 449, ruff 0, LICENSE/NOTICE, coverage 80%, RESUME pós-veto).
> Suíte de testes: **449 testes passando, 0 falhas** (~3min25s) com `uv sync` puro — **web UI é dependência obrigatória** (reflex saiu do extra; `uv sync` sozinho cobre tudo).
> Cobertura: **80%** (9549 stmts, `coverage run -m pytest`; `coverage` no dev group).
> Linter: **`ruff check` 0 erros e `ruff format` 100% limpo** (débito histórico de 91 débitos pago neste ciclo, incluindo 1 bug latente real `F821` em teste).
> Provedor padrão: **Z.ai GLM-5.3-Flash**.

## 1. Missão original (a que nos guia)

Reimplementar **100% do opencode original** numa implementação própria chamada **Bombe Code**, em **Python + UV (obrigatório)**, com as regras:

- **Derivação declarada:** nunca negar que somos derivados do opencode; atribuição e licenças no README/NOTICE. Licença nossa: **MIT**.
- **HARNESS & TUI AUTÔNOMOS:** ciclo completo de desenvolvimento com rigor arquitetural, TDD estrito e suporte a Vibe Coding.
- **STREAMING REAL TOKEN-A-TOKEN:** paridade completa com o streaming assíncrono do OpenCode original, suporte a reasoning delta e anti-freezing UI.

**Evolução da missão (Onda 2+):** acima da paridade com o opencode, o produto incorporou o **Turing Runtime Engine** — orquestração determinística da Metodologia ONDA com quality gates, Kanban e máquina de estados — transformando o harness em máquina de engenharia autônoma (ver `docs/architecture/bombe-code-foundation-master.md`).

### 🎯 Filtro da Premissa (teste obrigatório para qualquer ajuste futuro)

> **Teoria do projeto:** agentes especializados + governança + direcionamento de fluxo ⇒ um harness capaz do end-to-end de uma aplicação com intervenção humana mínima. Se a dependência humana fosse manter-se, bastaria usar o opencode original.

1. **O change cria ou remove pedágio humano?** Criar pedágio exige justificativa fortíssima: somente furo de informação real (dado que não existe no projeto).
2. **A parada é por falta de informação ou por pedido de permissão?** Pedido de permissão ("posso continuar?", "está certo?") é PROIBIDO em qualquer modo — a máquina encadeia sozinha.
3. **Todo ponto de espera tem:** auto-resolução primeiro → orçamento de tokens/tempo → escalonamento apenas com evidência estruturada (furo de informação ou não-convergência com laudo).
4. **Transparência total é o padrão** (verboso): cada agente anunciado, streaming completo, tool calls com caminho/args, resultados e gravações de arquivo visíveis. Esconder do usuário é regressão.
5. **O humano nunca precisa saber que houve erro interno:** autocura no boot; o runtime descobre onde parou e continua.
6. **Deploy e processo são inimigos:** `upgrade`/instalação RECUSA rodar com sessão viva do Bombe Code (trava no updater); nunca matar processo sem confirmar inatividade. Verificação de versão no pacote instalado é obrigatória pós-deploy.

## 2. Linha do tempo de entregas homologadas

| Marco | Escopo | Testes no gate | Versão |
|---|---|---|---|
| **ONDA 1** (F1–F9 + F15) | Harness completo: config, storage, providers, session loop, tools, permissions, server SSE, TUI, CLI, streaming real | 376 | v0.1.8 |
| **ONDA-003** (EP-002: skills & agentes) | Skills on-demand, catálogo de 23 agentes + AgentRunner (Pydantic AI), SQLite `.bombe-code/state.db` | 213 | v0.1.9–0.1.10 |
| **ONDA-004** (EP-004: ST-019..022) | ProjectConfigManager (`.bombeconfig`), gestão dinâmica de modos, RCA/Simplify forense, task avulsa + status report | 234 | v0.1.11–0.1.13 |
| **ONDA-005** (EP-005: ST-023..026) | StarterEngine, 4 starters builtin, SnippetRegistry v1, tools `snippet_search/get`, 36 comandos TUI | 248 | v0.1.14–0.1.16 |
| **ONDA-006** (EP-006: ST-027..030) | Upstream Gates (PRD, Journey, Arch, DoR), TuringReviewGate, KanbanManager (SQLite + markdown), wave status dashboard | 262 | v0.1.17–0.1.18 |
| **ONDA-007** (EP-007: ST-031..034) | Ciclo Kanban `DEV_DONE → DONE`, flag Andon de bloqueio, hardening anti-fraude do ReviewGate, priorização flexível no PRD gate | 269 | v0.1.19 |
| **EP-008 / EP-009** (ST-035..038, 039..041) | Ontologia Onda 0 vs. Ondas de Entrega, decomposição PBB atômica, task-level TDD dispatcher, migração do registry v2 (**38 starters, 55 snippets**) | — | v0.1.19 |
| **EP-010 completo** (ST-042..045) | Classificador de templates + protocolo story-zero upstream (ADR/manifesto) e downstream (execução com fallback) | — | pós-v0.1.19 |

Relatórios formais de homologação: `docs/reports/ONDA-00{3..7}-validation-report.md`.

## 3. O que está PRONTO (v0.1.19 + pós-release) — 100% OPERACIONAL

| # | Feature | Status | Evidência as-is |
|---|---------|--------|-----------------|
| F1 | config-storage | ✅ DONE | KV com lock, paths XDG, `project_config.py` (`.bombeconfig` YAML) |
| F2 | providers-auth | ✅ DONE | Z.ai GLM-5.3-Flash prioritário, OpenAI, Anthropic, Ollama, Llama.cpp + `resolver.py` |
| F3 | session-core | ✅ DONE | Models, CRUD, lifecycle, compressão |
| F4 | tools-system | ✅ DONE | Ferramentas builtin + LEGO snippets + execução em runtime |
| F5 | permissions | ✅ DONE | Regras, `shell_scan`, `stage_guard.py` (trava de escrita em src/ no Upstream) |
| F6 | agent-loop | ✅ DONE | Loop de prompts, subtasks, retry, streaming SSE |
| F7 | server-http | ✅ DONE | FastAPI/Uvicorn in-process e standalone, SSE real |
| F8 | tui-chat | ✅ DONE | TUI Textual, streaming reativo, design system |
| F9 | cli | ✅ DONE | Typer (`bombe`/`bombe-code`), `install.sh`, `upgrade` via git |
| F15 | tui-advanced | ✅ DONE | Multilinha + paste, reasoning stream, thinking animado, anti-freezing |
| EP-003 | agents & skills | ✅ DONE | 23 definições em `agents/definitions/`, `AgentRunner` com failover e cooldown |
| EP-006/007 | gates & kanban | ✅ DONE | `turing/upstream_gates.py`, `review_gate.py`, `kanban.py` (SQLite + markdown) |
| EP-009 | registry v2 | ✅ DONE | **38 starters** (`registry/starters/*.yaml` + 27 blueprints físicos) e **55 snippets** em 6 stacks (python, node, go, java, dotnet, react) |
| — | Turing intent | ✅ DONE | `turing/classifier.py` NLU local (0 tokens), waiter 3-tiers, auto-cascade |
| — | Progresso & verbosidade | ✅ DONE | `turing/progress.py` (bus thread-safe): **modo verboso padrão** streama texto/pensamento/tools token-a-token na TUI; `--quiet` (CLI) e `/verbosity` (TUI) exibem só anúncios canônicos de onda/etapa/veto |
| — | Streaming de agentes | ✅ DONE | `AgentRunner._run_with_stream_events` (pydantic-ai `run_stream_events`) com fallback síncrono — acabou a LLM "calada" no caminho das ONDAs |
| — | Ciclo Autônomo de Vetos (v2) | ✅ DONE | `turing/rework.py` + `_veto_rework_cycle`/`_autonomous_rework_burn`: **NENHUM veto para o processo** — classifica, rastreia a causa até o AUTOR do artefato (PRD→@grace, story→@caroli, schema→@codd, testes→@aniche, fallback→@unclebob), autor corrige upstream, stories re-queimadas no burn TDD (VALIDATE→EXECUTE→VALIDATE), re-auditoria; humano só via DÚVIDA DE NEGÓCIO estruturada após esgotar 2 rodadas autônomas |
| — | Encadeamento autônomo TUI | ✅ DONE | Validação OK em AUTO → `end_wave` → próxima onda do Sequenciador automaticamente; onda final → "🏆 MVP completo" (navegação humana de aceite) |
| — | RESUME de checkpoint | ✅ DONE | `start_wave` com a mesma ONDA pendente **retoma a etapa exata persistida** (ex.: VALIDATE pós-veto) — nunca reinicia por heurística; modos salvos prevalecem salvo pedido explícito; **em AUTO a máquina se encadeia sozinha a partir do ponto** (PLAN→plan, EXECUTE→execute, VALIDATE→validate); DISCUSS/DISCOVERY autosserviço (briefing do disco aciona a etapa sozinho; sem briefing → único furo de informação legítimo) |
| — | AUTOCURA global | ✅ DONE | Boot de qualquer comando varre **todas as ondas** (filas do Kanban + relatórios em docs/waves/): onda COMPLETED com stories DEV_DONE ou veredito REJEITADO no relatório → reabre na VALIDATE sozinha; se a onda ativa está vazia (sem cards), **a onda anômala assume o comando da máquina** (checkpoint ativo arquivado no histórico) |
| — | `--force` abolido | ✅ DONE | Trocar de onda arquiva o checkpoint ativo em `wave_history` e prossegue — zero decisão humana; flag removida da TUI/CLI e ignorada no orquestrador |
| — | Veredito estrutural à prova de prosa | ✅ DONE | 4 camadas: rejeição-primeiro (negações tratadas) → consistência por story (⚠️/❌/Parcial na linha da story veta) → aprovação canônica → **rede de segurança re-escaneia o relatório consolidado antes de gravar** — onda JAMAIS fecha com contradição; contradição em AUTO dispara Ciclo Autônomo |
| — | Contra-Auditoria Forense | ✅ DONE | `/wave audit ONDA-xxx` (TUI/CLI, opcional — só o usuário invoca): **@hoare** (24º agente, C.A.R. Hoare) audita "pedido vs. entregue" com o CÓDIGO como verdade — metodologia adversarial ≠ validate: cross-examina alegações do relatório anterior, checagens determinísticas de fraude (0 tokens), **executa a suíte real do projeto** (pytest/npm), amostragem profunda nas stories de risco; FUROs → cards bloqueados + onda reaberta + re-burn TDD autônomo; `AUDITORIA: LIMPA` exige zero furos + veredito canônico |
| — | Economia de tokens retroativa | ✅ DONE | Autocura global virou **aviso determinístico** (custo zero): detecta pendências em ondas antigas e recomenda `/wave audit` — a máquina NUNCA revalida ondas retroativamente por conta própria |
| — | Worktree | ✅ DONE | `worktree/manager.py` (git worktrees por onda/stories) |
| — | Skills/commands | ✅ DONE | `skills/` (discovery, registry, manifest) e `commands/` (loader, templates) |

### Arquitetura DDD pós-release (commits `4e3cbef` e `d84b00e`, não versionados)

- `domain/` — entidades e regras puras: `wave/` (models com `WaveState`, transições legais, `Wave` aggregate; `sequencer.py`; `workspace.py`), `intent/`, `session/`.
- `application/` — serviços de caso de uso: `wave/service.py`, `intent/`.
- `infrastructure/storage/` — adaptadores de persistência.
- `turing/` — motor de orquestração: `state_machine.py`, `orchestrator.py`, `gates.py`, `upstream_gates.py`, `upstream_profiler.py`, `review_gate.py`, `handoff_gate.py`, `kanban.py`, `pbb.py`, `prompt_assembler.py`, `classifier.py`, `waiter.py`.
- Ontologia vigente no domínio (`domain/wave/models.py`): **Onda 0** = `DISCOVERY → INCEPTION → COMPLETED` (bloqueio a EXECUTE); **Ondas de Entrega** = `PLAN → REFINEMENT → EXECUTE → VALIDATE → COMPLETED` + estado `BLOCKED`; `EngineeringMode` = `tdd-code`/`vibe-code` (`spec-code` mantido só por compatibilidade); `DeliveryTarget` = `poc`/`mvp`/`production`.
- Governança de workspace canônico da ONDA + **WaveSequencer** (sequenciamento Lean Inception) entregues no último commit.

**Suíte as-is: 414 testes verdes (72 arquivos unitários + 18 de integração), 0 falhas.**

## 4. O que PRECISA fazer (pendências as-is reais)

> **Backlog de stories: 100% consumido.** Todos os cards existentes (ST-015..045; não há cards ST-001..014 no diretório) estão `DONE` (ST-015..038 estavam com status obsoleto nos cards markdown e foram sincronizados nesta auditoria; evidência: relatórios ONDA-004..007 e código embarcado desde v0.1.2+). Não há story aberta — a próxima demanda exige novo épico.

1. **Novo épico (Onda seguinte)** — definir escopo pós-EP-010: candidatos naturais são fechamento da experiência de Onda 0 (Sequenciador/UpstreamProfiler sem relatório formal de homologação) e itens bônus F10–F14/F16.
2. **Versionar o pós-release** — refactor DDD + workspace governance + EP-010 + autonomia estão na `dev` sem tag SemVer (o hook pre-push faz bump; próximo push de release fecha isso).
3. ~~Zerar débito de lint~~ ✅ **PAGO** (2026-10-05): 91 → 0 erros, formatação 100%.
4. ~~`LICENSE` (MIT) + `NOTICE` de atribuição opencode~~ ✅ **CRIADOS** (2026-10-05).
5. ~~Teste da web UI~~ ✅ **RESOLVIDO** (2026-10-05): **reflex promovido a dependência obrigatória** (web é feature interna) — `uv sync` puro roda a suíte inteira (449 testes).
6. ~~Coverage~~ ✅ **RESOLVIDO** (2026-10-05): `coverage>=7` no dev group; cobertura atual **80%**.
7. ~~Selo formal para EP-008/EP-010~~ ✅ **RESOLVIDO** (2026-10-05): relatórios de homologação retroativa emitidos com evidências — `docs/reports/ONDA-008-validation-report.md` e `docs/reports/ONDA-010-validation-report.md`.
8. **Este status + docs** — manter sincronizados a cada release (status, README e Manual atualizados neste ciclo com verbosidade + Ciclo Autônomo de Vetos + RESUME + web obrigatória).

## 5. Evidência da auditoria (comandos e resultados reais)

```text
uv run pytest -q          (uv sync puro — reflex é dependência obrigatória)
  → 449 passed in ~205s

uv run coverage run -m pytest && uv run coverage report --include="src/*"
  → TOTAL 80% (9549 stmts)

uv run ruff check . && uv run ruff format --check .
  → All checks passed! / 275 files already formatted (débito histórico de 91 pago)

ls src/bombe_code/registry/starters/*.yaml | wc -l   → 38 starters
find registry/snippets -mindepth 3 -maxdepth 3 -type d | wc -l → 55 snippets
find src -name "*.py" -not -path "*__pycache__*" | wc -l → 188 módulos
find tests -name "test_*.py" | wc -l → 92 arquivos de teste
```

## 6. Decisões registradas

- Storage JSON XDG para sessões (não SQLite) — escolha explícita do usuário; **SQLite (`state.db`) é reservado ao estado do Turing/Kanban** em `.bombe-code/` (decisão da Onda 2).
- Camada LLM com injeção de adaptador (seam de fronteira de rede); testes de contrato via servidor SSE local real.
- Ordenação cronológica de mensagens/parts por `created_at` (ids são uuid).
- `run_prompt` é orquestrador único (~90 linhas, minor aceito no quality gate).
- **Toda interação com LLM passa obrigatoriamente pelo `pydantic-ai`** (PydanticAiFactory — decisão EP-002/Onda 2).
- **Classificador de intenções determinístico primeiro** (regex/slots, 0 tokens); LLM classificadora só sob ambiguidade semântica (`needs_llm=True`).
- Registry v2 declarativo em YAML (starters/snippets) substitui os builtins em código, que permanecem como baseline legado.
- Runtime Bombe Core **nunca** vai para o git (regra gravada; `.gitignore` ativo).
