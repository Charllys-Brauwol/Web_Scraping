import pandas as pd
from sqlalchemy import create_engine

def excel_to_database(novo_caminho_do_arquivo, orgao, db_params):
    connection = None
    try:
        # Ler o arquivo Excel
        df = pd.read_excel(novo_caminho_do_arquivo)

        # Conectar ao banco de dados
        engine = create_engine(f'postgresql://{db_params["user"]}:{db_params["password"]}@{db_params["host"]}:{db_params["port"]}/{db_params["database"]}')
        connection = engine.raw_connection()

        # Inserir dados no banco de dados
        df.to_sql(orgao, con=engine, if_exists='replace', index=False)

        # Confirmar a transação
        connection.commit()
        print("Dados inseridos com sucesso!")

    except Exception as e:
        print(f"Erro ao inserir dados no banco de dados: {e}")

    finally:
        # Fechar conexão
        if connection:
            connection.close()
            print("Conexão encerrada.")
