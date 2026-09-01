# Gráficos - Síntese de Extração Qualitativa

Esta pasta contém scripts Python para gerar visualizações e gráficos a partir dos dados coletados durante o processo de extração qualitativa de estudos.

## 📋 Arquivos

### `generate-metadata-charts.py`
Script que gera visualizações baseadas em metadados dos artigos.

**Funcionalidades:**
- Gera gráfico de **Top 10 Países** por publicação
- Gera gráfico de **Top 10 Afiliações** dos autores
- Gera gráfico de **Top 10 Autores** mais publicados
- Processa dados de múltiplos valores separados por vírgula ou ponto e vírgula

**Entrada:**
- Arquivo CSV com os seguintes campos: `País`, `Afiliação`, `Autores`

**Saída:**
- `top_paises.png` - Gráfico de barras com os países com mais publicações
- `top_afiliacoes.png` - Gráfico de barras com as principais afiliações
- Outros gráficos de metadados conforme o arquivo de entrada

**Uso:**
```python
from generate_metadata_charts import generate_metadata_visualizations
generate_metadata_visualizations('dados_metadados.csv', './output_charts')
```

### `generate-scopus-charts.py`
Script que gera visualizações específicas para os dados de qualidade dos artigos do Scopus.

**Funcionalidades:**
- Gera gráfico de **barras horizontais empilhadas** mostrando a distribuição de respostas (Fully attended to, Partially attended to, Not attended to)
- Filtra automaticamente artigos sem respostas
- Apresenta as 7 perguntas de qualidade (Q1-Q7) com seus respectivos textos completos

**Perguntas de Qualidade (Q1-Q7):**
- Q1: Does the search cover all relevant studies?
- Q2: Are the inclusion and exclusion criteria properly described?
- Q3: Is the quality of included primary studies assessed?
- Q4: Are primary studies adequately described?
- Q5: Is the justification for the study adequately described?
- Q6: Is the protocol validation properly described?
- Q7: Is data extraction properly described and appropriate?

**Entrada:**
- Arquivo CSV com as colunas: `ID`, `Q1`, `Q2`, `Q3`, `Q4`, `Q5`, `Q6`, `Q7` com valores das respostas

**Saída:**
- `qualidade_scopus.png` - Gráfico de barras horizontais empilhadas com a distribuição de qualidade

**Uso:**
```python
from generate_scopus_charts import generate_scopus_visualizations
generate_scopus_visualizations('artigos_scopus.csv', './output_charts')
```

## 🔧 Dependências

```
pandas
matplotlib
seaborn
```

**Instalação:**
```bash
pip install pandas matplotlib seaborn
```

## 📊 Formato dos Dados de Entrada

### Para `generate-metadata-charts.py`
O arquivo CSV deve conter pelo menos as colunas:
- `País` (valores separados por `;` ou `,`)
- `Afiliação` (valores separados por `;`)
- `Autores` (valores separados por `,` ou `and`)

### Para `generate-scopus-charts.py`
O arquivo CSV deve conter:
- `ID` - Identificador único do artigo
- `Q1` até `Q7` - Respostas às perguntas de qualidade (pode conter: "Fully attended to", "Partially attended to", "Not attended to", ou valores vazios)

## 💡 Exemplos de Uso

```bash
# Gerar gráficos de metadados
python generate-matadata-charts.py

# Gerar gráficos de qualidade Scopus
python generate-scopus-charts.py
```

## 📝 Notas Importantes

- Os gráficos são salvos em formato PNG com alta resolução
- O script cria automaticamente o diretório de saída se não existir
- Dados faltantes (`NaN`) são ignorados automaticamente
- O script de Scopus filtra apenas artigos com pelo menos uma resposta


