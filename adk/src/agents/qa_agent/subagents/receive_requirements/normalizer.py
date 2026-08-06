"""Normalização de entrada: extração de anexos inline (parts) e fusão com o campo 'conteudo'."""

import base64


def _extrair_de_parts(parts: list) -> tuple[list[dict], list[str]]:
    arquivos_apoio: list[dict] = []
    textos: list[str] = []

    for part in parts:
        if not isinstance(part, dict):
            continue

        texto = part.get("text")
        if isinstance(texto, str) and texto.strip():
            textos.append(texto.strip())

        inline = part.get("inlineData")
        if not isinstance(inline, dict):
            continue

        nome = inline.get("displayName") or inline.get("name") or "arquivo_anexo"
        mime = inline.get("mimeType") or "application/octet-stream"
        conteudo_b64 = inline.get("data")
        if not isinstance(conteudo_b64, str) or not conteudo_b64.strip():
            continue

        entrada_arquivo = {"nome": nome}
        try:
            bruto = base64.b64decode(conteudo_b64)
            texto_decodificado = bruto.decode("utf-8")
            entrada_arquivo["conteudo"] = texto_decodificado
            if texto_decodificado.strip():
                textos.append(texto_decodificado.strip())
        except Exception:
            entrada_arquivo["conteudo_base64"] = conteudo_b64

        entrada_arquivo["mime_type"] = mime
        arquivos_apoio.append(entrada_arquivo)

    return arquivos_apoio, textos


def _normalizar_anexos_inline(lista_artefatos: list) -> list:
    normalizados = []
    for artefato in lista_artefatos:
        if not isinstance(artefato, dict):
            continue

        arquivos_existentes = artefato.get("arquivos_apoio", [])
        if not isinstance(arquivos_existentes, list):
            arquivos_existentes = []

        parts = artefato.get("parts")
        if not isinstance(parts, list):
            content = artefato.get("content", {})
            if isinstance(content, dict):
                parts = content.get("parts")

        textos_extraidos: list[str] = []
        if isinstance(parts, list):
            arquivos_extraidos, textos_extraidos = _extrair_de_parts(parts)
            arquivos_existentes.extend(arquivos_extraidos)

        if arquivos_existentes:
            artefato["arquivos_apoio"] = arquivos_existentes

        conteudo_atual = artefato.get("conteudo", "")
        if not isinstance(conteudo_atual, str):
            conteudo_atual = str(conteudo_atual)

        if textos_extraidos:
            bloco_extra = "\n\n".join(textos_extraidos).strip()
            if bloco_extra and bloco_extra not in conteudo_atual:
                artefato["conteudo"] = (
                    f"{conteudo_atual}\n\n{bloco_extra}".strip()
                    if conteudo_atual.strip()
                    else bloco_extra
                )

        normalizados.append(artefato)

    return normalizados
