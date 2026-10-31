# PRD — MISSION-03: Sistema de Inferência Local Resiliente, Otimização de Hardware e Aceleração MTP

## 1. Problema de Negócio
Durante as POCs com modelos locais de LLM em GPUs de consumo/workstation (16GB VRAM), foram observados 4 problemas críticos:
1. **OOM Crítico por Concorrência:** Modelos concorrentes tentavam subir antes da desalocação completa do modelo anterior, travando a VRAM e corrompendo o processo do `llama-server`.
2. **Context Window Oversubscription:** Alocação ingênua de 128K de contexto causava swap massivo para a RAM do sistema e estouro de memória física em modelos de 26B e Qwen 3.8.
3. **Latência de Geração Elevada:** A decodificação padrão autorregressiva token-por-token limitava o throughput de geração a patamares inviáveis para tarefas de código complexas.
4. **Falta de Abstração de Ciclo de Vida:** O framework não possuía um gestor determinístico que garantisse teardown seguro, healthcheck via endpoint HTTP e warmup antes do despacho de requisições.

## 2. Personas & Usuários Impactados
- **Engenheiro de IA / Desenvolvedor:** Necessita de respostas de código com latência baixa e garantia de que o modelo certo será invocado sem que a máquina congele.
- **Framework Bombe Code (Agentes Autônomos):** Requer alta confiabilidade nas chamadas de LLM local, com fallback transparente e limites de contexto rigorosamente controlados.

## 3. Requisitos Funcionais (FR)
- **FR-01 (Gestor de Processos):** O sistema deve iniciar e terminar instâncias do `llama-server` (binário `b11985`, CUDA 13.2) de forma atômica e programática via Python (`LocalModelManager`).
- **FR-02 (Porteiro de VRAM - Fila Indiana):** Antes de iniciar um novo modelo, o sistema deve garantir que o processo anterior finalizou e verificar via `nvidia-smi` que a VRAM utilizada pelo driver/processos gerenciados está abaixo de 300MiB.
- **FR-03 (Perfis de Hardware & Contexto):**
  - Modelos MoE (ex: Gemma 4 26B-A4B): Suportar flag `--n-cpu-moe 999` para offload de experts na CPU/RAM mantendo camadas densas na GPU.
  - Flash Attention: Habilitar `-fa on` nos modelos compatíveis (Qwen, Gemma 26B) e `-fa off` nos incompatíveis (Gemma E4B sob certas quantizações).
  - KV Cache: Fixar `-ctk q8_0 -ctv q8_0` para manter fidelidade sem estourar alocação.
  - Teto de Context Window: Gemma E4B e LFM3 suportam 128K (`-c 131072`); Qwen 3.8-9B e Gemma 4 26B limitados a 64K (`-c 65536`).
- **FR-04 (Multi-Token Prediction - MTP):**
  - Permitir download e configuração de modelos draft complementares (`mtp-*.gguf`).
  - Para Gemma E4B: aplicar `--model-draft mtp-gemma-4-E4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3 -fa off`.
  - Para Gemma 26B: aplicar `--model-draft mtp-gemma-4-26B-A4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3 -fa on --n-cpu-moe 999`.
  - Para Qwen 3.8-9B: aplicar modo nativo `--spec-type draft-mtp --spec-draft-n-max 2 -fa on`.
- **FR-05 (Roteamento & Validação E2E):** O `HybridRouter` deve consumir os endpoints expostos pelo `LocalModelManager` e executar com sucesso a suíte de testes de geração do Token Bucket Rate Limiter.

## 4. Requisitos Não-Funcionais (NFR)
- **NFR-01 (Resiliência):** Timeout de shutdown gracioso de 15s; se o processo não encerrar, aplicar `SIGKILL` forçado e revalidar VRAM.
- **NFR-02 (Healthcheck Determinístico):** O launcher só considera o modelo pronto quando `GET /health` retornar HTTP 200 em menos de 120s.
- **NFR-03 (Zero Mocks em Testes de Integração):** As verificações de comandos de CLI e montagem de parâmetros devem ser cobertas por testes de unidade estritos e testes de integração com subprocessos reais.

## 5. Critérios de Sucesso
1. 100% de sucesso na troca sequencial de modelos (swap) sem OOM ou deadlock.
2. Aceleração de geração comprovada com MTP ativo (aumento mínimo de 30% em tokens/segundo versus inferência pura).
3. Implementação e passagem com 100% dos testes verdes no desafio do Token Bucket Rate Limiter.
