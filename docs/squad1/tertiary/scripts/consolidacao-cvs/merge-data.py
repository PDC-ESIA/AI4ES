import pandas as pd
import os
import re

def normalize_title(title):
    if not isinstance(title, str):
        return ""
    # Remover caracteres especiais, espaços extras e converter para minúsculas
    title = title.lower()
    title = re.sub(r'[^a-z0-9]', '', title)
    return title

def merge_data(quality_csv, extraction_xls, output_csv, output_excel):
    # Carregar dados de qualidade (Scopus Only)
    df_quality = pd.read_csv(quality_csv)
    
    # Carregar dados de extração
    df_extraction = pd.read_excel(extraction_xls)
    
    # Normalizar títulos para o merge
    df_quality['title_norm'] = df_quality['Artigo'].apply(normalize_title)
    df_extraction['title_norm'] = df_extraction['article'].apply(normalize_title)
    
    # Realizar o merge
    # Queremos manter todos os 68 artigos do Scopus (df_quality)
    # e trazer as colunas do df_extraction
    merged_df = pd.merge(
        df_quality, 
        df_extraction.drop(columns=['Ano']), # Remover 'Ano' da extração para evitar duplicata
        on='title_norm', 
        how='left'
    )
    
    # Remover a coluna de normalização
    merged_df = merged_df.drop(columns=['title_norm', 'article'])
    
    # Reordenar colunas para ficar organizado
    # ID, Artigo, Ano, Score Total, Fonte, Q1-Q7, depois as colunas da extração
    cols = list(merged_df.columns)
    
    # Salvar CSV
    merged_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    # Salvar Excel
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        merged_df.to_excel(writer, index=False, sheet_name='Dados Consolidados')
        
        # Adicionar legenda de perguntas
        questions_map = {
            "Q1": "Does the search cover all relevant studies?",
            "Q2": "Are the inclusion and exclusion criteria properly described?",
            "Q3": "Is the quality of included primary studies assessed?",
            "Q4": "Are primary studies adequately described?",
            "Q5": "Is the justification for the study adequately described?",
            "Q6": "Is the protocol validation properly described?",
            "Q7": "Is data extraction properly described and appropriate?"
        }
        legenda = pd.DataFrame([{"ID": k, "Pergunta": v} for k, v in questions_map.items()])
        legenda.to_excel(writer, index=False, sheet_name='Legenda Qualidade')

    print(f"Merge concluído. Total de linhas: {len(merged_df)}")
    
    # Verificar quantos deram match
    matches = merged_df['Quem extraiu'].notna().sum()
    print(f"Artigos com dados de extração encontrados: {matches} de {len(df_quality)}")
    
    return merged_df

if __name__ == "__main__":
    merge_data(
        '/home/ubuntu/artigos_scopus_only.csv', 
        '/home/ubuntu/upload/data_extraction.xls', 
        '/home/ubuntu/artigos_consolidado.csv', 
        '/home/ubuntu/artigos_consolidado.xlsx'
    )