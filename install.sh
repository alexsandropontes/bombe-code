#!/usr/bin/env bash
# ==============================================================================
# Bombe Code — Instalador Oficial via uv e Git
# ==============================================================================
set -euo pipefail

# Estilos de cores ANSI
BOLD='\033[1m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
DIM='\033[2m'
NC='\033[0m' # No Color

APP_NAME="bombe-code"
DEFAULT_GIT_URL="https://github.com/alexsandropontes/bombe-code.git"

usage() {
    echo -e "${BOLD}${CYAN}Bombe Code — Instalador Oficial${NC}"
    echo ""
    echo -e "${BOLD}Uso:${NC}"
    echo "  ./install.sh [opções]"
    echo "  curl -fsSL https://raw.githubusercontent.com/alexsandropontes/bombe-code/main/install.sh | bash"
    echo "  curl -fsSL https://raw.githubusercontent.com/alexsandropontes/bombe-code/main/install.sh | bash -s -- --branch dev-working-ia"
    echo ""
    echo -e "${BOLD}Opções:${NC}"
    echo "  -b, --branch <branch>     Instala a partir de uma branch específica (ex: dev-working-ia, main)"
    echo "  -t, --tag <tag>           Instala uma tag/versão específica (ex: v0.1.2)"
    echo "  -g, --git-url <url>       URL do repositório Git (padrão: ${DEFAULT_GIT_URL})"
    echo "  -l, --local               Instala a partir do diretório local atual"
    echo "  -p, --python <version>    Especifica a versão do Python para uv (ex: 3.13)"
    echo "      --no-modify-path      Não modifica arquivos rc (.bashrc, .zshrc)"
    echo "  -h, --help                Exibe esta ajuda"
    echo ""
}

branch=""
tag=""
git_url="${DEFAULT_GIT_URL}"
local_install=false
python_version=""
no_modify_path=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -b|--branch)
            if [[ -n "${2:-}" ]]; then
                branch="$2"
                shift 2
            else
                echo -e "${RED}Erro: --branch requer o nome da branch.${NC}" >&2
                exit 1
            fi
            ;;
        -t|--tag)
            if [[ -n "${2:-}" ]]; then
                tag="$2"
                shift 2
            else
                echo -e "${RED}Erro: --tag requer o nome da tag (ex: v0.1.2).${NC}" >&2
                exit 1
            fi
            ;;
        -g|--git-url)
            if [[ -n "${2:-}" ]]; then
                git_url="$2"
                shift 2
            else
                echo -e "${RED}Erro: --git-url requer uma URL válida.${NC}" >&2
                exit 1
            fi
            ;;
        -l|--local)
            local_install=true
            shift
            ;;
        -p|--python)
            if [[ -n "${2:-}" ]]; then
                python_version="$2"
                shift 2
            else
                echo -e "${RED}Erro: --python requer uma versão (ex: 3.13).${NC}" >&2
                exit 1
            fi
            ;;
        --no-modify-path)
            no_modify_path=true
            shift
            ;;
        *)
            echo -e "${YELLOW}Aviso: Opção desconhecida ignorada: $1${NC}" >&2
            shift
            ;;
    esac
done

echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║             ⚡ BOMBE CODE — INSTALADOR OFICIAL ⚡              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Checagem do Git
if ! command -v git &>/dev/null; then
    echo -e "${RED}❌ Git não encontrado. Instale o Git antes de prosseguir.${NC}" >&2
    exit 1
fi

# 2. Localização / Instalação do uv
UV_BIN=""
if command -v uv &>/dev/null; then
    UV_BIN=$(command -v uv)
elif [[ -x "$HOME/.local/bin/uv" ]]; then
    UV_BIN="$HOME/.local/bin/uv"
elif [[ -x "$HOME/.cargo/bin/uv" ]]; then
    UV_BIN="$HOME/.cargo/bin/uv"
fi

if [[ -z "$UV_BIN" ]]; then
    echo -e "${YELLOW}📦 uv não encontrado. Instalando o uv oficial da Astral...${NC}"
    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo -e "${RED}❌ Nem curl nem wget foram encontrados para baixar o uv.${NC}" >&2
        exit 1
    fi

    if [[ -x "$HOME/.local/bin/uv" ]]; then
        UV_BIN="$HOME/.local/bin/uv"
    elif [[ -x "$HOME/.cargo/bin/uv" ]]; then
        UV_BIN="$HOME/.cargo/bin/uv"
    else
        echo -e "${RED}❌ Falha ao localizar o uv após a instalação.${NC}" >&2
        exit 1
    fi
    echo -e "${GREEN}✓ uv instalado com sucesso em ${UV_BIN}.${NC}"
