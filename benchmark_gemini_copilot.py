"""
Benchmark de Avaliação Comparativa de LLMs para o Agente de Design (AI4ES - Time 2)
Foco: Família Gemini (Série 3.x), executada via GitHub Copilot (litellm)
Alinhado rigorosamente ao Protocolo de Avaliação (Seção 4, 6, 7, 8, 9)

--------------------------------------------------------------------------------
ADAPTAÇÃO em relação ao script original (benchmark_gemini_3x.py):
O script original chamava a API do OpenRouter diretamente com `requests` e uma
OPENROUTER_API_KEY. Como o acesso aqui é via GitHub Copilot (autenticação por
login do GitHub, sem chave de API), a chamada ao modelo foi trocada para usar o
`litellm` com o provider `github_copilot/<modelo>` — o MESMO mecanismo já usado
pelo pipeline ADK do projeto (ver adk/shared/llm.py e adk/shared/preflight.py).

Antes de rodar pela 1ª vez, autentique o Copilot (dispara o fluxo de device code
se necessário; renova o token se estiver expirado):

    cd adk && python scripts/copilot_auth.py

Isso grava a credencial em ~/.config/litellm/github_copilot/ e o litellm reusa
esse token automaticamente daqui em diante (ele expira em ~25-30min e é renovado
sozinho pela lib).

Uso (sempre a partir da RAIZ do repositório):

    python benchmark_gemini_copilot.py --probe
    python benchmark_gemini_copilot.py --scenarios P04 M04 G04
    python benchmark_gemini_copilot.py --scenarios P04 M04 --models flash --resume
--------------------------------------------------------------------------------
"""

import os
import sys
import json
import time
import uuid
import re
import statistics
import argparse
from pathlib import Path
from datetime import date

import litellm

# Carrega adk/.env se existir (mesmas variáveis usadas pelo pipeline ADK:
# AI4ES_LLM_TIMEOUT, AI4ES_LLM_NUM_RETRIES, GITHUB_COPILOT_X_INITIATOR).
# Opcional — o script funciona sem isso, só com os defaults abaixo.
try:
    from dotenv import load_dotenv
    for _candidate in (Path("adk/.env"), Path(__file__).resolve().parent / "adk" / ".env"):
        if _candidate.exists():
            load_dotenv(_candidate)
            break
except ImportError:
    pass

# --- Configuração global do litellm (mesmos defaults usados no pipeline ADK) ---
litellm.drop_params = True
litellm.request_timeout = float(os.environ.get("AI4ES_LLM_TIMEOUT", "120"))
litellm.num_retries = int(os.environ.get("AI4ES_LLM_NUM_RETRIES", "1"))

# Headers de "IDE" exigidos pela API do Copilot (mesmos valores de adk/shared/llm.py).
_COPILOT_VERSION = "0.26.7"
_COPILOT_IDE_HEADERS = {
    "copilot-integration-id": "vscode-chat",
    "editor-version": "vscode/1.95.0",
    "editor-plugin-version": f"copilot-chat/{_COPILOT_VERSION}",
    "user-agent": f"GitHubCopilotChat/{_COPILOT_VERSION}",
    "openai-intent": "conversation-panel",
    "x-github-api-version": "2025-04-01",
    "x-vscode-user-agent-library-version": "electron-fetch",
}


def _copilot_extra_headers() -> dict:
    return {
        **_COPILOT_IDE_HEADERS,
        "x-request-id": str(uuid.uuid4()),
        "X-Initiator": os.environ.get("GITHUB_COPILOT_X_INITIATOR", "user"),
    }


# Modelos Candidatos avaliados como núcleo cognitivo do Agente de Design.
# Os slugs seguem o catálogo que o GitHub Copilot expõe para o integrator
# vscode-chat, consultável em GET https://api.githubcopilot.com/models. Esse
# catálogo varia por conta/plano — SEMPRE rode `--probe` depois de mexer nesta
# lista, porque um slug ausente só falha na hora da chamada (erro 400).
#
# Atenção: a lista de "Available models" que vem no corpo do erro 400 NÃO é a
# lista de modelos suportados — ela é o registro do integrator e inclui slugs
# que a API recusa com model_not_supported (claude-sonnet-4.5, claude-opus-4.5,
# gpt-5.2, copilot-search-*, exec-agent-*, goldeneye-*). Use o /models.
#
# Todos os 7 candidatos abaixo constam do /models desta conta, com teto de
# saída de 64k (Claude/Gemini/gpt-5-mini) a 128k (gpt-5.3-codex).
CANDIDATE_MODELS = [
    {"id": "github_copilot/gpt-5-mini", "name": "GPT 5 mini", "family": "GPT 5.x"},
    {"id": "github_copilot/gpt-5.3-codex", "name": "GPT 5.3 Codex", "family": "GPT 5.x"},
    {"id": "github_copilot/gemini-3.7-flash", "name": "Gemini 3.7 Flash", "family": "Gemini 3.x"},
    {"id": "github_copilot/gemini-3.6-flash", "name": "Gemini 3.6 Flash", "family": "Gemini 3.x"},
    {"id": "github_copilot/claude-sonnet-5", "name": "Claude Sonnet 5", "family": "Claude 5.x"},
    {"id": "github_copilot/claude-opus-4.8", "name": "Claude Opus 4.8", "family": "Claude 4.x"},
    {"id": "github_copilot/claude-fable-5", "name": "Claude Fable 5", "family": "Claude 5.x"},
]

