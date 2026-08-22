import os
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def limpar_ambiente():
    db_file = "banking_tickets.db"
    csv_processado = "synthetic_dataset_processado.csv"
    csv_original = "synthetic_dataset.csv"

    print("Iniciando limpeza do ambiente de testes...\n")

    # 1. Apaga o banco de dados
    if os.path.exists(db_file):
        os.remove(db_file)
        logging.info(f"Banco de dados '{db_file}' deletado.")
    else:
        logging.info(f"Banco de dados não encontrado (já estava limpo).")

    # 2. Restaura o CSV
    if os.path.exists(csv_processado):
        os.rename(csv_processado, csv_original)
        logging.info(f"Arquivo '{csv_processado}' renomeado de volta para '{csv_original}'.")
    else:
        logging.info(f"CSV processado não encontrado.")

    print("\n mbiente resetado com sucesso! Pode rodar 'python main.py'.")

if __name__ == "__main__":
    limpar_ambiente()