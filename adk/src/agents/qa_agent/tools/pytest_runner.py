import subprocess
import json
from pathlib import Path
import logging
import sys
from datetime import datetime, timezone

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
Revisão manual do teste ou do requisito gerado. O agente entrou em loop tentando corrigir o erro.
"""
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)

def executar_pytest_tool(caminho_arquivo: str) -> dict:
    """
    Tool para executar pytest em um arquivo específico e retornar o relatório.
    """
    caminho = Path(caminho_arquivo)
    
    if not caminho.exists():
        return _gerar_erro_execucao("ERR_MODULO_NAO_ENCONTRADO", f"Arquivo {caminho} não existe.")

    # --- TRAVA DE LOOP ---
    nome_artefato = caminho.stem # Pega o nome do arquivo sem extensão (ex: test_dummy_rf001)
    tentativas = _contador_execucoes.get(str(caminho), 0) + 1
    _contador_execucoes[str(caminho)] = tentativas

    if tentativas > MAX_TENTATIVAS:
        logger.error(f"[QA Tool] ERR_LOOP acionado para {nome_artefato}. Tentativas: {tentativas}")
        caminho_duvida = _gerar_doubt_artifact_sincrono(
            id_artefato=nome_artefato, 
            motivo=f"Tentou processar a tool {MAX_TENTATIVAS} vezes e continuou falhando.",
            caminho_base=caminho
        )
        return _gerar_erro_execucao(
            "ERR_LOOP", 
            f"Execução bloqueada. Doubt Artifact gerado em: {caminho_duvida}"
        )
    # ---------------------

    # Comando: Roda o pytest como módulo do python atual
    comando = [
        sys.executable, 
        "-m", 
        "pytest", 
        str(caminho), 
        "--cov=.", 
        "--json-report", 
        f"--json-report-file={caminho.parent / 'report.json'}"
    ]
    
    try:
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=30)
        
        # Se o teste passou com sucesso, limpamos o contador para futuras manutenções
        if resultado.returncode == 0:
            _contador_execucoes[str(caminho)] = 0

        return _parse_resultados_pytest(caminho, resultado)
        
    except subprocess.TimeoutExpired:
        logger.error(f"[QA Tool] Timeout ao executar {caminho}")
        return _gerar_erro_execucao("ERR_TIMEOUT", "Execução ultrapassou o tempo limite.")
    except Exception as e:
        logger.error(f"[QA Tool] Erro fatal na execução: {e}")
        return _gerar_erro_execucao("ERR_TESTE_FALHOU", str(e))
    

def _parse_resultados_pytest(caminho: Path, resultado: subprocess.CompletedProcess) -> dict:
    status_geral = "sucesso" if resultado.returncode == 0 else "falha"
    erros = []
    
    # Aqui a tool do Filipe (Subtask 1.2) pode entrar em ação para ler o report.json
    # Para o escopo da Subtask 1.1, garantimos o contrato de saída:
    if status_geral == "falha":
        erros.append({
            "codigo": "ERR_TESTE_FALHOU",
            "log": resultado.stderr or resultado.stdout
        })

    return {
        "status": status_geral,
        "tipo_teste": "pytest",
        "testes_gerados": [
            {
                "nome": caminho.stem,
                "arquivo": str(caminho),
                "resultado": "passou" if status_geral == "sucesso" else "falhou"
            }
        ],
        "cobertura": {
            "percentual": 0.0, # Implementar extração do log de coverage aqui
            "linhas_cobertas": 0,
            "linhas_totais": 0
        },
        "erros": erros
    }

def _gerar_erro_execucao(codigo: str, mensagem: str) -> dict:
    """
    Gera um payload de erro padronizado para o Supervisor.
    """
    return {
        "status": "falha",
        "tipo_teste": "pytest",
        "testes_gerados": [],
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