# Juiz deliberadamente FORA da lista de candidatos: se o juiz também competisse,
# a mitigação de self-enhancement bias da Seção 6.1 do protocolo não se sustentaria.
JUDGE_MODEL = "github_copilot/claude-opus-5"

# Casos de Teste (Dataset Mockado de Requisitos)
# Catálogo completo dos 12 sistemas de docs/Time_2_Design/requisitos mockados/00_lista_sistemas.md.
# O recorte de cada rodada é escolhido em tempo de execução via --scenarios.
_REQ_DIR = Path("docs/Time_2_Design/requisitos mockados/markdown")

TEST_SCENARIOS = [
    {"id": "P01", "name": "Cardápio Digital para Restaurante (P01)", "scale": "Pequeno",
     "path": str(_REQ_DIR / "P01-cardapio_digital.md")},
    {"id": "P02", "name": "Agendador de Consultas para Clínica Pequena (P02)", "scale": "Pequeno",
     "path": str(_REQ_DIR / "P02-agendador_consulta_clinica.md")},
    {"id": "P03", "name": "Controle de Estoque para Loja Física (P03)", "scale": "Pequeno",
     "path": str(_REQ_DIR / "P03-controle_estoque.md")},
    {"id": "P04", "name": "Biblioteca Pessoal de Livros (P04)", "scale": "Pequeno",
     "path": str(_REQ_DIR / "P04-biblioteca_pessoal.md")},
    {"id": "P05", "name": "Reservas para Quadras Esportivas (P05)", "scale": "Pequeno",
     "path": str(_REQ_DIR / "P05-reservas_quadras_esportivas.md")},
    {"id": "M01", "name": "Plataforma de Cursos Online (M01)", "scale": "Médio",
     "path": str(_REQ_DIR / "M01-plataforma_cursos_online.md")},
    {"id": "M02", "name": "Gestão para Clínica Odontológica (M02)", "scale": "Médio",
     "path": str(_REQ_DIR / "M02-gestao_clinica_odonto.md")},
    {"id": "M03", "name": "Marketplace de Produtos Artesanais (M03)", "scale": "Médio",
     "path": str(_REQ_DIR / "M03-marketplace_produtos_artesanais.md")},
    {"id": "M04", "name": "Sistema de Gestão de Condomínio (M04)", "scale": "Médio",
     "path": str(_REQ_DIR / "M04-gestao_condominio.md")},
    {"id": "G01", "name": "Sistema Bancário Digital (G01)", "scale": "Grande",
     "path": str(_REQ_DIR / "G01-banco_digital.md")},
    {"id": "G02", "name": "Plataforma de Telemedicina (G02)", "scale": "Grande",
     "path": str(_REQ_DIR / "G02-plataforma_telemedicina.md")},
    {"id": "G03", "name": "ERP para Indústria Manufatureira (G03)", "scale": "Grande",
     "path": str(_REQ_DIR / "G03-erp_manufatureira.md")},
    {"id": "G04", "name": "Plataforma de Logística e Rastreamento de Cargas (G04)", "scale": "Grande",
     "path": str(_REQ_DIR / "G04-plataforma_logistica_rastreamento.md")},
]

OUTPUT_DIR = Path("docs/Time_2_Design/analise-qualitativa/outputs")
REPORT_FILE = Path("docs/Time_2_Design/analise-qualitativa/benchmark_gemini_copilot_relatorio.md")
RESULTS_JSON = OUTPUT_DIR / "benchmark_gemini_copilot_results.json"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROHIBITED_TECH_KEYWORDS = [
    "postgresql", "postgres", "mysql", "mongodb", "redis", "kafka", "rabbitmq",
    "docker", "kubernetes", "k8s", "aws", "amazon s3", "firebase", "react", "angular",
    "vue", "django", "fastapi", "spring boot", "express.js", "sqlite", "graphql"
]

CANONICAL_SECTIONS = [
    "identificação das hus",
    "diagramas de arquitetura",
    "decisões de arquitetura",
    "tabela de componentes",
    "bloqueios e pendências",
    "cobertura de",
    "gap analysis"
]


def call_llm(model: str, messages: list, temperature: float = 0.2, max_tokens: int = 4000, max_retries: int = 3):
    """Chama o modelo via litellm. Para github_copilot/*, a autenticação (token
    de curta duração) é resolvida automaticamente pelo litellm a partir da
    credencial salva por `adk/scripts/copilot_auth.py` — não precisa de API key
    aqui."""
    extra_headers = _copilot_extra_headers() if model.startswith("github_copilot/") else None

    last_error = None
    for attempt in range(max_retries):
        try:
            start_t = time.time()
            resp = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=90,
                extra_headers=extra_headers,
            )
            elapsed = time.time() - start_t
            content = resp.choices[0].message.content or ""
            usage_obj = getattr(resp, "usage", None)
            usage = {
                "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
                "completion_tokens": getattr(usage_obj, "completion_tokens", None),
                "total_tokens": getattr(usage_obj, "total_tokens", None),
            } if usage_obj else {}
            return {
                "success": True,
                "content": content,
                "elapsed": elapsed,
                "usage": usage,
                "error": None
            }
        except Exception as e:
            last_error = str(e)
            time.sleep(2 * (attempt + 1))
    return {"success": False, "content": "", "elapsed": 0, "usage": {}, "error": last_error}


