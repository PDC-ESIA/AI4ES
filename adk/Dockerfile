FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# ---------------------------------------------------------------------------
# Runtime Node + Chromium — exigido pelo QA de critérios de aceite (issue #394)
#
# O QA que roda DENTRO do loop coder ↔ executor comprova critérios navegando a
# aplicação com Playwright. Sem Node e sem browser aqui, `executar_playwright`
# devolve `bloqueado_infraestrutura`, o QA degrada para "não executou" e a
# verificação por navegação simplesmente não acontece em produção — em silêncio,
# porque a degradação é deliberadamente silenciosa (uma medida auxiliar
# indisponível não pode derrubar a rodada).
#
# Vem ANTES do `COPY . .` de propósito: o download do Chromium é a camada mais
# cara da imagem, e mudança de código-fonte não pode invalidá-la.
# ---------------------------------------------------------------------------
# `build-essential` não é para o Node: é para o `uv sync` mais abaixo. O projeto
# exige Python 3.14, e nem toda dependência publica wheel para cp314 ainda —
# `py-rust-stemmers`, por exemplo, compila via cargo e precisa de um linker `cc`,
# que a imagem slim não traz. Sem ele o build falha em "linker `cc` not found".
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y --auto-remove gnupg \
    && rm -rf /var/lib/apt/lists/*

# Fora de $HOME para não depender do usuário que roda o container. A variável é
# lida pelo Playwright e está na allowlist de env de `executar_playwright` — sem
# ela na allowlist, o processo Node não encontraria o browser.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# `package.json` fixa @playwright/test; `playwright.config.ts` é lido pelo runner
# a partir da raiz do projeto. Copiados isolados para preservar o cache de camada.
# O download do Chromium resolve nomes que respondem em IPv6, e um build sem
# egress IPv6 morre em `connect ENETUNREACH` depois de esgotar o timeout. Pedir
# ao Node que prefira IPv4 torna o build independente disso; onde há IPv6, nada
# muda.
ENV NODE_OPTIONS=--dns-result-order=ipv4first

COPY package.json playwright.config.ts ./
RUN npm install --no-save --package-lock=false --ignore-scripts \
    && npx --yes playwright install --with-deps chromium \
    && npm cache clean --force

# README.md entra junto porque `pyproject.toml` o declara em `readme = ...`, e o
# backend de build (hatchling) o LÊ ao resolver os metadados do próprio projeto.
# Sem ele, `uv sync` falha com "Readme file does not exist" — o build da imagem
# estava quebrado por isto antes desta mudança, e o job de CD junto.
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

COPY . .

EXPOSE 8081

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
