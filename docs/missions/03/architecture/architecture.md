# Arquitetura Técnica — MISSION-03: Local Inference Engine & MTP Acceleration

## 1. Visão Geral do Sistema
O subsistema de inferência local opera sob um padrão de Isolamento de Hardware e Ciclo de Vida Determinístico.

```
+--------------------------------------------------------------------+
|                         BOMBE AGENTS CORE                          |
+---------------------------------+----------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
|                           HybridRouter                             |
|  - Roteia por complexidade / contexto exigido                      |
+---------------------------------+----------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
|                        LocalModelManager                           |
|  - Fila Indiana (Mutex Global de Hardware)                         |
|  - VRAM Gate Monitor (nvidia-smi < 300MiB check)                   |
|  - Model Lifecycle (spawn, /health probe, graceful SIGKILL)        |
+---------------------------------+----------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
|                    ProcessLauncher (llama-server)                  |
|  Binário: b11985 / CUDA 13.2                                       |
|  Parâmetros Dinâmicos:                                             |
|   - Flash Attention (-fa on/off)                                   |
|   - KV Cache Quant (-ctk q8_0 -ctv q8_0)                           |
|   - MoE CPU Offload (--n-cpu-moe 999)                              |
|   - Context Window (-c 65536 / -c 131072)                          |
|   - MTP Speculative Engine (--model-draft, --spec-type draft-mtp)  |
+--------------------------------------------------------------------+
```

## 2. Componentes e Responsabilidades

### 2.1 `LocalModelManager` (`src/bombe_code/engine/local_manager.py`)
- Atua como Singleton / Mutex em nível de hardware.
- Controla o estado atual (`IDLE`, `SPAWNING`, `READY`, `STOPPING`).
- Executa a verificação `VRAMGate.assert_clean()` via `nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` garantindo `< 300MiB` antes de emitir qualquer novo `subprocess.Popen`.

### 2.2 `ModelHardwareProfile` (`src/bombe_code/engine/profiles.py`)
Estrutura imutável (`dataclass`) encapsulando a configuração específica por modelo:
```python
@dataclass(frozen=True)
class HardwareProfile:
    model_name: str
    model_path: Path
    context_window: int
    flash_attention: bool
    kv_cache_type: str = "q8_0"
    n_cpu_moe: int | None = None
    draft_model_path: Path | None = None
    spec_type: str | None = None
    spec_draft_n_max: int | None = None
```

### 2.3 Matriz de Perfis de Modelos
| Modelo | Contexto | Flash Attention | KV Cache | MoE CPU Offload | MTP Draft Config |
|---|---|---|---|---|---|
| **Gemma 4 E4B** | 131072 (128K) | `off` | `-ctk q8_0 -ctv q8_0` | N/A | `--model-draft mtp-gemma-4-E4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3` |
| **Gemma 4 26B-A4B** | 65536 (64K) | `on` | `-ctk q8_0 -ctv q8_0` | `--n-cpu-moe 999` | `--model-draft mtp-gemma-4-26B-A4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3` |
| **Qwen 3.8-9B** | 65536 (64K) | `on` | `-ctk q8_0 -ctv q8_0` | N/A | `--spec-type draft-mtp --spec-draft-n-max 2` (Nativo) |
| **LFM3** | 131072 (128K) | `on` | `-ctk q8_0 -ctv q8_0` | N/A | Standalone |

### 2.4 Integração com `HybridRouter`
O `HybridRouter` detecta o modelo alvo necessário para a tarefa:
1. Chama `LocalModelManager.acquire_model(model_name)`.
2. Aguarda o endpoint HTTP local (`http://127.0.0.1:8080/v1`) ficar saudável.
3. Despacha os prompts via cliente compatível com a API OpenAI.
4. Libera ou substitui o modelo sob demanda.

## 3. Estratégia de Segurança e Isolamento
- Isolamento absoluto de processos: nenhum subprocesso herda file descriptors abertos.
- Zero vazamento de memória: o monitor `VRAMGate` mata qualquer processo órfão do `llama-server` remanescente na porta antes de validar a VRAM.