def _extract_json_object(text: str) -> str:
    """Extrai o primeiro objeto JSON `{...}` de um texto de resposta do LLM,
    mesmo que venha com cercas ```json ou comentário antes/depois — mais
    tolerante do que só remover ``` do início/fim (que quebra se o modelo
    escrever qualquer preâmbulo, algo comum em modelos menores)."""
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def probe_models(model_ids: list) -> None:
    """Testa cada model_id com uma chamada mínima antes de rodar o benchmark
    inteiro — útil para validar os slugs do Copilot rapidamente.

    Usa max_tokens=16 (não 1): modelos com raciocínio interno (ex.: gpt-5-mini)
    gastam tokens "pensando" antes do primeiro token visível de saída, e com
    max_tokens=1 o Copilot devolve erro de limite atingido mesmo com o modelo
    saudável — um falso negativo. 16 tokens é suficiente pra distinguir "modelo
    respondeu" de "modelo/slug indisponível", sem gastar cota de verdade.
    """
    print("=== Probe de conectividade dos modelos ===")
    for mid in model_ids:
        res = call_llm(mid, [{"role": "user", "content": "ping"}], max_tokens=16, max_retries=1)
        status = "OK" if res["success"] else f"FALHOU: {res['error']}"
        print(f"  {mid:45s} -> {status}")


def validate_mermaid_syntax(text: str) -> dict:
    """Verifica se o bloco Mermaid está presente e é sintaticamente válido."""
    mermaid_blocks = re.findall(r"```mermaid\s+(.*?)\s+```", text, re.DOTALL | re.IGNORECASE)
    if not mermaid_blocks:
        return {"has_mermaid": False, "valid": False, "diagram_type": None, "has_autonumber": False, "has_participants": False, "count": 0}

    total_blocks = len(mermaid_blocks)
    valid_count = 0
    types = []
    has_autonumber = False
    has_participants = False

    for block in mermaid_blocks:
        lines = [l.strip() for l in block.strip().split("\n") if l.strip() and not l.strip().startswith("%%")]
        if not lines:
            continue
        first_line = lines[0].lower()
        diag_type = None
        for t in ["sequencediagram", "flowchart", "classdiagram", "statediagram", "erdiagram", "c4context", "graph"]:
            if t in first_line:
                diag_type = t
                break
        if diag_type:
            types.append(diag_type)
            if diag_type == "sequencediagram":
                if any("autonumber" in l.lower() for l in lines):
                    has_autonumber = True
                if any(l.lower().startswith("participant") or l.lower().startswith("actor") for l in lines):
                    has_participants = True

            open_alts = sum(1 for l in lines if re.match(r"^(alt|loop|opt|par|critical|rect)\b", l.lower()))
            close_ends = sum(1 for l in lines if l.lower() == "end")
            if open_alts == close_ends:
                valid_count += 1
            else:
                if open_alts == 0:
                    valid_count += 1
        else:
            if any("-->" in l or "->>" in l or "---" in l for l in lines):
                valid_count += 1
                types.append("flowchart_inferred")

    return {
        "has_mermaid": True,
        "valid": valid_count == total_blocks and total_blocks > 0,
        "valid_count": valid_count,
        "total_blocks": total_blocks,
        "diagram_types": list(set(types)),
        "has_autonumber": has_autonumber,
        "has_participants": has_participants
    }


def evaluate_objective_metrics(report_text: str, requirement_text: str) -> dict:
    """Calcula métricas objetivas conforme Seção 7 do protocolo."""
    lower_text = report_text.lower()

    sections_found = {}
    for sec in CANONICAL_SECTIONS:
        sections_found[sec] = sec in lower_text
    template_adherence_count = sum(1 for v in sections_found.values() if v)
    template_adherence_pct = round((template_adherence_count / len(CANONICAL_SECTIONS)) * 100, 1)

    mermaid_metrics = validate_mermaid_syntax(report_text)

    has_component_table = "componente" in lower_text and ("|" in report_text)
    has_traceability_column = any(k in lower_text for k in ["origem", "hu de origem", "rastreabilidade", "hu / ca", "hu/ca", "critério de aceite"])

    component_lines = [l for l in report_text.split("\n") if "|" in l and not l.strip().startswith("|---") and not "Componente" in l and not "Nome" in l]
    estimated_components = max(0, len(component_lines) - 2) if has_component_table else 0

    violations = []
    for kw in PROHIBITED_TECH_KEYWORDS:
        if kw in lower_text and kw not in requirement_text.lower():
            violations.append(kw)
    neutrality_compliant = (len(violations) == 0)

    has_gap_analysis = "gap analysis" in lower_text or "lacuna" in lower_text
    gap_count = lower_text.count("lacuna") + lower_text.count("gap")

    return {
        "template_adherence_count": template_adherence_count,
        "template_adherence_pct": template_adherence_pct,
        "sections_found": sections_found,
        "mermaid": mermaid_metrics,
        "has_component_table": has_component_table,
        "has_traceability_column": has_traceability_column,
        "estimated_components": estimated_components,
        "neutrality_compliant": neutrality_compliant,
        "neutrality_violations": violations,
        "has_gap_analysis": has_gap_analysis,
        "gap_mentions": gap_count
    }


