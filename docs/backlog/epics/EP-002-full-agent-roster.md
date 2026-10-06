# ÉPICO EP-002: EXPANSÃO DO ELENCO COMPLETO DE AGENTES & ESPECIALIDADES POR STACK

> **Status:** Aberto / Planejado  
> **Dependência:** ONDA 3 (Sistema Base de Agentes & Skills On-Demand)  
> **Composição:** 23 Agentes Oficiais (12 do Brasil, 6 dos Estados Unidos, 3 do Reino Unido, 1 do Canadá e 1 Maestro Universal)  
> **Aviso Legal:** Nomes e referências possuem finalidade exclusivamente honorífica e referencial de papéis conceituais. Consulte o [Disclaimer de Homenagens](file:///home/lexpontes/projetos/struct/bombe-code/docs/architecture/agents-homage.md).  

---

## 1. Visão do Épico

O Bombe Core original contemplava mais de 20 especialistas para cobrir cada camada, linguagem de programação e disciplina do ciclo de vida de software. O Bombe Code herda essa riqueza, expandindo-a de forma modular, leve e sem poluição de tokens:
- **Especialistas de Backend por Stack:** José Valim não programa em todas as linguagens; temos especialistas dedicados para Python/Go, .NET, Node.js/TypeScript, Java e Elixir.
- **Arquiteto da Jornada do Usuário:** Reintegração de `@alan` para mapear de ponta a ponta entry points, navegação e telas faltantes.
- **Engenharia de Testes Automatizados (QA de Automação):** `@aniche` atuando especificamente na arquitetura e implementação de testes unitários, integração e E2E reais.
- **Dupla Brasileira de Segurança de Aplicação (AppSec & Criptografia):** A segurança de aplicação não fica diluída. Criamos duas cadeiras técnicas autônomas para AppSec defensivo e ofensivo: `@barreto` (Criptografia, STRIDE, Auth) e `@diego` (Auditoria Ofensiva, OWASP, Pentest).
- **Maioria de Pioneiros Brasileiros:** 12 especialistas brasileiros contra 10 pioneiros internacionais dos Estados Unidos, Reino Unido e Canadá (+ Turing como maestro neutro).

---

## 2. Mapa do Elenco Completo de 23 Agentes

```mermaid
flowchart TD
    subgraph ORQUESTRAÇÃO
        TURING["@turing<br>Maestro do Runtime"]
    end

    subgraph UPSTREAM["FASE 1: UPSTREAM (Concepção & Planejamento)"]
        direction TB
        MEIRA["@meira<br>Viabilidade & Inovação"]
        GRACE["@grace<br>Product Manager & PRD"]
        ALAN["@alan<br>User Journey & Navigation"]
        NORMAN["@norman<br>UI/UX & Heurísticas"]
        IERU["@ieru<br>Arquiteto de Software"]
        CODD["@codd<br>DB Relacional (SQL)"]
        CLAUDIA["@claudia<br>DB NoSQL & Vetores"]
        CAROLI["@caroli<br>Agile Master (Lean Inception)"]
        BARRETO_UP["@barreto<br>Threat Modeling & Cripto"]
    end

    subgraph DOWNSTREAM["FASE 2: DOWNSTREAM (Construção, Segurança & Validação)"]
        direction TB
        subgraph DEV_STACKS["Desenvolvimento por Stack"]
            VALIM["@valim<br>Backend Elixir & Concorrência"]
            BARBARA["@barbara<br>Backend Python & Go"]
            SCOTT["@scott<br>Backend .NET & C#"]
            RYAN["@ryan<br>Backend Node.js & TypeScript"]
            JAMES["@james<br>Backend Java & Spring Boot"]
            ADA["@ada<br>Frontend React/Tailwind/Flutter"]
        end

        subgraph SECURITY_QUALITY["Segurança, Qualidade & SRE"]
            BOB["@unclebob<br>Tech Lead & Selo do Cycle"]
            ARANHA["@diego<br>AppSec, OWASP & Pentest"]
            ANICHE["@aniche<br>QA de Automação & Testes E2E"]
            EDITH["@edith<br>Contract Validator & Selo Final"]
            DEMI["@demi<br>SRE, Infraestrutura & Redes"]
            NELSON["@nelson<br>Prompt Engineer & AI Context"]
            NINA["@nina<br>Gov, FinOps & Ética em IA"]
        end
    end

    TURING -.-> UPSTREAM
    TURING -.-> DOWNSTREAM
```

---

## 3. Catálogo Oficial dos Agentes por Especialidade

| Handle | Agente | País | Papel Técnico | Etapa Primária | Escopo de Atuação |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **@turing** | Alan Turing | Reino Unido | Autônomo Orchestrator | Todas | Orquestração da ONDA, máquina de estados e fiscalização de gates. |
| **@meira** | Silvio Meira | Brasil | Viabilidade & Inovação | `DISCUSS` | Validação de ideia, análise de mercado e fatiamento estratégico. |
| **@grace** | Grace Hopper | Estados Unidos | Product Manager & PRD | `DISCUSS` | Escopo de produto, priorização RICE, personas e elaboração do PRD. |
| **@alan** | Alan Cooper | Estados Unidos | User Journey Architect | `PLAN` | Mapeamento de entry points, fluxos de navegação e telas faltantes. |
| **@norman** | Don Norman | Estados Unidos | UI/UX Designer | `PLAN` | Heurísticas de usabilidade, design emocional e especificações visuais. |
| **@ieru** | Roberto Ierusalimschy | Brasil | Arquiteto de Software | `PLAN` | Arquitetura modular, hexagonal, contratos de API e ADRs. |
| **@codd** | Edgar F. Codd | Reino Unido | Database Architect (SQL) | `PLAN` | Schemas relacionais, normalização de dados, índices e migrações. |
| **@claudia** | Claudia Bauzer Medeiros | Brasil | Database Architect (NoSQL) | `PLAN` | Caching distribuído (Redis), vector stores e dados não-relacionais. |
| **@barreto** | Paulo Barreto | Brasil | Security Architect & Cripto | `PLAN` | Threat Modeling (STRIDE), criptografia, JWT/OAuth2 e dados sensíveis. |
| **@caroli** | Paulo Caroli | Brasil | Agile Master & Flow | `PLAN` | Lean Inception, quebra de épicos e stories verticais com DoR. |
| **@nelson** | Nelson Mattos | Brasil | Prompt & AI Context | `PLAN` | Engenharia de prompts sob PDW 4.0 e grounding contextual. |
| **@valim** | José Valim | Brasil | Backend Lead (Elixir) | `EXECUTE` | Lógica concorrente, TDD estrito e resiliência de processos. |
| **@barbara** | Barbara Liskov | Estados Unidos | Backend Lead (Python/Go) | `EXECUTE` | APIs em FastAPI/Pydantic e Go/Gin com tipagem estrita. |
| **@scott** | Scott Guthrie | Estados Unidos | Backend Lead (.NET/C#) | `EXECUTE` | APIs em ASP.NET Core 8+, Minimal APIs, C# e EF Core. |
| **@ryan** | Ryan Dahl | Estados Unidos | Backend Lead (Node/TS) | `EXECUTE` | APIs assíncronas em Fastify, Express, Bun e TypeScript. |
| **@james** | James Gosling | Canadá | Backend Lead (Java) | `EXECUTE` | APIs em Java 21+, Spring Boot 3 e Virtual Threads. |
| **@ada** | Ada Lovelace | Reino Unido | Frontend Engineer | `EXECUTE` | Interfaces visuais (React/Tailwind/Flutter) conectadas à API real. |
| **@unclebob** | Robert C. Martin | Estados Unidos | Tech Lead & Reviewer | `EXECUTE` | Code review cirúrgico, Clean Code, SOLID e Selo do Cycle. |
| **@diego** | Diego Aranha | Brasil | AppSec & Offensive Auditor | `EXECUTE` | Auditoria OWASP Top 10, sanitização de inputs e pentest em rotas. |
| **@aniche** | Maurício Aniche | Brasil | QA & Test Architect | `EXECUTE` | Pirâmide de testes, automação de integração e testes E2E reais. |
| **@demi** | Demi Getschko | Brasil | SRE, Infra & Redes | `EXECUTE` | Dockerfiles, docker-compose, CI/CD, deploys e healthchecks. |
| **@edith** | Edith Ranzini | Brasil | Contract Validator & QA | `VALIDATE` | Auditoria PRD vs. Entregável e Selo de Homologação Final da ONDA. |
| **@nina** | Nina Silva | Brasil | Gov & FinOps Auditor | `VALIDATE` | Auditoria de custos de tokens, compliance e governança ética de IA. |

---

## 4. Plano de Entrega das Stories do Épico EP-002

1. **Story ST-010: Registro dos Especialistas de Linguagem Backend**
   - Incorporar `@barbara` (Python/Go), `@scott` (.NET/C#), `@ryan` (Node/TS) e `@james` (Java/Spring) ao `AgentRegistry`.
2. **Story ST-011: Reintegração do User Journey Architect (`@alan`)**
   - Definir os contratos de mapeamento de entry points, navegação e telas faltantes em `docs/architecture/journey.md`.
3. **Story ST-012: Blindagem de Segurança da Aplicação (`@barreto` & `@diego`)**
   - Criar os agentes de AppSec defensivo (Threat Modeling/Criptografia) e ofensivo (OWASP/Pentest).
4. **Story ST-013: Registro dos Especialistas de Qualidade, Infra & Governança**
   - Incorporar `@aniche` (QA de Automação), `@demi` (SRE/Infra), `@claudia` (NoSQL/Vetores), `@nelson` (AI Context) e `@nina` (FinOps/Ética).
5. **Story ST-014: Testes de Integração e Suite Completa no AgentRunner**
   - Validar suite de 23 agentes com 100% de cobertura, mantendo zero erros no Ruff e 100% de testes verdes.
