import os
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def reset_environment():
    db_file = "banking_tickets.db"
    csv_processado = "synthetic_dataset_processado.csv"
    csv_original = "synthetic_dataset.csv"

    print("Starting test environment cleanup...\n")

    # 1. Delete the database
    if os.path.exists(db_file):
        os.remove(db_file)
        logging.info(f"Database '{db_file}' deleted.")
    else:
        logging.info("Database not found (already clean).")

    # 2. Restore the CSV
    if os.path.exists(csv_processado):
        os.rename(csv_processado, csv_original)
        logging.info(f"File '{csv_processado}' renamed back to '{csv_original}'.")
    else:
        logging.info("Processed CSV not found.")

    print("\nEnvironment reset successfully! You can run 'python main.py'.")

if __name__ == "__main__":
    reset_environment()