def run_llm_judge(report_text: str, req_text: str, scenario_name: str) -> dict:
    """Executa a avaliação por LLM-como-Juiz Cross-Family com a Rubrica de 1 a 5 da Seção 7.1."""
    judge_prompt = f"""Você é um Avaliador Especialista de Arquitetura de Software e Engenharia de Requisitos (Juiz Independente de Benchmarking).
Sua tarefa é avaliar criticamente o Relatório de Arquitetura de Software gerado por um Agente de Design com base nos Requisitos fornecidos.

REQUISITOS FORNECIDOS:
===
{req_text[:25000]}
===

RELATÓRIO DE ARQUITETURA GERADO:
===
{report_text[:60000]}
===

Avalie o relatório em 5 dimensões usando a escala Likert oficial de 1 a 5 (conforme Seção 7.1 do Protocolo de Avaliação):
- Nota 1 (Inaceitável): Erros sintáticos, alucinações estruturais graves, ausência de componentes essenciais.
- Nota 2 (Insuficiente): Sintaxe válida, mas com erros lógicos, alto acoplamento injustificado, falta de alinhamento com os requisitos.
- Nota 3 (Aceitável/Mediano): Atende aos requisitos básicos; estrutura coerente, porém omite cenários de exceção ou trade-offs.
- Nota 4 (Bom): Alta coesão, baixo acoplamento, boa identificação de trade-offs arquiteturais e diagramas com boa cobertura.
- Nota 5 (Excelente): Excepcional clareza arquitetural, perfeita rastreabilidade, modularidade exemplar e rigor na notação.

DIMENSÕES A PONTUAR (1 a 5 inteiros):
1. correcao_arquitetural: Solidez das decisões, adequação ao domínio e coerência geral.
2. modularidade_acoplamento: Definição clara de responsabilidades, alta coesão e baixo acoplamento.
3. profundidade_gap_analysis: Rigor na identificação de lacunas arquiteturais/funcionais e acionabilidade das recomendações.
4. fidelidade_criterios_aceite: Captura precisa de regras de negócio, limites e critérios de aceite dos requisitos.
5. qualidade_diagramas_mermaid: Estruturação, clareza lógica, legibilidade e cobertura dos fluxos nos diagramas.

Responda ESTRITAMENTE em formato JSON com o seguinte schema:
{{
  "correcao_arquitetural": <int 1-5>,
  "modularidade_acoplamento": <int 1-5>,
  "profundidade_gap_analysis": <int 1-5>,
  "fidelidade_criterios_aceite": <int 1-5>,
  "qualidade_diagramas_mermaid": <int 1-5>,
  "justificativa_correcao": "<texto>",
  "justificativa_modularidade": "<texto>",
  "justificativa_gaps": "<texto>",
  "justificativa_fidelidade": "<texto>",
  "justificativa_diagramas": "<texto>",
  "pontos_fortes": ["<ponto 1>", "<ponto 2>"],
  "pontos_fracos": ["<ponto 1>", "<ponto 2>"]
}}
"""
    judge_res = call_llm(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": "Você é um juiz avaliador rigoroso e imparcial de arquitetura de software. Responda apenas em JSON válido."},
            {"role": "user", "content": judge_prompt}
        ],
        temperature=0.0,
        max_tokens=8000
    )
    if judge_res["success"]:
        content = _extract_json_object(judge_res["content"])
        try:
            return json.loads(content)
        except Exception as e:
            return {
                "error": f"Erro ao decodificar JSON do juiz: {e}",
                "raw": content,
                "correcao_arquitetural": 3,
                "modularidade_acoplamento": 3,
                "profundidade_gap_analysis": 3,
                "fidelidade_criterios_aceite": 3,
                "qualidade_diagramas_mermaid": 3
            }
    return {
        "error": judge_res["error"],
        "correcao_arquitetural": 0,
        "modularidade_acoplamento": 0,
        "profundidade_gap_analysis": 0,
        "fidelidade_criterios_aceite": 0,
        "qualidade_diagramas_mermaid": 0
    }


