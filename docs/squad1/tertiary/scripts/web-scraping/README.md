# Web Scraping - Extração de Dados de Artigos

Esta pasta contém scripts e ferramentas para realizar web scraping e extração de dados de artigos a partir de arquivos HTML.

## 📋 Arquivos

### `beautiful-soup` (diretório)
Script Python que utiliza a biblioteca BeautifulSoup para extrair dados de avaliação de qualidade de artigos.

**Funcionalidades:**
- Extrai dados de artigos a partir de arquivos HTML
- Processa avaliações qualitativas estruturadas em tabelas
- Identifica automaticamente a fonte dos artigos (Arxiv ou Scopus)
- Extrai respostas a 7 perguntas de qualidade (Q1-Q7)
- Extrai metadados: ID, Título, Ano, Score Total
- Exporta dados para CSV e Excel com legenda

**Perguntas de Qualidade Extraídas:**
- Q1: Does the search cover all relevant studies?
- Q2: Are the inclusion and exclusion criteria properly described?
- Q3: Is the quality of included primary studies assessed?
- Q4: Are primary studies adequately described?
- Q5: Is the justification for the study adequately described?
- Q6: Is the protocol validation properly described?
- Q7: Is data extraction properly described and appropriate?

## 🔧 Dependências

```
pandas
beautifulsoup4
openpyxl
```

**Instalação:**
```bash
pip install pandas beautifulsoup4 openpyxl
```

## 📊 Estrutura do HTML Esperado

O script espera um HTML com a seguinte estrutura:

```html
<div class="panel panel-default panel-quality-assessment">
    <h3 class="panel-title">
        Título do Artigo
        <small>(2024)</small>
        <span class="badge score pull-right">8.5</span>
    </h3>
    
    <table id="tbl-quality" article-id="4623xxxxx">
        <!-- Dados da tabela -->
    </table>
    
    <!-- Tabela com respostas -->
    <table>
        <tr>
            <td>Does the search cover all relevant studies?</td>
            <td class="selected-answer">Fully attended to</td>
        </tr>
        <!-- Mais linhas de respostas -->
    </table>
</div>
```

## 🚀 Uso

### Importar e usar a função

```python
from beautiful_soup import extract_all_finished

# Parâmetros:
# - html_file: caminho do arquivo HTML
# - output_csv: caminho de saída para o arquivo CSV
# - output_excel: caminho de saída para o arquivo Excel

extract_all_finished(
    'Conducting·Tertiary-GenAIforSoftwareEngineering-ALL-Finished.html',
    'artigos_all_finished.csv',
    'artigos_all_finished.xlsx'
)
```

## 📤 Dados de Saída

### Arquivo CSV
Contém as seguintes colunas:
- `ID` - Identificador único (A1, A2, A3, ...)
- `Artigo` - Título do artigo
- `Ano` - Ano de publicação
- `Score Total` - Pontuação de qualidade
- `Fonte` - Origem do artigo (Arxiv ou Scopus)
- `Q1` até `Q7` - Respostas às perguntas de qualidade

### Arquivo Excel
Contém 2 abas:
1. **Dados Extraídos** - Mesmas colunas do CSV
2. **Legenda Perguntas** - Mapeamento das perguntas (Q1-Q7) com seus textos completos

## 🔍 Lógica de Extração

1. **Identificação de Containers**: O script localiza todos os `<div>` com classe `panel-quality-assessment`
2. **Extração de Metadados**: Extrai título, ano e score do elemento `<h3>`
3. **Identificação da Fonte**: Verifica o atributo `article-id` da tabela:
   - Se começa com "4623" → Arxiv
   - Caso contrário → Scopus
4. **Extração de Respostas**: Procura por elementos `<td>` com classe `selected-answer` para obter as respostas
5. **Mapeamento de Perguntas**: Mapeia o texto das perguntas encontradas para IDs (Q1-Q7)

## 💾 Exemplo de Saída CSV

```
ID,Artigo,Ano,Score Total,Fonte,Q1,Q2,Q3,Q4,Q5,Q6,Q7
A1,Título do Artigo 1,2024,8.5,Arxiv,Fully attended to,Partially attended to,Not attended to,Fully attended to,Fully attended to,Partially attended to,Fully attended to
A2,Título do Artigo 2,2023,7.2,Scopus,Fully attended to,Fully attended to,Partially attended to,Not attended to,Fully attended to,Fully attended to,Partially attended to
```

## ⚙️ Configuração

As configurações principais do script estão na função `extract_all_finished()`:

```python
# Mapeamento de perguntas (pode ser customizado)
questions_map = {
    "Does the search cover all relevant studies?": "Q1",
    "Are the inclusion and exclusion criteria properly described?": "Q2",
    # ... etc
}
```

## 🐛 Tratamento de Erros

- Se um arquivo HTML não contiver a estrutura esperada, valores padrão são utilizados ("N/A" para campos ausentes)
- Valores `None` indicam que não houve resposta para a pergunta
- Artigos sem título recebem identificadores genéricos (Artigo 1, Artigo 2, etc.)

## 📝 Notas Importantes

- O script utiliza encoding UTF-8 com BOM para garantir compatibilidade com Excel
- O índice de artigos é automaticamente gerado começando de A1
- O encoding do arquivo HTML deve ser UTF-8
- A tabela de respostas é procurada tanto como irmã quanto dentro do container do artigo


