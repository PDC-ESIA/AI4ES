"""Testes da verificação estática de dependências (import × requirements.txt).

O foco é o modo de falha caro: **falso positivo**. Um gate que acusa dependência
inexistente devolve ao coder um erro que não existe e queima uma iteração do
loop — por isso a maior parte dos casos aqui afirma "0 achados".
"""

from pathlib import Path

from shared.tools.coding_tools.verificacao_dependencias import (
    ALIAS_IMPORT_PARA_PACOTE,
    TRANSITIVOS_CONHECIDOS,
    verificar_dependencias,
)


def _montar_projeto(raiz: Path, arquivos: dict[str, str]) -> Path:
    """Materializa um projeto mínimo a partir de {caminho relativo: conteúdo}."""
    for caminho, conteudo in arquivos.items():
        destino = raiz / caminho
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    return raiz


# ---------------------------------------------------------------------------
# Casos que NÃO devem gerar achado
# ---------------------------------------------------------------------------


def test_import_de_terceiro_presente_no_requirements(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_import_de_stdlib_nao_gera_achado(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "import os\nimport json\nfrom pathlib import Path\n",
            "requirements.txt": "fastapi\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_import_relativo_nao_gera_achado(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/__init__.py": "",
            "app/models.py": "class X: pass\n",
            "app/main.py": "from .models import X\nfrom . import models\n",
            "requirements.txt": "fastapi\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_import_de_modulo_local_nao_gera_achado(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/__init__.py": "",
            "app/database.py": "engine = None\n",
            "app/main.py": "from app.database import engine\n",
            "requirements.txt": "fastapi\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_nome_divergente_com_alias_conhecido_nao_gera_achado(tmp_path):
    """`jose` ↔ `python-jose`: o pacote está declarado, o import tem outro nome."""
    _montar_projeto(
        tmp_path,
        {
            "app/auth.py": "from jose import jwt as _jwt\n",
            "requirements.txt": "fastapi\npython-jose\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_caso_real_pillow_nao_gera_achado(tmp_path):
    """Caso real: `import PIL` com `pillow` declarado.

    Veio de uma execução bem-sucedida de verdade. Um gate sem a tabela de alias a
    teria abortado — é o cenário que motiva a política fail-open.
    """
    _montar_projeto(
        tmp_path,
        {
            "app/services/thumbnails.py": "from PIL import Image\n",
            "requirements.txt": "fastapi\npillow\npython-multipart\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_normalizacao_pep503_e_specifiers(tmp_path):
    """Case, extras, specifiers e `_`↔`-` não podem virar falso positivo.

    `SQLAlchemy` → `sqlalchemy` (case); `uvicorn[standard]==0.35.0` → `uvicorn`
    (extras + versão + comentário); `python_multipart` → `python-multipart`
    (PEP 503), que é o pacote do import `multipart`.

    Cuidado ao estender: `SQL_Alchemy` **não** serve como variante de
    `sqlalchemy` — normaliza para `sql-alchemy`, outra distribuição.
    """
    _montar_projeto(
        tmp_path,
        {
            "app/db.py": "import sqlalchemy\nimport uvicorn\nimport multipart\n",
            "requirements.txt": (
                "SQLAlchemy>=2.0\n"
                "uvicorn[standard]==0.35.0  # comentário\n"
                "python_multipart\n"
            ),
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_arquivo_com_sintaxe_invalida_nao_levanta(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/quebrado.py": "def f(:\n    pass\n",
            "app/main.py": "from fastapi import FastAPI\n",
            "requirements.txt": "fastapi\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_diretorio_inexistente_devolve_lista_vazia(tmp_path):
    assert verificar_dependencias(tmp_path / "nao-existe") == []


def test_projeto_sem_python_devolve_lista_vazia(tmp_path):
    _montar_projeto(tmp_path, {"README.md": "# nada aqui\n"})
    assert verificar_dependencias(tmp_path) == []


# ---------------------------------------------------------------------------
# Casos que DEVEM gerar achado
# ---------------------------------------------------------------------------


def test_import_de_terceiro_ausente_gera_um_achado_informativo(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "from fastapi import FastAPI\nimport httpx\n",
            "requirements.txt": "fastapi\n",
        },
    )
    achados = verificar_dependencias(tmp_path)

    assert len(achados) == 1
    achado = achados[0]
    assert achado["tipo"] == "import_nao_declarado"
    assert achado["modulo"] == "httpx"
    assert achado["arquivo"] == "app/main.py"
    assert achado["linha"] == 2
    # Divergência de nome NUNCA reprova — só informa.
    assert achado["severidade"] == "info"


def test_alias_conhecido_ausente_sugere_o_pacote_correto(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/img.py": "from PIL import Image\n",
            "requirements.txt": "fastapi\n",
        },
    )
    achados = verificar_dependencias(tmp_path)

    assert len(achados) == 1
    assert achados[0]["modulo"] == "PIL"
    assert achados[0]["pacote_sugerido"] == "Pillow"
    assert achados[0]["severidade"] == "info"


def test_alias_desconhecido_nao_sugere_pacote(tmp_path):
    """Sem entrada na tabela, a mensagem admite a incerteza em vez de chutar."""
    _montar_projeto(
        tmp_path,
        {"app/x.py": "import biblioteca_exotica\n", "requirements.txt": "fastapi\n"},
    )
    achados = verificar_dependencias(tmp_path)

    assert len(achados) == 1
    assert achados[0]["pacote_sugerido"] is None
    assert "confirme antes de alterar" in achados[0]["mensagem"]
    assert achados[0]["severidade"] == "info"


def test_requirements_ausente_com_terceiros_e_o_unico_caso_critical(tmp_path):
    """Único cenário sem ambiguidade possível — e o único que reprova."""
    _montar_projeto(
        tmp_path,
        {"app/main.py": "from fastapi import FastAPI\nimport sqlalchemy\n"},
    )
    achados = verificar_dependencias(tmp_path)

    assert len(achados) == 1, (
        "deve ser UM achado explicando a ausência, não um por módulo"
    )
    assert achados[0]["tipo"] == "requirements_ausente"
    assert achados[0]["severidade"] == "critical"
    assert "fastapi" in achados[0]["mensagem"]
    assert "sqlalchemy" in achados[0]["mensagem"]


def test_requirements_ausente_mas_so_stdlib_nao_gera_achado(tmp_path):
    """Sem dependência externa, não ter requirements.txt não é problema."""
    _montar_projeto(tmp_path, {"app/main.py": "import os\nimport sys\n"})
    assert verificar_dependencias(tmp_path) == []


def test_requirements_alternativo_em_subpasta_e_reconhecido(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "from fastapi import FastAPI\n",
            "requirements/base.txt": "fastapi\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


# ---------------------------------------------------------------------------
# Import transitivo — achado registrado, mas não acionável
# ---------------------------------------------------------------------------


def test_caso_real_starlette_sob_fastapi(tmp_path):
    """Caso real: `Jinja2Templates` importado de `starlette.templating`.

    O achado é verdadeiro (o `starlette` não está declarado) e inofensivo (o
    `fastapi` o instala). Classificá-lo como divergência comum saturaria a
    evidência de qualquer projeto FastAPI que renderize template.
    """
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": (
                "from fastapi import FastAPI\n"
                "from starlette.templating import Jinja2Templates\n"
            ),
            "requirements.txt": "fastapi\nuvicorn\njinja2\n",
        },
    )
    achados = verificar_dependencias(tmp_path)

    assert len(achados) == 1
    achado = achados[0]
    assert achado["tipo"] == "import_transitivo"
    assert achado["modulo"] == "starlette"
    assert achado["severidade"] == "info"
    # Não há pacote a acrescentar: declarar transitiva duplica o pin.
    assert achado["pacote_sugerido"] is None
    assert "fastapi" in achado["mensagem"]


def test_transitivo_sem_o_provedor_declarado_volta_a_ser_divergencia(tmp_path):
    """A tabela não isenta o módulo em si — isenta a combinação com o provedor."""
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "from starlette.templating import Jinja2Templates\n",
            "requirements.txt": "uvicorn\n",
        },
    )
    achados = verificar_dependencias(tmp_path)

    assert len(achados) == 1
    assert achados[0]["tipo"] == "import_nao_declarado"
    assert achados[0]["modulo"] == "starlette"


def test_transitivo_nao_mascara_dependencia_realmente_ausente(tmp_path):
    """As duas classes convivem no mesmo run, cada uma com seu tipo."""
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "import httpx\nimport starlette\n",
            "requirements.txt": "fastapi\n",
        },
    )
    achados = verificar_dependencias(tmp_path)

    assert [(a["modulo"], a["tipo"]) for a in achados] == [
        ("httpx", "import_nao_declarado"),
        ("starlette", "import_transitivo"),
    ]


def test_transitivo_declarado_explicitamente_nao_gera_achado(tmp_path):
    """Quem declara a transitiva à mão não é penalizado — é caso de declarado."""
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "import starlette\n",
            "requirements.txt": "fastapi\nstarlette>=0.37\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_tabela_de_transitivos_cobre_o_caso_observado():
    """Guarda contra remoção acidental do par que motivou a tabela."""
    assert "starlette" in TRANSITIVOS_CONHECIDOS["fastapi"]
    assert "pydantic" in TRANSITIVOS_CONHECIDOS["fastapi"]


# ---------------------------------------------------------------------------
# Propriedades gerais
# ---------------------------------------------------------------------------


def test_modulo_repetido_aparece_uma_unica_vez(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/a.py": "import httpx\n",
            "app/b.py": "import httpx\n",
            "app/c.py": "from httpx import Client\n",
            "requirements.txt": "fastapi\n",
        },
    )
    achados = verificar_dependencias(tmp_path)
    assert [a["modulo"] for a in achados] == ["httpx"]


def test_saida_e_deterministica(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/a.py": "import httpx\nimport rich\n",
            "app/b.py": "import typer\n",
            "requirements.txt": "fastapi\n",
        },
    )
    assert verificar_dependencias(tmp_path) == verificar_dependencias(tmp_path)
    assert [a["modulo"] for a in verificar_dependencias(tmp_path)] == [
        "httpx",
        "rich",
        "typer",
    ]


def test_pycache_e_venv_sao_ignorados(tmp_path):
    _montar_projeto(
        tmp_path,
        {
            "app/main.py": "from fastapi import FastAPI\n",
            ".venv/lib/pacote.py": "import biblioteca_que_nao_existe\n",
            "app/__pycache__/lixo.py": "import outra_biblioteca\n",
            "requirements.txt": "fastapi\n",
        },
    )
    assert verificar_dependencias(tmp_path) == []


def test_tabela_de_alias_cobre_os_casos_do_plano():
    """Guarda contra remoção acidental — sem estes, falso positivo garantido."""
    for importado, pacote in (
        ("jose", "python-jose"),
        ("dotenv", "python-dotenv"),
        ("jwt", "PyJWT"),
        ("multipart", "python-multipart"),
        ("PIL", "Pillow"),
        ("yaml", "PyYAML"),
        ("bs4", "beautifulsoup4"),
        ("sklearn", "scikit-learn"),
    ):
        assert ALIAS_IMPORT_PARA_PACOTE[importado] == pacote
