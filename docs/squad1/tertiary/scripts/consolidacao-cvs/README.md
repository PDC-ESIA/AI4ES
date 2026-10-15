# Consolidação CSV - Merge de Dados

Esta pasta contém scripts para consolidar e mesclar dados de diferentes fontes no processo de extração qualitativa.

## 📋 Arquivos

### `merge-data.py`
Script Python que realiza o merge (fusão) de dados de qualidade com dados de extração.

**Funcionalidades:**
- Mescla dados de avaliação de qualidade com dados de extração
- Normaliza títulos de artigos para fazer matching preciso
- Mantém todos os artigos do conjunto de qualidade (merge left)
- Remove colunas duplicadas automaticamente
- Exporta resultado em CSV e Excel com abas separadas
- Adiciona legenda de perguntas na planilha Excel

## 🔧 Dependências

```
pandas
openpyxl
```

**Instalação:**
```bash
pip install pandas openpyxl
```

## 🚀 Uso

### Importar e usar a função

```python
from merge_data import merge_data

# Parâmetros:
# - quality_csv: arquivo CSV com dados de qualidade 
# - extraction_xls: arquivo Excel com dados de extração
# - output_csv: caminho de saída para o arquivo CSV consolidado
# - output_excel: caminho de saída para o arquivo Excel consolidado

merge_data(
    'artigos_scopus_quality.csv',
    'dados_extracao.xlsx',
    'artigos_consolidados.csv',
    'artigos_consolidados.xlsx'
)
```

## 📊 Formato dos Dados de Entrada

### Arquivo CSV de Qualidade (quality_csv)
Deve conter as colunas:
- `Artigo` - Título do artigo
- `Ano` - Ano de publicação
- `Q1` até `Q7` - Respostas às perguntas de qualidade
- Outras colunas de metadados

**Exemplo:**
```
ID,Artigo,Ano,Score Total,Fonte,Q1,Q2,Q3,Q4,Q5,Q6,Q7
A1,Título do Artigo,2024,8.5,Scopus,Fully attended to,Partially attended to,...
```

### Arquivo Excel de Extração (extraction_xls)
Deve conter as colunas:
- `article` - Título do artigo
- `Ano` - Ano de publicação (será removido para evitar duplicata)
- Outras colunas com dados extraídos

**Exemplo:**
```
article,Ano,tools,techniques,challenges,benefits
Título do Artigo,2024,"Tool1, Tool2","Technique1","Challenge1","Benefit1"
```

## 📤 Dados de Saída

### Arquivo CSV Consolidado
Contém todas as colunas do arquivo de qualidade mais as colunas do arquivo de extração (exceto `Ano` duplicado e coluna `article`).

**Exemplo de estrutura:**
```
ID,Artigo,Ano,Score Total,Fonte,Q1,Q2,Q3,Q4,Q5,Q6,Q7,tools,techniques,challenges,benefits
```

### Arquivo Excel Consolidado
Contém 2 abas:
1. **Dados Consolidados** - Mesmos dados do CSV
2. **Legenda Perguntas** - Mapeamento das perguntas (Q1-Q7) com seus textos completos

**Legenda de Perguntas:**
```
ID,Pergunta
Q1,Does the search cover all relevant studies?
Q2,Are the inclusion and exclusion criteria properly described?
Q3,Is the quality of included primary studies assessed?
Q4,Are primary studies adequately described?
Q5,Is the justification for the study adequately described?
Q6,Is the protocol validation properly described?
Q7,Is data extraction properly described and appropriate?
```

## 🔗 Lógica de Merge

### Normalização de Títulos

O script normaliza títulos para fazer o matching:
1. Converte para minúsculas
2. Remove caracteres especiais (mantém apenas letras e números)
3. Remove espaços extras

**Exemplo:**
- `"GenAI for Software Engineering"` → `genaiforswireengineering`
- `"Gen-AI for SW Engineering (2024)"` → `genaiforswengineering`

### Estratégia de Merge

- Tipo: **LEFT JOIN** (mantém todos os registros do arquivo de qualidade)
- Chave: `title_norm` (título normalizado)
- Se não houver match na extração, as colunas da extração ficarão vazias (`NaN`)

### Remoção de Colunas Duplicadas

- Remove `Ano` do arquivo de extração para evitar colunas duplicadas
- Remove `article` (título em inglês) após o merge
- Remove a coluna de normalização `title_norm` do resultado final

## 📊 Fluxo de Dados

```
Arquivo de Qualidade (CSV)          Arquivo de Extração (Excel)
         |                                    |
         v                                    v
   Normalizar títulos    +    Normalizar títulos
         |                                    |
         +---------> MERGE LEFT <-----------+
                     (por título)
                            |
                            v
                   Consolidado (CSV + Excel)
```

## 💡 Casos de Uso

1. **Análise completa**: Combina dados de qualidade com informações extraídas
2. **Rastreabilidade**: Manter referência aos IDs e fontes originais
3. **Relatórios**: Gerar relatórios consolidados com todas as dimensões

## ⚠️ Notas Importantes

- O script mantém todos os ~68 artigos do Scopus (aqueles no arquivo de qualidade)
- Se houver títulos com variações mínimas, o normalize_title ajuda na correspondência
- A coluna `Ano` é mantida apenas do arquivo de qualidade
- Valores `NaN` (vazios) indicam que não houve correspondência para aquele artigo na extração
- O encoding do arquivo de saída é UTF-8 com BOM para compatibilidade com Excel

## 🔍 Debugging

Se você quiser debugar o processo de merge:

```python
import pandas as pd

# Ver quantos registros foram encontrados
print(f"Total de artigos na qualidade: {len(df_quality)}")
print(f"Total de artigos na extração: {len(df_extraction)}")
print(f"Total após merge: {len(merged_df)}")

# Ver qual de registros ficaram sem match
print(f"Registros sem match: {merged_df[merged_df.isna().any(axis=1)].shape[0]}")
```