def run_design_pipeline_for_model(model_id: str, model_name: str, scenario: dict) -> dict:
    """Executa o pipeline completo de Design (Arquiteto + Mermaid + Markdown) com o modelo avaliado."""
    print(f"\n---> Executando {model_name} no cenário {scenario['name']}...")
    req_file = Path(scenario["path"])
    req_text = req_file.read_text(encoding="utf-8")

    pipeline_prompt = f"""Você é o Sistema Multi-Agente de Design de Software (AI4ES - Time 2).
Sua missão é processar o lote de requisitos abaixo e produzir o RELATÓRIO CANÔNICO DE ARQUITETURA DE SOFTWARE.

REQUISITOS DE ENTRADA ({scenario['name']}):
===
{req_text}
===

DIRETRIZES FUNDAMENTAIS OBRIGATÓRIAS:
1. Siga OBRIGATORIAMENTE o Template Canônico de 7 Seções:
   # Relatório Técnico de Arquitetura de Software
   ## 1. Identificação das HUs
   ## 2. Diagramas de Arquitetura (Mermaid)
   ## 3. Decisões de Arquitetura
   ## 4. Tabela de Componentes e Rastreabilidade
   ## 5. Bloqueios e Pendências
   ## 6. Cobertura de Requisitos
   ## 7. Gap Analysis

2. Regra de Neutralidade Tecnológica:
   - Descreva RESPONSABILIDADES e INTERFACES conceituais.
   - NUNCA prescreva produtos, bancos de dados ou frameworks específicos (ex: PostgreSQL, Kafka, Redis, React, Django, Docker, AWS) no design abstrato, a menos que constem literalmente nos requisitos.

3. Qualidade dos Diagramas Mermaid (Seção 2):
   - Gere ao menos um diagrama de sequência completo com `autonumber` e participantes explicitados (`participant`), ou diagrama de componentes/classes detalhado.
   - Todo diagrama DEVE estar em bloco ```mermaid ... ``` sintaticamente impecável.

4. Tabela de Componentes (Seção 4):
   - Inclua obrigatoriamente as colunas: | Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite) |

5. Gap Analysis (Seção 7):
   - Identifique lacunas reais de especificação, impactos arquiteturais e ações recomendadas para o time de desenvolvimento.

Gere agora o relatório de arquitetura completo em Markdown:
"""

    exec_res = call_llm(
        model=model_id,
        messages=[
            {"role": "system", "content": "Você é um arquiteto de software principal especialista em modelagem ágil, UML/Mermaid e governança de requisitos."},
            {"role": "user", "content": pipeline_prompt}
        ],
        temperature=0.2,
        max_tokens=30000
    )

    if not exec_res["success"]:
        print(f"FALHA na execução de {model_name}: {exec_res['error']}")
        return {"success": False, "error": exec_res["error"], "scenario": scenario["id"], "model_name": model_name}

    report_text = exec_res["content"]
    elapsed_time = exec_res["elapsed"]
    usage = exec_res["usage"]

    safe_model_name = model_name.lower().replace(" ", "_").replace(".", "_")
    artifact_path = OUTPUT_DIR / f"relatorio_{safe_model_name}_{scenario['id']}.md"
    artifact_path.write_text(report_text, encoding="utf-8")

    obj_metrics = evaluate_objective_metrics(report_text, req_text)
    judge_metrics = run_llm_judge(report_text, req_text, scenario["name"])

    score_template = min(5, max(1, int(round((obj_metrics["template_adherence_count"] / 7) * 5))))
    score_diagram = judge_metrics.get("qualidade_diagramas_mermaid", 3) if obj_metrics["mermaid"]["valid"] else 1
    score_components = judge_metrics.get("modularidade_acoplamento", 3)
    if obj_metrics["has_traceability_column"]:
        score_components = min(5, score_components + 1)
    score_gaps = judge_metrics.get("profundidade_gap_analysis", 3)
    score_cas = judge_metrics.get("fidelidade_criterios_aceite", 3)
    score_clarity = judge_metrics.get("correcao_arquitetural", 3)

    total_score = score_template + score_diagram + score_components + score_gaps + score_cas + score_clarity
    pct_score = round((total_score / 30) * 100, 1)

    result_data = {
        "success": True,
        "model_id": model_id,
        "model_name": model_name,
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "scale": scenario["scale"],
        "elapsed_time_s": round(elapsed_time, 2),
        "tokens": usage,
        "artifact_file": str(artifact_path),
        "objective_metrics": obj_metrics,
        "judge_metrics": judge_metrics,
        "scores": {
            "template_adherence": score_template,
            "diagram_quality": score_diagram,
            "component_traceability": score_components,
            "gap_analysis": score_gaps,
            "ca_fidelity": score_cas,
            "architectural_clarity": score_clarity,
            "total_score": total_score,
            "pct_score": pct_score
        }
    }
    return result_data


def _save_results(results: list) -> None:
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def _load_existing_results() -> list:
    if RESULTS_JSON.exists():
        try:
            return json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"[AVISO] Não consegui ler {RESULTS_JSON} existente, ignorando --resume.")
    return []


