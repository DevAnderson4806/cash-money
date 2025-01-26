import sqlite3

def inicializar_banco_dados():
    # Conectar ao banco de dados de usuários
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    # Criar tabela de usuários (caso não exista)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0
    )
    """)

    # Adicionar a coluna is_admin (se não existir)
    try:
        cursor.execute('ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT 0')
    except sqlite3.OperationalError:
        # Ignorar se a coluna já existir
        pass

    conn.commit()
    conn.close()

    # Conectar ao banco de dados de finanças
    conn = sqlite3.connect("finanças.db")
    cursor = conn.cursor()

    # Criar tabela de transações (caso não exista)
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

    conn.commit()
    conn.close()

    # Conectar ao banco de dados de planejamento
    conn = sqlite3.connect("planejamento.db")
    cursor = conn.cursor()

    # Criar tabela de planejamento (caso não exista)
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

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso.")

if __name__ == "__main__":
    inicializar_banco_dados()