fi

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# 3. Verificação do PATH no Shell RC
if [[ "$no_modify_path" = false ]]; then
    SHELL_CONFIG=""
    if [[ -n "${SHELL:-}" ]]; then
        SHELL_NAME=$(basename "$SHELL")
        case "$SHELL_NAME" in
            zsh)
                SHELL_CONFIG="$HOME/.zshrc"
                ;;
            bash)
                if [[ -f "$HOME/.bashrc" ]]; then
                    SHELL_CONFIG="$HOME/.bashrc"
                elif [[ -f "$HOME/.bash_profile" ]]; then
                    SHELL_CONFIG="$HOME/.bash_profile"
                fi
                ;;
        esac
    fi

    if [[ -n "$SHELL_CONFIG" ]] && [[ -f "$SHELL_CONFIG" ]]; then
        if ! grep -q 'export PATH=.*\.local/bin' "$SHELL_CONFIG" 2>/dev/null; then
            echo -e "${DIM}Configurando PATH em ${SHELL_CONFIG}...${NC}"
            echo '' >> "$SHELL_CONFIG"
            echo '# Bombe Code & uv bin path' >> "$SHELL_CONFIG"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        fi
    fi
fi

# 4. Determinação do Alvo de Instalação
INSTALL_CMD=("$UV_BIN" "tool" "install" "--force")

if [[ -n "$python_version" ]]; then
    INSTALL_CMD+=("--python" "$python_version")
fi

if [[ "$local_install" = true ]]; then
    echo -e "${CYAN}📍 Instalando Bombe Code a partir do diretório local atual...${NC}"
    INSTALL_CMD+=(".")
else
    if [[ -n "$tag" ]]; then
        TARGET_REF="git+${git_url}@${tag}"
        echo -e "${CYAN}🚀 Instalando Bombe Code da Tag: ${BOLD}${tag}${NC}..."
    elif [[ -n "$branch" ]]; then
        TARGET_REF="git+${git_url}@${branch}"
        echo -e "${CYAN}🚀 Instalando Bombe Code da Branch: ${BOLD}${branch}${NC}..."
    else
        # Auto-detecta a branch padrão do Git remoto
        DETECTED_BRANCH=""
        if REMOTE_HEAD=$(git ls-remote --symref "$git_url" HEAD 2>/dev/null); then
            DETECTED_BRANCH=$(echo "$REMOTE_HEAD" | awk '/^ref: refs\/heads\// {sub("refs/heads/", "", $2); print $2}')
        fi
        if [[ -z "$DETECTED_BRANCH" ]]; then
            DETECTED_BRANCH="main"
        fi
        TARGET_REF="git+${git_url}@${DETECTED_BRANCH}"
        echo -e "${CYAN}🚀 Instalando Bombe Code da Branch Padrão (${BOLD}${DETECTED_BRANCH}${NC})..."
    fi
    INSTALL_CMD+=("$TARGET_REF")
fi

# 5. Execução do uv tool install
echo -e "${DIM}Executando: ${INSTALL_CMD[*]}${NC}"
"${INSTALL_CMD[@]}"

# 6. Validação e Informações de Uso
echo ""
BOMBE_EXE="$HOME/.local/bin/bombe-code"

if [[ -x "$BOMBE_EXE" ]]; then
    VERSION_INFO=$("$BOMBE_EXE" version 2>/dev/null || echo "instalado")
    echo -e "${GREEN}${BOLD}✓ ${VERSION_INFO} instalado com sucesso!${NC}"
else
    echo -e "${YELLOW}✓ Instalação concluída via uv tool!${NC}"
fi

echo ""
echo -e "${BOLD}${CYAN}────────────────────────────────────────────────────────────────${NC}"
echo -e "${BOLD}Comandos disponíveis no seu terminal:${NC}"
echo -e "  ${GREEN}bombe-code --help${NC}      ${DIM}# Ajuda completa do Bombe Code${NC}"
echo -e "  ${GREEN}bombe-code tui${NC}         ${DIM}# Inicia a interface gráfica no terminal (TUI)${NC}"
echo -e "  ${GREEN}bombe-code wave start${NC}  ${DIM}# Inicia uma ONDA de engenharia de software${NC}"
echo -e "  ${GREEN}bombe-code upgrade${NC}     ${DIM}# Atualiza o Bombe Code diretamente via Git${NC}"
echo -e "${BOLD}${CYAN}────────────────────────────────────────────────────────────────${NC}"
echo -e "${DIM}Nota: se o comando 'bombe-code' não for encontrado de imediato, rode:${NC}"
echo -e "  ${YELLOW}source ~/.bashrc${NC}  ${DIM}(ou reinicie sua sessão do terminal)${NC}"
echo ""
