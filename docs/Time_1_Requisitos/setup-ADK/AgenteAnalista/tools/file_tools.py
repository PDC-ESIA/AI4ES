import os
import re


def check_glossary(term: str) -> str:
    """
    Verifica se um termo já existe no glossário.

    Args:
        term: O termo a verificar.

    Returns:
        Mensagem indicando se o termo existe ou não, com sua definição atual se existir.
    """
    glossary_path = os.path.join("knowledge", "glossario.md")

    if not os.path.exists(glossary_path):
        return "Erro: Arquivo glossario.md não encontrado em knowledge/."

    with open(glossary_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')]
        if len(cells) >= 4 and cells[1].lower() == term.strip().lower():
            return f"Termo '{term}' já existe no glossário. Definição atual: {cells[2]}"

    return f"Termo '{term}' não encontrado no glossário."


def add_to_glossary(term: str, definition: str, sources: str):
    """
    Adiciona um termo técnico ao glossário em knowledge/glossario.md.
    Se o termo já existir, atualiza a definição e as fontes.

    Args:
        term: O termo técnico a ser adicionado.
        definition: A definição formal extraída do documento.
        sources: As fontes (nomes dos chunks separados por vírgula, ex: "chunk_001.txt, chunk_003.txt").

    Returns:
        Mensagem de sucesso ou erro.
    """
    glossary_path = os.path.join("knowledge", "glossario.md")

    if not os.path.exists(glossary_path):
        return "Erro: Arquivo glossario.md não encontrado em knowledge/."

    try:
        with open(glossary_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Escapa pipes dentro da definição para não quebrar a tabela markdown
        definition_clean = definition.replace('|', '\\|').strip()
        sources_clean = sources.replace('|', '\\|').strip()
        term_clean = term.strip()

        new_row = f"| {term_clean} | {definition_clean} | {sources_clean} |"

        # Verifica se o termo já existe na tabela (case-insensitive)
        lines = content.split('\n')
        term_found = False
        for i, line in enumerate(lines):
            # Procura por linhas da tabela que começam com | Termo |
            if line.startswith('|'):
                cells = [c.strip() for c in line.split('|')]
                # cells[0] é vazio (antes do primeiro |), cells[1] é o termo
                if len(cells) >= 4 and cells[1].lower() == term_clean.lower():
                    lines[i] = new_row
                    term_found = True
                    break

        if term_found:
            content = '\n'.join(lines)
        else:
            # Adiciona nova linha ao final da tabela
            content = content.rstrip('\n') + '\n' + new_row + '\n'

        with open(glossary_path, 'w', encoding='utf-8') as f:
            f.write(content)

        action = "atualizado" if term_found else "adicionado"
        return f"Sucesso: Termo '{term_clean}' {action} no glossário."

    except Exception as e:
        return f"Erro ao escrever no glossário: {str(e)}"


def add_doubt(
    affected_artifact: str,
    context_excerpt: str,
    doubt_description: str,
    reason: str,
    impact: str,
    suggestion: str = ""
):
    """
    Adiciona uma dúvida ao Doubt_Artifact.md com numeração D-NNN auto-incrementada.

    Args:
        affected_artifact: Artefato afetado (ex: "Glossário", "HU-001", "RF-003").
        context_excerpt: Trecho do contexto que gerou a dúvida.
        doubt_description: Descrição clara da incerteza.
        reason: Motivo da dúvida.
        impact: Impacto se a dúvida não for resolvida.
        suggestion: Sugestão do agente (opcional).

    Returns:
        Mensagem de sucesso ou erro.
    """
    doubt_path = "Doubt_Artifact.md"

    if not os.path.exists(doubt_path):
        return "Erro: Doubt_Artifact.md não encontrado."

    try:
        with open(doubt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Auto-incremento: encontra o maior D-NNN existente
        existing_ids = re.findall(r'### D-(\d+)', content)
        if existing_ids:
            next_id = max(int(n) for n in existing_ids) + 1
        else:
            next_id = 1

        doubt_id = f"{next_id:03d}"

        # Monta a entrada da dúvida
        doubt_entry = f"""
### D-{doubt_id}

- **Artefato afetado:** {affected_artifact}
- **Trecho do contexto:** "{context_excerpt}"
- **Dúvida:** {doubt_description}
- **Motivo da dúvida**: {reason}
- **Impacto se não resolvida:** {impact}
- **Bloqueante:** Não
- **Status:** Aberta
- **Sugestão do Agente:** {suggestion if suggestion else "Nenhuma"}
- **Resposta:** _(preencher na revisão humana)_

---"""

        # Insere antes da última linha separadora "---" do template,
        # ou ao final do arquivo
        content = content.rstrip('\n') + '\n' + doubt_entry + '\n'

        with open(doubt_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Sucesso: Dúvida D-{doubt_id} registrada no Doubt_Artifact.md."

    except Exception as e:
        return f"Erro ao registrar dúvida: {str(e)}"
