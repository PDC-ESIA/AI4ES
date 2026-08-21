"""Instruction do subagente receber_requisitos."""

RECEBER_REQUISITOS_PROMPT = (
    "Ao receber uma mensagem do usuário, monte um JSON com os campos: "
    "id_artefato (ex: 'HU-001'), tipo ('HU'), conteudo, modulo ('geral' se não informado), criticidade ('alta'). "
    "MUITO IMPORTANTE: Se a requisição contiver código-fonte (em anexo ou no texto), você DEVE criar uma propriedade chamada 'arquivos_apoio' "
    "sendo uma lista de objetos com 'nome' (ex: arquivo.py) e 'conteudo' (o código completo). "
    "Use arquivos_apoio para código inline; fontes já persistidos também são descobertos automaticamente. "
    "No campo conteudo, inclua apenas o texto do requisito. "
    "Chame a tool receber_requisitos com o JSON gerado e retorne o resultado."
)

RECEBER_REQUISITOS_PROMPT += (
    " Quando a mensagem contiver um Manifesto de Fase com artifacts "
    "tipo=source e path=..., inclua CADA fonte em arquivos_apoio no formato "
    "{'nome': '<basename>.py', 'path': '<path do manifesto>'}. "
    "Use 'conteudo' para anexos inline e 'path' para arquivos já persistidos. "
    "Paths do manifesto são canônicos; não declare código ausente sem usá-los."
)

RECEBER_REQUISITOS_PROMPT += (
    " O manifesto de Coding é opcional: a tool receber_requisitos também "
    "descobre automaticamente fontes persistidos em workspace_output/coder/src. "
    "Por isso, sempre chame a tool antes de concluir que o código está ausente. "
    "Na resposta, preserve literalmente os campos bootstrap_pytest e "
    "marcador_pacote retornados pela tool; não os substitua por inferências."
)
