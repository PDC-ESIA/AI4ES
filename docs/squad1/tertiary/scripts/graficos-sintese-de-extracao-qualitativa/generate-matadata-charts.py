import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

# Configurações de estilo
sns.set_theme(style="whitegrid")

def clean_vehicle_name(name):
    if not isinstance(name, str): return "N/A"
    # Remover anos entre parênteses ou no final da string
    name = re.sub(r'\(\d{4}\)', '', name)
    name = re.sub(r'\d{4}', '', name)
    return name.strip()

def generate_metadata_visualizations(csv_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df = pd.read_csv(csv_file)
    
    # 1. Países (Explodir se houver múltiplos separados por vírgula ou ponto e vírgula)
    if 'País' in df.columns:
        countries = df['País'].dropna().str.replace(';', ',').str.split(',').explode().str.strip()
        country_counts = countries.value_counts().head(10)
        plt.figure(figsize=(12, 7))
        sns.barplot(x=country_counts.values, y=country_counts.index, palette='flare', hue=country_counts.index, legend=False)
        plt.title('Top 10 Países por Publicação', fontsize=16)
        plt.xlabel('Quantidade de Artigos', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_paises.png'), bbox_inches='tight')
        plt.close()

    # 2. Afiliação (Top 10)
    if 'Afiliação' in df.columns:
        affiliations = df['Afiliação'].dropna().str.split(';').explode().str.strip()
        aff_counts = affiliations.value_counts().head(10)
        plt.figure(figsize=(12, 7))
        sns.barplot(x=aff_counts.values, y=aff_counts.index, palette='crest', hue=aff_counts.index, legend=False)
        plt.title('Top 10 Afiliações', fontsize=16)
        plt.xlabel('Quantidade de Artigos', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_afiliacoes.png'), bbox_inches='tight')
        plt.close()

    # 3. Autores (Top 10)
    if 'Autores' in df.columns:
        authors = df['Autores'].dropna().str.replace(' and ', ',').str.split(',').explode().str.strip()
        author_counts = authors.value_counts().head(10)
        plt.figure(figsize=(12, 7))
        sns.barplot(x=author_counts.values, y=author_counts.index, palette='magma', hue=author_counts.index, legend=False)
        plt.title('Top 10 Autores mais Produtivos', fontsize=16)
        plt.xlabel('Quantidade de Artigos', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_autores.png'), bbox_inches='tight')
        plt.close()

    # 4. Ano de Publicação
    if 'Ano' in df.columns:
        year_counts = df['Ano'].dropna().astype(int).value_counts().sort_index()
        plt.figure(figsize=(10, 6))
        sns.lineplot(x=year_counts.index.astype(str), y=year_counts.values, marker='o', color='#10B981', linewidth=3)
        plt.fill_between(year_counts.index.astype(str), year_counts.values, alpha=0.2, color='#10B981')
        plt.title('Evolução Temporal das Publicações', fontsize=16)
        plt.ylabel('Quantidade de Artigos', fontsize=12)
        plt.xlabel('Ano', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'evolucao_temporal.png'), bbox_inches='tight')
        plt.close()

    # 5. Veículo de Publicação (Limpo)
    if 'Veículo de Publicação' in df.columns:
        df['Veiculo_Limpo'] = df['Veículo de Publicação'].apply(clean_vehicle_name)
        vehicle_counts = df['Veiculo_Limpo'].value_counts().head(10)
        plt.figure(figsize=(12, 7))
        sns.barplot(x=vehicle_counts.values, y=vehicle_counts.index, palette='viridis', hue=vehicle_counts.index, legend=False)
        plt.title('Top 10 Veículos de Publicação', fontsize=16)
        plt.xlabel('Quantidade de Artigos', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_veiculos.png'), bbox_inches='tight')
        plt.close()

    # 6. Tipo de Veículo
    if 'Tipo ' in df.columns: # Note o espaço no final da coluna identificado no read_excel
        type_counts = df['Tipo '].value_counts()
        plt.figure(figsize=(8, 8))
        plt.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette('pastel'))
        plt.title('Distribuição por Tipo de Veículo', fontsize=16)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'tipo_veiculo.png'), bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    generate_metadata_visualizations('/home/ubuntu/artigos_consolidado.csv', '/home/ubuntu/charts_metadata')
    print("Gráficos de metadados gerados com sucesso.")