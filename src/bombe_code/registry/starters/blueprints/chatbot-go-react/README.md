# Chatbot POC - Go + React

## Quick Start

### 1. Configurar
```bash
cp .env.example .env
# Editar .env com chaves de API
```

### 2. Backend (Go)
```bash
cd backend
go mod tidy
go run cmd/api/main.go
```

### 3. Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

### 4. Acessar
http://localhost:5173

## Estrutura
```
chatbot/
├── backend/      # Go API
├── frontend/     # React UI
├── agents/teams/ # Times de agentes
└── .env
```