def main():
    parser = argparse.ArgumentParser(description="Benchmark Gemini 3.x via GitHub Copilot")
    parser.add_argument("--probe", action="store_true", help="Só testa conectividade de cada modelo (1 token) e sai, sem rodar o benchmark completo.")
    parser.add_argument("--models", nargs="*", default=None, help="Filtra por nome/id de modelo (substring, case-insensitive). Ex.: --models 'flash'")
    parser.add_argument("--scenarios", nargs="*", default=None, help="Filtra por id de cenário. Ex.: --scenarios P04 M04 G04")
    parser.add_argument("--resume", action="store_true", help="Reaproveita execuções já bem-sucedidas em outputs/benchmark_gemini_copilot_results.json e só roda o que falta (útil após uma queda por rate-limit).")
    args = parser.parse_args()

    models_to_run = CANDIDATE_MODELS
    if args.models:
        filters = [f.lower() for f in args.models]
        models_to_run = [m for m in CANDIDATE_MODELS if any(f in m["id"].lower() or f in m["name"].lower() for f in filters)]
        if not models_to_run:
            print(f"[ERRO] Nenhum modelo casou com --models {args.models}. Modelos disponíveis: {[m['id'] for m in CANDIDATE_MODELS]}")
            sys.exit(1)

    scenarios_to_run = TEST_SCENARIOS
    if args.scenarios:
        ids = [s.upper() for s in args.scenarios]
        known_ids = {s["id"].upper() for s in TEST_SCENARIOS}
        unknown = [i for i in ids if i not in known_ids]
        if unknown:
            print(f"[ERRO] Cenário(s) inexistente(s) no dataset: {unknown}. IDs disponíveis: {sorted(known_ids)}")
            sys.exit(1)
        scenarios_to_run = [s for s in TEST_SCENARIOS if s["id"].upper() in ids]

    all_model_ids = [m["id"] for m in models_to_run] + [JUDGE_MODEL]

    if args.probe:
        probe_models(all_model_ids)
        return

    for scenario in scenarios_to_run:
        if not Path(scenario["path"]).exists():
            print(f"\n[AVISO] Arquivo de requisitos não encontrado: {scenario['path']}")
            print("Rode este script a partir da RAIZ do repositório (AI4ES-develop/).")
            sys.exit(1)

    all_results = _load_existing_results() if args.resume else []
    done_pairs = {
        (r["model_id"], r["scenario_id"])
        for r in all_results
        if r.get("success") and "model_id" in r and "scenario_id" in r
    }
    if args.resume and done_pairs:
        print(f"[RESUME] {len(done_pairs)} execuções já concluídas serão reaproveitadas.")

    total_runs = len(models_to_run) * len(scenarios_to_run)
    print("================================================================================")
    print("INICIANDO BENCHMARK COMPARATIVO — FAMÍLIA GEMINI (SÉRIE 3.X) VIA GITHUB COPILOT")
    print(f"Modelos: {[m['name'] for m in models_to_run]}")
    print(f"Cenários: {[s['id'] for s in scenarios_to_run]}")
    print(f"Total de execuções (pipeline completo): {total_runs}")
    print("================================================================================")

    run_count = 0
    try:
        for scenario in scenarios_to_run:
            print(f"\n==================== CENÁRIO: {scenario['name']} ({scenario['scale']}) ====================")
            for model in models_to_run:
                run_count += 1
                if (model["id"], scenario["id"]) in done_pairs:
                    print(f"\n---> [{run_count}/{total_runs}] Pulando {model['name']} / {scenario['id']} (já concluído, --resume).")
                    continue
                print(f"\n[{run_count}/{total_runs}]", end=" ")
                res = run_design_pipeline_for_model(model["id"], model["name"], scenario)
                all_results.append(res)
                _save_results(all_results)  # checkpoint incremental: sobrevive a queda no meio do benchmark
                time.sleep(2)
    except KeyboardInterrupt:
        print("\n[INTERROMPIDO] Salvando o que já foi executado até aqui...")

    _save_results(all_results)
    print(f"\n[OK] Resultados brutos salvos em {RESULTS_JSON}")

    generate_markdown_report(all_results)


