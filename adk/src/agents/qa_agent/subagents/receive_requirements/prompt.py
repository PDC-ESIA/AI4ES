"""Instruction do subagente receber_requisitos."""

RECEBER_REQUISITOS_PROMPT = (
    "Ao receber uma mensagem do usuário, monte um JSON com os campos: "
    "id_artefato (ex: 'HU-001'), tipo ('HU'), conteudo, modulo ('geral' se não informado), criticidade ('alta'). "
    "MUITO IMPORTANTE: Se a requisição contiver código-fonte (em anexo ou no texto), você DEVE criar uma propriedade chamada 'arquivos_apoio' "
    "sendo uma lista de objetos com 'nome' (ex: arquivo.py) e 'conteudo' (o código completo). "
    "Se você não preencher 'arquivos_apoio', o sistema NÃO reconhecerá o código-fonte! "
    "No campo conteudo, inclua apenas o texto do requisito. "
    "Chame a tool receber_requisitos com o JSON gerado e retorne o resultado."
)
