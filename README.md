# Bombe Code
> Harness local-first, soberano e determinístico para engenharia de software com múltiplos agentes de IA.

---

## ⚠️ Disclaimer de Homenagens & Nomes

### Nomes e Homenagens

Os nomes, pseudônimos e referências a profissionais utilizados neste projeto são homenagens a pessoas que contribuíram significativamente para a computação, engenharia de software, ciência da computação e áreas relacionadas.

A utilização desses nomes tem finalidade exclusivamente referencial e honorífica. Ela não implica, sugere ou representa participação, colaboração, endosso, afiliação, patrocínio ou contribuição direta dessas pessoas para este projeto.

As personas e agentes que utilizam esses nomes são personagens conceituais criados exclusivamente para representar papéis dentro da arquitetura do Bombe Code. Suas opiniões, decisões, comportamentos e instruções são definidos pelo projeto e não representam necessariamente as opiniões ou posições das pessoas homenageadas.

Os nomes foram escolhidos por sua relação histórica ou profissional com as áreas representadas pelas respectivas personas. O projeto não pretende reproduzir, simular ou se passar pelas pessoas homenageadas.

> **Aviso Específico:** Uma persona denominada `@turing`, `@unclebob`, `@grace`, ou qualquer outra referência nominal **não constitui** uma representação digital, réplica ou simulação da pessoa homenageada.

Para detalhes completos sobre cada uma das 23 pessoas homenageadas e seus respectivos países de origem, consulte [Catálogo de Personas & Homenagens](docs/architecture/agents-homage.md).

---

## Visão Geral

O Bombe Code é uma plataforma local-first para desenvolvimento guiado por agentes de inteligência artificial sob as fases de **UPSTREAM** (concepção, viabilidade, PRD, jornada de usuário, modelagem e arquitetura) e **DOWNSTREAM** (desenvolvimento por linguagem, TDD estrito, AppSec defensivo e ofensivo, QA de automação, infraestrutura e validação contratual).

### Arquitetura de Fases da ONDA

1. **FASE 1: UPSTREAM**
   - `DISCUSS`: Viabilidade & Inovação (`@meira`), Product Management & PRD (`@grace`).
   - `PLAN`: User Journey (`@alan`), UI/UX Heuristics (`@norman`), Arquitetura de Sistemas (`@ieru`), Banco Relacional (`@codd`), Banco NoSQL & Vetores (`@claudia`), Threat Modeling & Cripto (`@barreto`), Agile Master (`@caroli`), AI Context (`@nelson`).

2. **FASE 2: DOWNSTREAM**
   - `EXECUTE`: Especialistas backend por stack (Elixir: `@valim`, Python/Go: `@barbara`, .NET: `@scott`, Node.js/TS: `@ryan`, Java: `@james`), Frontend UI (`@ada`), Tech Lead & Clean Code (`@unclebob`), AppSec Ofensivo & Pentest (`@diego`), QA & Automação de Testes (`@aniche`), SRE & Redes (`@demi`).
   - `VALIDATE`: Contract Validator (`@edith`), Gov, FinOps & AI Ethics (`@nina`).
   - **Maestro do Runtime:** Orquestração de ciclo de vida e gates determinísticos (`@turing`).

---

## Executando o Projeto

```bash
# Instalação das dependências via uv
uv sync

# Execução da suíte completa de testes
uv run pytest

# Verificação de qualidade e tipagem
uv run ruff check .
```