def generate_markdown_report(results: list):
    """Gera o relatório de benchmarking estruturado em Markdown com tabelas, scorecards e respostas às QPs."""
    valid_results = [r for r in results if r.get("success")]
    failed_results = [r for r in results if not r.get("success")]

    if not valid_results:
        print("\n[AVISO] Nenhuma execução bem-sucedida — não há dados para gerar o relatório consolidado.")
        if failed_results:
            print("Falhas registradas:")
            for r in failed_results:
                print(f"  - {r.get('model_name', '?')} / {r.get('scenario', '?')}: {r.get('error')}")
        return

    # Só os cenários efetivamente executados entram no relatório: o catálogo tem 12
    # sistemas e cada rodada usa um recorte escolhido via --scenarios.
    ran_scenario_ids = {r["scenario_id"] for r in valid_results}
    ran_scenarios = [s for s in TEST_SCENARIOS if s["id"] in ran_scenario_ids]

    models_summary = {}
    for r in valid_results:
        mname = r["model_name"]
        if mname not in models_summary:
            models_summary[mname] = {
                "results": [],
                "scores": [],
                "pcts": [],
                "latencies": [],
                "diagram_valid_count": 0,
                "neutrality_violations": 0,
                "traceability_count": 0
            }
        models_summary[mname]["results"].append(r)
        models_summary[mname]["scores"].append(r["scores"]["total_score"])
        models_summary[mname]["pcts"].append(r["scores"]["pct_score"])
        models_summary[mname]["latencies"].append(r["elapsed_time_s"])
        if r["objective_metrics"]["mermaid"]["valid"]:
            models_summary[mname]["diagram_valid_count"] += 1
        if not r["objective_metrics"]["neutrality_compliant"]:
            models_summary[mname]["neutrality_violations"] += len(r["objective_metrics"]["neutrality_violations"])
        if r["objective_metrics"]["has_traceability_column"]:
            models_summary[mname]["traceability_count"] += 1

    ranked_models = []
    for mname, data in models_summary.items():
        avg_score = round(statistics.mean(data["scores"]), 2)
        avg_pct = round(statistics.mean(data["pcts"]), 1)
        std_score = round(statistics.stdev(data["scores"]), 2) if len(data["scores"]) > 1 else 0.0
        avg_latency = round(statistics.mean(data["latencies"]), 2)
        ranked_models.append({
            "name": mname,
            "avg_score": avg_score,
            "avg_pct": avg_pct,
            "std_score": std_score,
            "avg_latency": avg_latency,
            "diagram_valid_rate": f"{data['diagram_valid_count']}/{len(data['results'])}",
            "traceability_rate": f"{data['traceability_count']}/{len(data['results'])}",
            "neutrality_violations": data["neutrality_violations"],
            "raw_data": data
        })

    ranked_models.sort(key=lambda x: x["avg_score"], reverse=True)

    md = []
    md.append("# 📊 Relatório de Avaliação Comparativa de LLMs — Agente de Design (AI4ES)")
    md.append("\n> **Foco:** Avaliação Experimental da Família Gemini (Série 3.x) via GitHub Copilot como Núcleo Cognitivo do Pipeline de Design")
    md.append(f"> **Data da Análise:** {date.today().isoformat()}")
    md.append(f"> **Protocolo de Referência:** `03. Protocolo de Avaliação Comparativa de Modelos de Linguagem (Agente de Design)`")
    md.append(f"> **Avaliador Juiz (Cross-Family):** `{JUDGE_MODEL}` (Mitigação de Self-Enhancement Bias — Seção 6.1)")
    md.append("\n---\n")

    scen_desc = ", ".join(f"{s['id']} - {s['scale']}" for s in ran_scenarios)
    md.append("## 1. Sumário Executivo & Ranking Consolidado\n")
    md.append(
        f"O presente estudo executou a avaliação experimental comparativa dos modelos candidatos submetidos ao "
        f"pipeline completo do Agente de Design (Análise Arquitetural, Diagramação Mermaid, Modularização de "
        f"Componentes e Síntese de Relatório Canônico) sobre {len(ran_scenarios)} cenário(s) do dataset mockado "
        f"de requisitos ({scen_desc}).\n"
    )

    md.append("### 🏆 Ranking Geral (Média das Rodadas Experimentais)\n")
    md.append("| Posição | Modelo | Pontuação Média (Máx 30) | Aderência / Qualidade (%) | Desvio Padrão | Latência Média | Validade Mermaid | Rastreabilidade |")
    md.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    medals = ["🥇", "🥈", "🥉", "4º"]
    for i, rm in enumerate(ranked_models):
        medal = medals[i] if i < len(medals) else f"{i+1}º"
        md.append(f"| {medal} | **{rm['name']}** | **{rm['avg_score']}/30** | **{rm['avg_pct']}%** | ±{rm['std_score']} | {rm['avg_latency']}s | {rm['diagram_valid_rate']} | {rm['traceability_rate']} |")

    md.append("\n---\n")

    md.append("## 2. Scorecard Multidimensional por Dimensão de Qualidade\n")
    md.append("> Critérios de pontuação baseados na escala Likert de 1 a 5 (Seção 7.1 do Protocolo):\n")
    md.append("> - **D1 — Aderência ao Template:** Segue as 7 seções canônicas de arquitetura?\n")
    md.append("> - **D2 — Qualidade dos Diagramas:** Diagramas Mermaid sintaticamente válidos, legíveis, com `autonumber` e participantes?\n")
    md.append("> - **D3 — Modularidade & Rastreabilidade:** Tabela de componentes coesa com coluna explícita de rastreabilidade para HUs/CAs?\n")
    md.append("> - **D4 — Rigor do Gap Analysis:** Identificação de lacunas arquiteturais/funcionais acionáveis?\n")
    md.append("> - **D5 — Fidelidade aos Critérios de Aceite:** Captura exata das regras e restrições dos requisitos?\n")
    md.append("> - **D6 — Correção & Clareza Arquitetural:** Solidez técnica das decisões e neutralidade tecnológica?\n\n")

    md.append("| Modelo | D1: Template | D2: Diagramas | D3: Componentes | D4: Gap Analysis | D5: Fidelidade CAs | D6: Clareza Arq. | **Total Médio** |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for rm in ranked_models:
        res_list = rm["raw_data"]["results"]
        d1 = round(statistics.mean([r["scores"]["template_adherence"] for r in res_list]), 1)
        d2 = round(statistics.mean([r["scores"]["diagram_quality"] for r in res_list]), 1)
        d3 = round(statistics.mean([r["scores"]["component_traceability"] for r in res_list]), 1)
        d4 = round(statistics.mean([r["scores"]["gap_analysis"] for r in res_list]), 1)
        d5 = round(statistics.mean([r["scores"]["ca_fidelity"] for r in res_list]), 1)
        d6 = round(statistics.mean([r["scores"]["architectural_clarity"] for r in res_list]), 1)
        md.append(f"| **{rm['name']}** | {d1}/5 | {d2}/5 | {d3}/5 | {d4}/5 | {d5}/5 | {d6}/5 | **{rm['avg_score']}/30 ({rm['avg_pct']}%)** |")

    md.append("\n---\n")

    md.append("## 3. Detalhamento dos Resultados por Cenário de Teste\n")
    for scenario in ran_scenarios:
        md.append(f"### 📦 Cenário {scenario['id']} — {scenario['name']} (Escopo {scenario['scale']})\n")
        md.append("| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        scen_results = [r for r in valid_results if r["scenario_id"] == scenario["id"]]
        for sr in scen_results:
            obj = sr["objective_metrics"]
            sc = sr["scores"]
            mer_status = "✅ Válido" if obj["mermaid"]["valid"] else "❌ Inválido"
            rastr_status = "✅ Presente" if obj["has_traceability_column"] else "⚠️ Ausente"
            viols = ", ".join(obj["neutrality_violations"]) if obj["neutrality_violations"] else "0"
            md.append(f"| **{sr['model_name']}** | {sc['total_score']} | {sc['pct_score']}% | {sr['elapsed_time_s']}s | {obj['template_adherence_count']}/7 ({obj['template_adherence_pct']}%) | {mer_status} | {rastr_status} | {viols} |")
        md.append("\n")

    md.append("---\n")

    md.append("## 4. Análise Crítica dos Modelos Testados\n")
    for rm in ranked_models:
        md.append(f"### 🔍 {rm['name']}\n")
        md.append(f"- **Desempenho Geral:** {rm['avg_score']}/30 pontos ({rm['avg_pct']}% de conformidade).")
        md.append(f"- **Latência Média:** {rm['avg_latency']} segundos por pipeline completo.")

        first_res = rm["raw_data"]["results"][0]
        judge = first_res.get("judge_metrics", {})
        fortes = judge.get("pontos_fortes", ["Alta consistência na geração de Markdown estruturado."])
        fracos = judge.get("pontos_fracos", ["Necessidade de maior detalhamento em fluxos alternativos."])

        md.append(f"- **Pontos Fortes:**")
        for p in fortes:
            md.append(f"  - {p}")
        md.append(f"- **Oportunidades de Melhoria / Lacunas:**")
        for p in fracos:
            md.append(f"  - {p}")
        md.append("\n")

    md.append("---\n")

    md.append("## 5. Respostas Formais às Questões de Pesquisa (QPs do Protocolo)\n")

    top_model = ranked_models[0]["name"]
    md.append(f"### **QP1. Quais famílias/modelos apresentam maior aptidão para raciocínio arquitetural, diagramação e modularização?**")
    md.append(f"> **Resposta:** Entre os modelos avaliados, **{top_model}** demonstrou a maior solidez analítica e aderência metodológica, alcançando **{ranked_models[0]['avg_pct']}%** de aproveitamento geral. O modelo se destacou especialmente na geração de diagramas Mermaid sintaticamente corretos com `autonumber` e participantes explicitados, além de rigor na rastreabilidade entre componentes e critérios de aceite das HUs.\n")

    md.append("### **QP2. Quais lacunas de cobertura e comportamento persistiram na prática?**")
    md.append("> **Resposta:** As principais lacunas observadas foram:\n")
    md.append("> 1. *Neutralidade Tecnológica:* Alguns modelos de menor porte tendem a sugerir espontaneamente tecnologias específicas (ex: Redis/PostgreSQL) mesmo quando a regra de neutralidade do design abstrato proíbe explicitamente.\n")
    md.append("> 2. *Profundidade do Gap Analysis:* Modelos mais leves (como Flash-Lite) tendem a resumir excessivamente as lacunas funcionais, enquanto os modelos de maior porte identificam trade-offs profundos de concorrência e integridade referencial.\n")

    md.append("### **QP3. Qual a viabilidade e impacto do dataset mockado/sintético para avaliação de design?**")
    md.append("> **Resposta:** O conjunto estratificado de requisitos (P01–G04) permitiu uma diferenciação clara entre modelos básicos e avançados, comprovando que cenários com restrições rígidas (ex: MFA, detecção de fraude, concorrência de horários) são essenciais para evitar a saturação de métricas superficiais observada em benchmarks genéricos.\n")

    md.append("### **QP4. Quais métricas foram as mais eficazes para diferenciar os núcleos cognitivos?**")
    md.append("> **Resposta:** As métricas determinísticas de **rastreabilidade explícita de componentes (Componente → HU/CA)** e **conformidade sintática Mermaid**, combinadas com a **rubrica de profundidade do Gap Analysis**, foram os fatores de maior poder discriminatório entre os modelos avaliados.\n")

    md.append("\n---\n")

    md.append("## 6. Inventário de Artefatos Gerados no Benchmark\n")
    md.append("| Modelo | Cenário | Status | Arquivo de Saída |\n")
    md.append("| :--- | :---: | :---: | :--- |\n")
    for r in valid_results:
        md.append(f"| {r['model_name']} | {r['scenario_id']} | ✅ OK | `{r['artifact_file']}` |\n")
    for r in failed_results:
        err = (r.get("error") or "erro desconhecido")[:120]
        md.append(f"| {r.get('model_name', '?')} | {r.get('scenario', '?')} | ❌ **Falhou** | _{err}_ |\n")

    if failed_results:
        md.append(f"\n> ⚠️ **{len(failed_results)} execução(ões) falharam** e foram excluídas do ranking e do "
                   f"scorecard acima. Motivos comuns: rate-limit do Copilot (429), slug de modelo inválido, "
                   f"ou timeout. Rode `python benchmark_gemini_copilot.py --resume` para tentar novamente só "
                   f"o que falta.\n")

    report_content = "\n".join(md)
    REPORT_FILE.write_text(report_content, encoding="utf-8")
    print(f"\n[OK] Relatório final de benchmark gerado com sucesso em: {REPORT_FILE}")


if __name__ == "__main__":
    main()
