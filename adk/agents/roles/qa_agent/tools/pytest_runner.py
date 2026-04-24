import subprocess
import json
from pathlib import Path
import logging
import sys
from datetime import datetime, timezone

# Variáveis de controle de estado do agente
_contador_execucoes = {}
MAX_TENTATIVAS = 5

logger = logging.getLogger("qa_agent_tool")

def _gerar_doubt_artifact_sincrono(id_artefato: str, motivo: str, caminho_base: Path) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    doubt_dir = caminho_base.parent / "doubt_artifacts"
    doubt_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
    caminho = doubt_dir / nome_arquivo

    conteudo = f"""# Doubt Artifact — QA Agent
**ID do Artefato:** {id_artefato}
**Data/Hora:** {timestamp}
**Agente:** qa_agent
**Status:** BLOQUEADO — aguardando intervenção humana

---

## Descrição da Inconsistência ou Bloqueio
{motivo}

## Contexto
- Etapa onde o bloqueio ocorreu: Execução de testes (pytest_runner)
- Ação tomada: Execução interrompida via ERR_LOOP.

## O que é necessário para continuar
Revisão manual do teste ou do requisito (HU) gerado. O agente entrou em loop tentando corrigir o erro.
"""
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)

def gerar_teste_via_hu(hu_conteudo: str, caminho_destino: Path) -> dict:
    """Gera casos de teste pytest a partir de História de Usuário ou requisito funcional.

    Args:
        hu_conteudo: Conteúdo da história de usuário ou requisito funcional.
        caminho_destino: Path do arquivo onde o teste será gravado.

    Returns:
        dict: Dicionário com status da operação e caminho do arquivo gerado.
    """
    logger.info("[QA Subagent] Iniciando geração de teste baseado na HU...")
    
    # Exemplo de integração: Aqui o LLM do subagente processaria a HU e geraria o código.
    # llm_output = llm_chain.invoke({"hu": hu_conteudo})
    # caminho_destino.write_text(llm_output)
    
    return {
        "status": "sucesso",
        "acao": "geracao_teste",
        "arquivo_gerado": str(caminho_destino),
        "arquivo": str(caminho_destino)
    }

def _normalizar_caminho_arquivo(caminho_arquivo: str | dict) -> Path:
    """Normaliza caminho de arquivo aceitando string ou dicionário.

    Args:
        caminho_arquivo: String com o path ou dicionário contendo chaves como 'arquivo_gerado', 'arquivo', 'caminho_arquivo'.

    Returns:
        Path: Objeto Path normalizado.
    """
    if isinstance(caminho_arquivo, dict):
        caminho_arquivo = caminho_arquivo.get("arquivo_gerado") or caminho_arquivo.get("arquivo") or caminho_arquivo.get("caminho_arquivo")
    return Path(caminho_arquivo)

def executar_pytest_tool(caminho_arquivo: str | dict) -> dict:
    """Executa testes pytest em um arquivo específico com análise de cobertura.

    Args:
        caminho_arquivo: Path do arquivo de teste ou dicionário com o caminho.

    Returns:
        dict: Resultado estruturado com status, cobertura e erros (se houver).

    Raises:
        subprocess.TimeoutExpired: Se a execução ultrapassar 30 segundos.
    """
    caminho = _normalizar_caminho_arquivo(caminho_arquivo)
    dir_base = caminho.parent
    
    if not caminho.exists():
        return _gerar_erro_execucao("ERR_MODULO_NAO_ENCONTRADO", f"Arquivo {caminho} não existe.", caminho)

    nome_artefato = caminho.stem 
    tentativas = _contador_execucoes.get(str(caminho), 0) + 1
    _contador_execucoes[str(caminho)] = tentativas

    # Trava de Loop ReAct
    if tentativas > MAX_TENTATIVAS:
        logger.error(f"[QA Subagent] ERR_LOOP acionado para {nome_artefato}. Tentativas: {tentativas}")
        caminho_duvida = _gerar_doubt_artifact_sincrono(
            id_artefato=nome_artefato, 
            motivo=f"Tentou processar a tool {MAX_TENTATIVAS} vezes e continuou falhando.",
            caminho_base=caminho
        )
        return _gerar_erro_execucao(
            "ERR_LOOP", 
            f"Execução bloqueada. Doubt Artifact gerado em: {caminho_duvida}",
            caminho
        )

    arquivo_report_json = dir_base / 'report.json'
    arquivo_cov_json = dir_base / 'coverage.json'

    # Adicionando --cov-report=json para capturar a cobertura exata e cumprir o DoD
    comando = [
        sys.executable, 
        "-m", 
        "pytest", 
        str(caminho), 
        "--cov=.", 
        "--json-report", 
        f"--json-report-file={arquivo_report_json}",
        "--cov-report=json"
    ]
    
    try:
        logger.info(f"[QA Subagent] Executando testes para {nome_artefato}...")
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=30, cwd=str(dir_base))
        
        if resultado.returncode == 0:
            _contador_execucoes[str(caminho)] = 0

        return _parse_resultados_pytest(caminho, resultado, arquivo_cov_json)
        
    except subprocess.TimeoutExpired:
        logger.error(f"[QA Subagent] Timeout ao executar {caminho}")
        return _gerar_erro_execucao("ERR_TIMEOUT", "Execução ultrapassou o tempo limite 30s.", caminho)
    except Exception as e:
        logger.error(f"[QA Subagent] Erro fatal na execução: {e}")
        return _gerar_erro_execucao("ERR_TESTE_FALHOU_CRITICO", str(e), caminho)
    

