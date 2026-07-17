"""Contratos do gerador de planos e código Playwright E2E.

O núcleo permanece independente do fluxo pytest. Código Playwright só pode ser
gerado a partir dos passos estruturados definidos neste módulo.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TipoSistema(str, Enum):
    WEB = "web"
    API = "api"
    FULLSTACK = "fullstack"
    CLI = "cli"
    AGENTICO = "agentico"
    DESCONHECIDO = "desconhecido"


class FrameworkAlvo(str, Enum):
    PLAYWRIGHT = "playwright"


class TipoSaida(str, Enum):
    PLANO_E2E = "plano_e2e"
    CODIGO_PLAYWRIGHT = "codigo_playwright"
    EXECUTADO = "executado"
    BLOQUEADO = "bloqueado"


class NivelConfianca(str, Enum):
    ALTO = "alto"
    MEDIO = "medio"
    BAIXO = "baixo"


class CategoriaCenario(str, Enum):
    FLUXO_FELIZ = "fluxo_feliz"
    FALHA_DEPENDENCIA_EXTERNA = "falha_dependencia_externa"
    TIMEOUT_LATENCIA = "timeout_latencia"
    DADOS_MALFORMADOS = "dados_malformados"


class CategoriaBloqueio(str, Enum):
    ENTRADA = "entrada"
    ESCOPO = "escopo"
    GERACAO_CODIGO = "geracao_codigo"
    EXECUCAO = "execucao"


class TipoLocalizador(str, Enum):
    ROLE = "role"
    LABEL = "label"
    TEXT = "text"
    TEST_ID = "test_id"
    PLACEHOLDER = "placeholder"


class AcaoAutomacao(str, Enum):
    PREENCHER = "preencher"
    CLICAR = "clicar"
    MARCAR = "marcar"
    DESMARCAR = "desmarcar"
    SELECIONAR = "selecionar"
    PRESSIONAR = "pressionar"
    VERIFICAR_VISIVEL = "verificar_visivel"
    VERIFICAR_TEXTO = "verificar_texto"
    VERIFICAR_URL = "verificar_url"


class EntradaE2E(_SchemaBase):
    """Contrato flexível recebido pela futura tool pública."""

    requisitos: Any = Field(description="Texto, JSON ou lista de requisitos.")
    codigo_fonte: Any = None
    tipo_sistema: TipoSistema | None = None
    framework_alvo: FrameworkAlvo = FrameworkAlvo.PLAYWRIGHT
    base_url: str | None = None
    rotas_ou_telas: Any = None
    perfis_usuario: Any = None
    dados_teste: Any = None
    contratos_api: Any = None
    ambiente_execucao: Any = None
    comando_execucao: str | None = None
    restricoes: Any = None

    @field_validator("tipo_sistema", mode="before")
    @classmethod
    def normalizar_tipo_sistema(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator("framework_alvo", mode="before")
    @classmethod
    def normalizar_framework(cls, value: Any) -> Any:
        if value is None or value == "":
            return FrameworkAlvo.PLAYWRIGHT
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("base_url", "comando_execucao", mode="before")
    @classmethod
    def normalizar_textos_opcionais(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class RequisitoNormalizado(_SchemaBase):
    id: str = Field(min_length=1, max_length=120)
    tipo: str = Field(default="REQUISITO", min_length=1, max_length=40)
    conteudo: str = Field(min_length=1, max_length=100_000)
    fonte: str = Field(default="texto")
    metadados: dict[str, Any] = Field(default_factory=dict)


class CodigoFonteNormalizado(_SchemaBase):
    nome: str = Field(default="codigo_fonte.txt", min_length=1, max_length=255)
    conteudo: str = Field(min_length=1, max_length=200_000)
    linguagem: str | None = None


class LocalizadorPlaywright(_SchemaBase):
    tipo: TipoLocalizador
    valor: str = Field(min_length=1, max_length=500)
    nome_acessivel: str | None = Field(default=None, max_length=500)
    exato: bool = True

    @field_validator("tipo", mode="before")
    @classmethod
    def normalizar_tipo(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value


class PassoAutomacao(_SchemaBase):
    acao: AcaoAutomacao
    localizador: LocalizadorPlaywright | None = None
    valor: str | int | float | bool | None = None
    chave_dado: str | None = Field(default=None, max_length=200)

    @field_validator("acao", mode="before")
    @classmethod
    def normalizar_acao(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value


class AlvoNavegacao(_SchemaBase):
    nome: str = Field(min_length=1, max_length=300)
    rota: str | None = None
    seletores: list[str] = Field(default_factory=list)
    acoes: list[str] = Field(default_factory=list)
    passos_automacao: list[PassoAutomacao] = Field(default_factory=list)
    erros_automacao: list[str] = Field(default_factory=list)


class EntradaE2ENormalizada(_SchemaBase):
    requisitos: list[RequisitoNormalizado] = Field(default_factory=list)
    codigo_fonte: list[CodigoFonteNormalizado] = Field(default_factory=list)
    tipo_sistema_informado: TipoSistema | None = None
    framework_alvo: FrameworkAlvo = FrameworkAlvo.PLAYWRIGHT
    base_url: str | None = None
    rotas_ou_telas: list[AlvoNavegacao] = Field(default_factory=list)
    perfis_usuario: list[str] = Field(default_factory=list)
    dados_teste: list[dict[str, Any]] = Field(default_factory=list)
    contratos_api: list[dict[str, Any]] = Field(default_factory=list)
    ambiente_execucao: dict[str, Any] = Field(default_factory=dict)
    comando_execucao: str | None = None
    restricoes: list[str] = Field(default_factory=list)


class AnaliseSuperficie(_SchemaBase):
    tipo_sistema: TipoSistema
    origem_classificacao: str
    sinais_encontrados: list[str] = Field(default_factory=list)
    suportado_no_p0: bool
    resumo: str


class BloqueioE2E(_SchemaBase):
    codigo: str
    categoria: CategoriaBloqueio
    mensagem: str
    campos_ausentes: list[str] = Field(default_factory=list)
    impede_plano: bool = False
    impede_codigo: bool = True
    impede_execucao: bool = True


class ValidacaoContratoE2E(_SchemaBase):
    pode_gerar_plano: bool
    pode_gerar_codigo: bool
    pode_executar: bool
    nivel_confianca: NivelConfianca
    pontuacao_confianca: float = Field(ge=0, le=1)
    bloqueios: list[BloqueioE2E] = Field(default_factory=list)


class CenarioE2E(_SchemaBase):
    id: str
    nome: str
    categoria: CategoriaCenario
    objetivo: str
    requisitos_origem: list[str] = Field(default_factory=list)
    precondicoes: list[str] = Field(default_factory=list)
    passos: list[str] = Field(default_factory=list)
    dados_teste: list[str] = Field(default_factory=list)
    assercoes: list[str] = Field(default_factory=list)
    dependencias: list[str] = Field(default_factory=list)
    mocks_stubs: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    pronto_para_automacao: bool = False


class ResultadoExecucaoE2E(_SchemaBase):
    status: str
    comando: str | None = None
    codigo_saida: int | None = None
    duracao_ms: int = 0
    testes_executados: int = 0
    testes_aprovados: int = 0
    testes_falhos: int = 0
    testes_pulados: int = 0
    arquivo_relatorio: str | None = None
    diretorio_artefatos: str | None = None
    falhas: list[dict[str, Any]] = Field(default_factory=list)
    logs_resumidos: list[str] = Field(default_factory=list)


class ResultadoGeracaoPlaywright(_SchemaBase):
    arquivo: str
    testes_ativos: int
    testes_pulados: int


class RespostaE2E(_SchemaBase):
    tipo_saida: TipoSaida
    framework_alvo: FrameworkAlvo = FrameworkAlvo.PLAYWRIGHT
    nivel_confianca: NivelConfianca
    tipo_sistema: TipoSistema = TipoSistema.DESCONHECIDO
    resumo: str
    cenarios: list[CenarioE2E] = Field(default_factory=list)
    precondicoes: list[str] = Field(default_factory=list)
    mocks_stubs: list[str] = Field(default_factory=list)
    arquivos_sugeridos: list[str] = Field(default_factory=list)
    arquivos_gerados: list[str] = Field(default_factory=list)
    resultado_execucao: ResultadoExecucaoE2E | None = None
    bloqueios: list[BloqueioE2E] = Field(default_factory=list)
    metadados: dict[str, Any] = Field(default_factory=dict)
