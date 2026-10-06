# EP-007: Ciclo de Vida do Kanban com VALIDATE, Runtime Gates Anti-Fraude e Priorização Flexível

> **Épico:** EP-007  
> **Status:** IN_PROGRESS  
> **Responsáveis:** @turing (Orquestrador), @edith (Validadora), @aniche (Testes), @unclebob (Review)  
> **Modo:** tdd-code  

---

## 1. Visão Geral & Problema
O fluxo do Kanban precisava refletir a realidade física da fábrica de software sem estados presumidos:
1. Uma story que termina a revisão técnica de `@aniche` e `@unclebob` não está `DONE`, ela está **`DEV_DONE`**.
2. Quando a fase de validação de produto é iniciada com `@edith` e `@nina`, os cards transitam formalmente para o status **`VALIDATE`**.
3. Somente após `@edith` atestar que a entrega cumpre o PRD é que os cards são promovidos para o **`DONE`** definitivo.
4. O `TuringReviewGate` deve inspecionar ativamente contra fraudes de código (`NotImplementedError`, mocks enganosos e `pass` em stubs).
5. O `PRDQualityGate` deve aceitar múltiplos critérios formais de priorização (`RICE`, `WSJF`, `MoSCoW`, `ICE`).

---

## 2. Cadeia de Estados do Card no Kanban
```
BACKLOG ──► READY ──► IN_PROGRESS ──► IN_REVIEW ──► DEV_DONE ──► VALIDATE ──► DONE
```

---

## 3. Stories do Épico
* **ST-031:** Ciclo de Vida do Kanban com `DEV_DONE`, `VALIDATE` e `DONE` no `KanbanManager` e `WaveOrchestrator`.
* **ST-032:** Hardening do `TuringReviewGate` com scanner anti-fraude (`NotImplementedError`, stubs vazios e mocks abusivos).
* **ST-033:** Flexibilização de Critérios Formais de Priorização no `PRDQualityGate` (RICE, WSJF, MoSCoW, ICE).
* **ST-034:** Dashboard da ONDA e CLI/TUI com visualização completa das colunas `DEV_DONE` e `VALIDATE`.
