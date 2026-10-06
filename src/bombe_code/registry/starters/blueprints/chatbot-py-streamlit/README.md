# Chatbot POC - Python + Streamlit

Chatbot simples para teste rápido de agentes Forge.

## 🚀 Quick Start

### 1. Configurar Ambiente

```bash
# Copiar .env.example para .env
cp .env.example .env

# Editar .env e adicionar chave de API
# OPENAI_API_KEY=sk-...  OU  GEMINI_API_KEY=...
```

### 2. Instalar Dependências (UV)

```bash
# Backend
cd backend
uv sync

# Frontend
cd ../frontend
uv sync
```

### 3. Rodar

```bash
# Terminal 1 - Backend
cd backend
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
uv run streamlit run app.py
```

### 4. Acessar

Frontend: http://localhost:8501
Backend API: http://localhost:8000/docs

## 📁 Estrutura

```
chatbot/
├── backend/
│   ├── pyproject.toml      # Dependências do backend
│   └── app/
│       ├── main.py         # API FastAPI
│       ├── llm_client.py   # Cliente OpenAI/Gemini
│       └── orchestrator.py # Orquestração de agentes
├── frontend/
│   ├── pyproject.toml      # Dependências do frontend
│   └── app.py              # Streamlit UI
├── agents/
│   └── teams/              # Times criados pelo wizard
└── .env                    # Configurações
```

## 🤖 Como Funciona

1. **Selecionar Time**: Sidebar → Carregar Times → Selecionar
2. **Enviar Mensagem**: Digite e envie
3. **Orquestração**: Mensagem passa por todos os agentes do time (A→B→C)
4. **Resposta**: Última resposta é exibida

## 🔑 Regras de API

- **OPENAI_API_KEY** definida → Usa OpenAI (ou compatível)
- **GEMINI_API_KEY** definida → Usa Gemini
- **Ambas definidas** → OpenAI ganha
- **OPENAI_BASE_URL** vazio → OpenAI oficial
- **OPENAI_BASE_URL** preenchido → API compatível

## 📝 Criar Times

Use o wizard do Forge Core:

```bash
code-forge create team
```

Depois finalize com o workflow:

```
@unclebob /finalize-chatbot
```
