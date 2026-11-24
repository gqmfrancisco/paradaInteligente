import sqlite3
from datetime import datetime

BANCO = "historico.db"


# Cria a tabela de umidade
def inicializar_banco():
    with sqlite3.connect(BANCO) as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS leituras_umidade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                umidade REAL NOT NULL,
                data_hora TEXT NOT NULL
            )
        """)


# Salva uma leitura no banco
def salvar_leitura(umidade):
    with sqlite3.connect(BANCO) as conexao:
        conexao.execute("""
            INSERT INTO leituras_umidade (umidade, data_hora)
            VALUES (?, ?)
        """, (
            umidade,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ))


# Retorna as últimas 50 leituras
def obter_historico():
    with sqlite3.connect(BANCO) as conexao:
        conexao.row_factory = sqlite3.Row

        registros = conexao.execute("""
            SELECT * FROM leituras_umidade
            ORDER BY id DESC
            LIMIT 50
        """).fetchall()

        return [dict(registro) for registro in registros]


if __name__ == "__main__":
    inicializar_banco()
    print("Banco de dados inicializado!")