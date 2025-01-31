import psycopg2

# Parâmetros de conexão
db_params = {
    'host': 'aula-youtube.c5o6ysg0ci7d.us-east-2.rds.amazonaws.com',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'cb2907cb',
    'port': '5432',  # Normalmente 5432 para PostgreSQL
}

# Inicializar a conexão fora do bloco try
connection = None

# Conectar ao banco de dados
try:
    connection = psycopg2.connect(**db_params)
    cursor = connection.cursor()

    # Exemplo de inserção de dados
    cursor.execute("INSERT INTO usuarios (nome, email) VALUES ('Calors', 'Pedro')")
    
    # Confirmar a transação
    connection.commit()

except (Exception, psycopg2.Error) as error:
    print("Erro ao conectar ao banco de dados:", error)

finally:
    # Fechar conexão e cursor
    if connection:
        cursor.close()
        connection.close()
        print("Conexão encerrada.")
