import pandas as pd
from bs4 import BeautifulSoup
import re
import os

def extract_all_finished(html_file, output_csv, output_excel):
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    articles_data = []
    
    # Encontrar todos os containers de artigos
    # A estrutura identificada é <div class="panel panel-default panel-quality-assessment">
    article_containers = soup.find_all('div', class_='panel-quality-assessment')
    
    # Mapeamento de perguntas para IDs (Q1-Q7)
    questions_map = {
        "Does the search cover all relevant studies?": "Q1",
        "Are the inclusion and exclusion criteria properly described?": "Q2",
        "Is the quality of included primary studies assessed?": "Q3",
        "Are primary studies adequately described?": "Q4",
        "Is the justification for the study adequately described?": "Q5",
        "Is the protocol validation properly described?": "Q6",
        "Is data extraction properly described and appropriate?": "Q7"
    }

    for idx, container in enumerate(article_containers, 1):
        # Codificação A1, A2, etc.
        article_id = f"A{idx}"
        
        # Título do artigo e Ano
        # <h3 class="panel-title">Título <small>(Ano)</small><span class="badge score pull-right">Score</span></h3>
        title_h3 = container.find('h3', class_='panel-title')
        if title_h3:
            # Remover o small e o span para pegar só o texto do título
            small_tag = title_h3.find('small')
            year = small_tag.get_text(strip=True).strip('()') if small_tag else "N/A"
            
            score_tag = title_h3.find('span', class_='badge')
            score = score_tag.get_text(strip=True) if score_tag else "0.0"
            
            # Clonar para não alterar o original ao remover tags
            import copy
            temp_h3 = copy.copy(title_h3)
            if temp_h3.find('small'): temp_h3.find('small').decompose()
            if temp_h3.find('span'): temp_h3.find('span').decompose()
            title = temp_h3.get_text(strip=True)
        else:
            title = f"Artigo {idx}"
            year = "N/A"
            score = "0.0"
        
        # Identificar Fonte (Arxiv = 4623, Scopus = 4626)
        table = container.find('table', id='tbl-quality') or container.find_next('table', id='tbl-quality')
        raw_id = table['article-id'] if table and table.has_attr('article-id') else ""
        fonte = "Arxiv" if raw_id.startswith("4623") else "Scopus"

        # Respostas Q1-Q7
        row_data = {
            "ID": article_id,
            "Artigo": title,
            "Ano": year,
            "Score Total": score,
            "Fonte": fonte
        }
        
        # Inicializar Q1-Q7 como N/A
        for q in range(1, 8):
            row_data[f"Q{q}"] = None # Usar None para facilitar identificação de vazios
            
        # Extrair respostas da tabela
        # A resposta selecionada tem a classe 'selected-answer'
        table = container.find_next_sibling('table') or container.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    q_text = cols[0].get_text(strip=True)
                    
                    # Encontrar qual das colunas de resposta tem a classe 'selected-answer'
                    selected_td = row.find('td', class_='selected-answer')
                    ans_text = selected_td.get_text(strip=True) if selected_td else None
                    
                    # Mapear para Q1-Q7
                    for full_q, q_id in questions_map.items():
                        if full_q in q_text:
                            row_data[q_id] = ans_text
                            break
                            
        articles_data.append(row_data)

    # Criar DataFrame
    df = pd.DataFrame(articles_data)
    
    # Salvar CSV
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    # Salvar Excel com legenda
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados Extraídos')
        
        # Aba de legenda
        legenda_data = []
        for full_q, q_id in questions_map.items():
            legenda_data.append({"ID": q_id, "Pergunta": full_q})
        legenda = pd.DataFrame(legenda_data).sort_values('ID')
        legenda.to_excel(writer, index=False, sheet_name='Legenda Perguntas')

    print(f"Extração concluída: {len(df)} artigos processados.")
    return df

if __name__ == "__main__":
    html_path = "/home/ubuntu/upload/Conducting·Tertiary-GenAIforSoftwareEngineering-ALL-Finished.html"
    csv_path = "/home/ubuntu/artigos_all_finished.csv"
    excel_path = "/home/ubuntu/artigos_all_finished.xlsx"
    
    extract_all_finished(html_path, csv_path, excel_path)