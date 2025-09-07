import psycopg2
from psycopg2 import OperationalError
import pandas as pd
from sqlalchemy import create_engine
import os
import glob
from pathlib import Path # Importa Path para manipulação de caminhos

# --- Configurações do Banco de Dados ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb"
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# --- Diretório de Saída para CSVs ---
# Define o diretório base para salvar os arquivos Excel filtrados.
# O 'r' antes da string garante que backslashes sejam tratados como literais.
OUTPUT_DIR_BASE = Path(r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\comfiltro")

# Lista de ministérios (nomes das tabelas no banco de dados)
# Ajustado para usar a capitalização correta dos nomes das tabelas no PostgreSQL.
# As tabelas MINISTERIO_DAS_CIDADES, MINISTERIO_DA_EDUCACAO e MINISTERIO_DA_SAUDE
# são presumidas como tendo sido criadas em maiúsculas.
ministerios = [
    "ministerio_da_defesa",
    "ministerio_da_pesca_e_aquicultura",
    "ministerio_da_ciencia_tecnologia_e_inovacao",
    "ministerio_da_gestao_e_da_inovacao_em_servicos_publicos",
    "ministerio_da_cultura",
    "ministerio_da_justica_e_seguranca_publica",
    "ministerio_do_turismo",
    "ministerio_da_economia",
    "ministerio_das_comunicacoes",
    "ministerio_das_mulheres",
    "ministerio_de_minas_e_energia",
    "ministerio_de_portos_e_aeroportos",
    "ministerio_da_infraestrutura",
    "ministerio_do_esporte",
    "presidencia_da_republica",
    "sec_esp_de_agric_fam_e_desenv_agrario",
    "ministerio_do_desenvolvimento_e_assistencia_social_familiar_e_combate_a_fome",
    "ministerio_do_desenvolvimento_agrario_e_da_agricultura_familiar",
    "ministerio_do_desenvolvimento_industria_comercio_e_servicos",
    "ministerio_do_meio_ambiente",
    "ministerio_do_trabalho_e_emprego",
    "ministerio_do_desenvolvimento_regional",
    "MINISTERIO_DAS_CIDADES", # Ajustado para maiúsculas
    "MINISTERIO_DA_EDUCACAO", # Ajustado para maiúsculas
    "MINISTERIO_DA_SAUDE"    # Ajustado para maiúsculas
]

def sanitize_folder_name(name):
    """
    Sanitiza uma string para ser usada como nome de pasta, removendo caracteres inválidos.
    """
    if pd.isna(name): # Verifica se o nome é NaN (Not a Number) ou similar
        return "sem_orgao_superior" # Nome padrão para órgãos superiores ausentes

    # Substitui caracteres especiais por underscore e remove múltiplos underscores
    sanitized = str(name).lower().strip()
    sanitized = ''.join(c if c.isalnum() or c == ' ' else '_' for c in sanitized)
    sanitized = '_'.join(filter(None, sanitized.split(' '))) # Divide por espaço, filtra vazios e junta com '_'
    sanitized = '_'.join(filter(None, sanitized.split('_'))) # Remove múltiplos underscores

    # Limita o tamanho do nome da pasta para evitar caminhos muito longos
    return sanitized[:100] if sanitized else "nome_invalido"


def query_ministry_data():
    """
    Conecta ao banco de dados 'minhas_obras', itera sobre as tabelas dos ministérios,
    filtra os dados, seleciona apenas 'nº_instrumento' e 'situação_atual',
    e salva os resultados em novas tabelas no DB e em arquivos Excel (.xlsx).
    """
    try:
        # Cria a engine de conexão com o banco de dados
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print(f"Conexão com o banco de dados '{TARGET_DB_NAME}' estabelecida para consulta e carga.")
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}': {e}")
        print("Certifique-se de que o banco de dados está online e acessível com as credenciais fornecidas.")
        return

    print("\nIniciando a consulta, filtragem e exportação dos dados dos ministérios...")

    # Cria o diretório base para os Excel se ele não existir
    OUTPUT_DIR_BASE.mkdir(parents=True, exist_ok=True)
    print(f"Diretório de saída para Excel: '{OUTPUT_DIR_BASE}'")

    for ministerio in ministerios:
        print(f"\n--- Processando tabela: '{ministerio}' ---")
        try:
            # Construindo a query SQL para filtrar os dados
            query = f"""
            SELECT *
            FROM "{ministerio}"
            WHERE "situação_atual" = 'Em Execução'
              AND LENGTH(CAST("nº_instrumento" AS TEXT)) = 6
              AND CAST("nº_instrumento" AS TEXT) ~ '^[0-9]{{6}}$';
            """

            df_filtered = pd.read_sql(query, engine)

            if not df_filtered.empty:
                print(f"  {len(df_filtered)} registros 'Em Execução' e com 'nº_instrumento' de 6 dígitos encontrados para '{ministerio}'.")

                # Seleciona apenas as colunas desejadas para o output e para a nova tabela do DB
                # Garante que as colunas existem antes de tentar selecioná-las
                required_columns = ["nº_instrumento", "situação_atual"]
                available_columns = [col for col in required_columns if col in df_filtered.columns]

                if len(available_columns) != len(required_columns):
                    print(f"  AVISO: Uma ou mais colunas necessárias ({required_columns}) não foram encontradas na tabela '{ministerio}'. Pulando o salvamento/exportação para este ministério.")
                    continue

                df_output_columns = df_filtered[available_columns]


                # 1. Salvar em uma nova tabela no banco de dados com apenas as colunas especificadas
                new_table_name = f"{ministerio}_filtrado_simplificado" # Nome diferente para evitar conflito com filtros anteriores
                df_output_columns.to_sql(name=new_table_name, con=engine, if_exists='replace', index=False)
                print(f"  Dados filtrados (apenas '{', '.join(available_columns)}') salvos na nova tabela do banco de dados: '{new_table_name}'.")

                # 2. Exportar para Excel (.xlsx) organizado por 'orgao_superior'
                # A lógica de organização por 'orgao_superior' ainda usa a coluna do df_filtered original
                if 'orgao_superior' in df_filtered.columns:
                    unique_orgaos = df_filtered['orgao_superior'].unique()
                    print(f"  Exportando Excel por Órgão Superior para '{ministerio}'...")
                    for orgao_sup in unique_orgaos:
                        # Sanitiza o nome do órgão superior para ser um nome de pasta válido
                        sanitized_orgao_sup_name = sanitize_folder_name(orgao_sup)
                        
                        # Define o caminho completo da pasta para este órgão superior
                        orgao_output_dir = OUTPUT_DIR_BASE / sanitized_orgao_sup_name
                        orgao_output_dir.mkdir(parents=True, exist_ok=True) # Cria a pasta se não existir

                        # Filtra o DataFrame original pelo órgão superior e então seleciona as colunas de output
                        df_orgao = df_filtered[df_filtered['orgao_superior'] == orgao_sup][available_columns]
                        
                        # Define o caminho completo do arquivo Excel
                        excel_path = orgao_output_dir / f"{ministerio}.xlsx"
                        
                        # Salva o DataFrame como Excel
                        df_orgao.to_excel(excel_path, index=False) # to_excel não usa 'encoding'
                        print(f"    - '{len(df_orgao)}' registros para '{orgao_sup}' (Excel: '{excel_path.name}')")
                else:
                    print("  AVISO: Coluna 'orgao_superior' não encontrada nos dados filtrados para exportação Excel por órgão.")
                    # Se não houver 'orgao_superior', salva tudo em uma pasta genérica do ministério
                    sanitized_ministry_name = sanitize_folder_name(ministerio)
                    ministry_output_dir = OUTPUT_DIR_BASE / sanitized_ministry_name
                    ministry_output_dir.mkdir(parents=True, exist_ok=True)
                    excel_path_all = ministry_output_dir / f"{ministerio}_todos.xlsx"
                    df_output_columns.to_excel(excel_path_all, index=False)
                    print(f"  Dados filtrados de '{ministerio}' (apenas '{', '.join(available_columns)}') salvos em '{excel_path_all.name}' na pasta do ministério, pois 'orgao_superior' não foi encontrada.")

            else:
                print(f"  Nenhum registro encontrado para '{ministerio}' com os critérios especificados. Nenhuma nova tabela ou Excel criado.")

        except KeyError as ke:
            print(f"  ERRO de coluna: A coluna '{ke}' não foi encontrada na tabela '{ministerio}'. Verifique se os nomes das colunas estão corretos.")
        except Exception as e:
            print(f"  ERRO inesperado ao processar '{ministerio}': {e}")
            print("  Verifique se a tabela existe e se as colunas 'situação_atual' e 'nº_instrumento' estão corretas e no formato esperado.")

    print("\nProcessamento completo para todos os ministérios: tabelas no DB e Excel exportados.")

if __name__ == "__main__":
    query_ministry_data()
