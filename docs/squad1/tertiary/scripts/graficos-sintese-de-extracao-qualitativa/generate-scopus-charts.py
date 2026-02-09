import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import textwrap

# Configurações de estilo
sns.set_theme(style="whitegrid")

def generate_scopus_visualizations(csv_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df = pd.read_csv(csv_file)
    
    # Filtrar artigos sem respostas (NaN)
    questions = [f'Q{i}' for i in range(1, 8)]
    df_filtered = df[~df[questions].isna().all(axis=1)].copy()
    filtered_count = len(df_filtered)
    print(f"Artigos Scopus totais: {len(df)}. Artigos Scopus com respostas: {filtered_count}")

    questions_map = {
        "Q1": "Does the search cover all relevant studies?",
        "Q2": "Are the inclusion and exclusion criteria properly described?",
        "Q3": "Is the quality of included primary studies assessed?",
        "Q4": "Are primary studies adequately described?",
        "Q5": "Is the justification for the study adequately described?",
        "Q6": "Is the protocol validation properly described?",
        "Q7": "Is data extraction properly described and appropriate?"
    }

    # 1. Gráfico de Barras Horizontais Empilhadas (Qualidade)
    melted_df = df_filtered.melt(id_vars=['ID'], value_vars=questions, var_name='Q_ID', value_name='Resposta')
    melted_df['Pergunta'] = melted_df['Q_ID'].map(questions_map)
    melted_df['Pergunta_Wrapped'] = melted_df['Pergunta'].apply(lambda x: '\n'.join(textwrap.wrap(x, width=50)))
    
    q_order = [questions_map[q] for q in questions]
    q_order_wrapped = ['\n'.join(textwrap.wrap(q, width=50)) for q in q_order]
    
    pivot_counts = melted_df.groupby(['Pergunta_Wrapped', 'Resposta']).size().unstack(fill_value=0)
    pivot_counts = pivot_counts.reindex(q_order_wrapped)
    
    pivot_pct = pivot_counts.div(pivot_counts.sum(axis=1), axis=0) * 100
    
    ans_order = ['Fully attended to', 'Partially attended to', 'Not attended to']
    cols_to_plot = [c for c in ans_order if c in pivot_pct.columns]
    pivot_pct = pivot_pct[cols_to_plot]
    
    ax = pivot_pct.plot(kind='barh', stacked=True, figsize=(15, 10), color=['#2ecc71', '#f1c40f', '#e74c3c'])
    plt.title(f'Qualidade dos Artigos - Scopus (n={filtered_count} avaliados)', fontsize=18, pad=20)
    plt.xlabel('Percentual (%)', fontsize=14)
    plt.ylabel('Critérios de Avaliação', fontsize=14)
    plt.legend(title='Resposta', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=12)
    plt.gca().invert_yaxis()
    
    for p in ax.patches:
        width = p.get_width()
        if width > 5:
            x, y = p.get_xy()
            ax.text(x + width/2, y + p.get_height()/2, f'{width:.1f}%', 
                    ha='center', va='center', fontsize=11, color='white', fontweight='bold')
            
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'qualidade_scopus.png'), bbox_inches='tight')
    plt.close()

    # 2. Distribuição de Scores Totais
    plt.figure(figsize=(10, 6))
    sns.histplot(df_filtered['Score Total'], bins=10, kde=True, color='#3B82F6')
    plt.title(f'Distribuição dos Scores Totais - Scopus (n={filtered_count})', fontsize=16)
    plt.xlabel('Score Total', fontsize=12)
    plt.ylabel('Frequência', fontsize=12)
    
    mean_score = df_filtered['Score Total'].mean()
    plt.axvline(mean_score, color='red', linestyle='--', label=f'Média: {mean_score:.2f}')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'scores_scopus.png'), bbox_inches='tight')
    plt.close()

    # 3. Gráfico de Seleção (Apenas Scopus)
    plt.figure(figsize=(8, 6))
    selection_data = {'Status': ['Aceitos', 'Rejeitados', 'Duplicados'], 'Quantidade': [68, 60, 2]}
    sel_df = pd.DataFrame(selection_data)
    sns.barplot(data=sel_df, x='Status', y='Quantidade', palette=['#2ecc71', '#e74c3c', '#95a5a6'], hue='Status', legend=False)
    plt.title('Status de Seleção - Scopus (Total: 130)', fontsize=16)
    for i, v in enumerate(sel_df['Quantidade']):
        plt.text(i, v + 1, str(v), ha='center', fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'selecao_scopus.png'), bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    generate_scopus_visualizations('/home/ubuntu/artigos_scopus_only.csv', '/home/ubuntu/charts_scopus')