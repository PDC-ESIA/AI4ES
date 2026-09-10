#!/usr/bin/env bash
#
# Executa o benchmark do Agente de Design (benchmark_gemini_copilot.py) numa
# rodada COMPLETA — todos os modelos, todos os cenários, sem --resume.
#
# Roda em container (política da máquina: nada é instalado no host) e sob
# `screen`, para que a queda da conexão SSH não interrompa o experimento.
#
# Uso:
#   ./run_benchmark.sh              # arquiva a rodada anterior e roda tudo
#   ./run_benchmark.sh --resume     # só o que falta (mantém o results.json)
#   ./run_benchmark.sh --models astra --scenarios G01 G02
#
# Qualquer argumento é repassado ao benchmark_gemini_copilot.py. Com --resume
# a rodada anterior NÃO é arquivada nem apagada, porque ela é o insumo.

set -euo pipefail

REPO="$HOME/PDC/AI4ES"
IMAGEM="ghcr.io/astral-sh/uv:python3.12-bookworm-slim"
SESSAO="benchmark"
CONTAINER="benchmark-run"
LOG="$HOME/benchmark-$(date +%Y%m%d_%H%M%S).log"

SAIDA="$REPO/docs/Time_2_Design/analise-qualitativa/outputs"
RELATORIO="$REPO/docs/Time_2_Design/analise-qualitativa/benchmark_gemini_copilot_relatorio.md"

# --resume em qualquer posição preserva a rodada anterior.
RESUME=0
for arg in "$@"; do [ "$arg" = "--resume" ] && RESUME=1; done

# --- Verificações antes de gastar horas de execução -------------------------

[ -d "$REPO" ] || { echo "ERRO: repositório não encontrado em $REPO"; exit 1; }
[ -f "$REPO/benchmark_gemini_copilot.py" ] || { echo "ERRO: benchmark_gemini_copilot.py ausente em $REPO"; exit 1; }

if ! docker info >/dev/null 2>&1; then
    echo "ERRO: sem acesso ao daemon do Docker."
    echo "Se você acabou de ser adicionado ao grupo 'docker', reabra a sessão SSH."
    exit 1
fi

if screen -ls 2>/dev/null | grep -q "\.${SESSAO}[[:space:]]"; then
    echo "ERRO: já existe uma sessão screen '$SESSAO'."
    echo "  Ver:      screen -r $SESSAO"
    echo "  Encerrar: docker stop $CONTAINER"
    exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "ERRO: já existe um container chamado '$CONTAINER'."
    echo "  Remover: docker rm -f $CONTAINER"
    exit 1
fi

# A credencial do Copilot expira em ~25-30min, mas o litellm a renova sozinho
# a partir do access-token. O que não dá para recuperar é a ausência do arquivo.
if [ ! -f "$HOME/.config/litellm/github_copilot/access-token" ]; then
    echo "ERRO: credencial do GitHub Copilot ausente."
    echo "Autentique antes com adk/scripts/copilot_auth.py (fluxo de device code)."
    exit 1
fi

# --- Arquiva a rodada anterior (rodada completa apaga o results.json) --------

if [ "$RESUME" -eq 0 ] && [ -d "$SAIDA" ]; then
    ARQUIVO="$HOME/benchmark-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
    echo "Arquivando rodada anterior em $ARQUIVO"
    tar -czf "$ARQUIVO" -C "$REPO/docs/Time_2_Design/analise-qualitativa" \
        outputs "$(basename "$RELATORIO")" 2>/dev/null || true
    # Limpa para que nenhum .md órfão de uma execução antiga seja confundido
    # com resultado desta rodada, caso algum par falhe agora.
    rm -rf "$SAIDA" "$RELATORIO"
    echo "Saídas anteriores removidas (recuperáveis pelo tar acima)."
fi

# --- Dispara -----------------------------------------------------------------

echo "Sessão screen: $SESSAO"
echo "Log:           $LOG"
echo

screen -dmS "$SESSAO" bash -c "
docker run --rm --name '$CONTAINER' \
    -e PYTHONUNBUFFERED=1 \
    -u \"\$(id -u):\$(id -g)\" \
    -e HOME=/tmp \
    -e UV_CACHE_DIR=/cache \
    -e UV_PYTHON_INSTALL_DIR=/cache/python \
    -e UV_PROJECT_ENVIRONMENT=/venvs/adk \
    -v '$REPO':/repo -w /repo \
    -v \"\$HOME/.cache/ai4es-uv\":/cache \
    -v \"\$HOME/.local/share/ai4es-venv\":/venvs \
    -v \"\$HOME/.config/litellm\":/tmp/.config/litellm \
    '$IMAGEM' \
    uv run --project adk python benchmark_gemini_copilot.py $* 2>&1 | tee '$LOG'
"

sleep 3
if screen -ls 2>/dev/null | grep -q "\.${SESSAO}[[:space:]]"; then
    echo "Rodando. A conexão SSH pode ser fechada."
    echo
    echo "  Acompanhar:  tail -f $LOG"
    echo "  Progresso:   ls $SAIDA/*.md 2>/dev/null | wc -l"
    echo "  Reanexar:    screen -r $SESSAO      (sair sem matar: Ctrl+A depois D)"
    echo "  Abortar:     docker stop $CONTAINER"
else
    echo "AVISO: a sessão encerrou em menos de 3s — algo falhou na largada."
    echo "Veja o log: $LOG"
    exit 1
fi