def _parse_resultados_pytest(caminho: Path, resultado: subprocess.CompletedProcess, cov_json_path: Path) -> dict:
    """Parse do resultado de execução pytest com extração de cobertura.

    Args:
        caminho: Path do arquivo de teste executado.
        resultado: Objeto CompletedProcess com stdout/stderr do pytest.
        cov_json_path: Path do arquivo coverage.json gerado pelo pytest-cov.

    Returns:
        dict: Dicionário estruturado com status, testes gerados, cobertura e erros.
    """
    status_geral = "sucesso" if resultado.returncode == 0 else "falha"
    erros = []
    
    # Validação de Cobertura de Testes
    cobertura_dados = {
        "percentual": 0.0,
        "linhas_cobertas": 0,
        "linhas_totais": 0
    }

    if cov_json_path.exists():
        try:
            with open(cov_json_path, "r", encoding="utf-8") as f:
                cov_data = json.load(f)
                totals = cov_data.get("totals", {})
                cobertura_dados["percentual"] = round(totals.get("percent_covered", 0.0), 2)
                cobertura_dados["linhas_cobertas"] = totals.get("covered_lines", 0)
                cobertura_dados["linhas_totais"] = totals.get("num_statements", 0)
        except Exception as e:
            logger.warning(f"[QA Subagent] Falha ao ler coverage.json: {e}")

    # Trigger automático para o subagente de parsing (Filipe)
    next_action = "finalizar_qa"
    if status_geral == "falha":
        # Junta o stdout e o stderr para não perder nenhuma informação do Pytest
        log_completo = resultado.stdout
        if resultado.stderr:
            log_completo += f"\n--- AVISOS DE SISTEMA ---\n{resultado.stderr}"

        erros.append({
            "codigo": "ERR_TESTE_FALHOU",
            "log": log_completo
        })
        next_action = "trigger_correcao_matunag"

    return {
        "status": status_geral,
        "agente_origem": "pytest_runner",
        "proxima_acao_orquestrador": next_action, # Roteamento explícito
        "tipo_teste": "pytest",
        "testes_gerados": [
            {
                "nome": caminho.stem,
                "arquivo": str(caminho),
                "resultado": "passou" if status_geral == "sucesso" else "falhou"
            }
        ],
        "cobertura": cobertura_dados,
        "erros": erros
    }

def _gerar_erro_execucao(codigo: str, mensagem: str, caminho: Path = None) -> dict:
    """Gera payload de erro estruturado para roteamento ao subagente de correção.

    Args:
        codigo: Código do erro (ex: ERR_TIMEOUT, ERR_TESTE_FALHOU).
        mensagem: Descrição legível do erro.
        caminho: Path do arquivo de teste (opcional).

    Returns:
        dict: Payload estruturado com status, agente_origem e erros.
    """
    return {
        "status": "falha",
        "agente_origem": "pytest_runner",
        "proxima_acao_orquestrador": "trigger_correcao_matunag", # Roteamento de erro acionado
        "tipo_teste": "pytest",
        "testes_gerados": [
            {
                "nome": caminho.stem if caminho else "desconhecido",
                "arquivo": str(caminho) if caminho else "",
                "resultado": "falhou"
            }
        ],
        "cobertura": {
            "percentual": 0.0,
            "linhas_cobertas": 0,
            "linhas_totais": 0
        },
        "erros": [
            {
                "codigo": codigo,
                "log": mensagem
            }
        ]
    }