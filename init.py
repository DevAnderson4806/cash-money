import sqlite3

def inicializar_banco_dados():
    # Conectar ao banco de dados de usuários
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    # Criar tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    """)

    # Conectar ao banco de dados de finanças
    conn = sqlite3.connect("finanças.db")
    cursor = conn.cursor()

    # Criar tabela de transações
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        tipo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        data TEXT NOT NULL
    )
    """)

    # Conectar ao banco de dados de planejamento
    conn = sqlite3.connect("planejamento.db")
    cursor = conn.cursor()

    # Criar tabela de planejamento
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planejamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        descricao TEXT NOT NULL,
        valor_meta REAL NOT NULL,
        valor_atual REAL DEFAULT 0,
        prazo TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES usuarios (id)
    )
    """)

    # Commit e fechar conexão
    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso.")

if __name__ == "__main__":
    inicializar_banco_dados()