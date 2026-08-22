import csv
import time
import os
import json
import logging

# Nossas importações modulares
from models import ProcessedTicket
from database import (
    setup_database, 
    insert_raw_ticket, 
    get_pending_tickets, 
    insert_llm_analysis, 
    update_ticket_status
)
from extractor import extract_information_via_api

# Configuração global de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def worker_process_pending() -> None:
    tickets = get_pending_tickets()
    
    if not tickets:
        logger.info("No pending tickets in the queue.")
        return
        
    logger.info(f"Starting processing of {len(tickets)} pending tickets...")
    current_model = "gemini-3.6-flash"
    
    for ticket_id, client_text in tickets:
        try:
            json_data = extract_information_via_api(client_text, current_model)
            
            if isinstance(json_data, str):
                json_data = json.loads(json_data)
                
            processed_ticket = ProcessedTicket(
                category=json_data.get("category", "Desconhecida"),
                involved_value=json_data.get("involved_value"),
                sentiment=json_data.get("sentiment", "Neutro")
            )
            
            insert_llm_analysis(ticket_id, processed_ticket, current_model)
            update_ticket_status(ticket_id, "CONCLUIDO")
            logger.info(f"Ticket {ticket_id} processed successfully!")
            
        except json.JSONDecodeError:
            logger.error(f"JSON error in ticket {ticket_id}.")
            update_ticket_status(ticket_id, "ERRO")
            
        except Exception as e:
            logger.error(f"Unexpected error in ticket {ticket_id}: {e}")
            update_ticket_status(ticket_id, "ERRO")
            
            if "429" in str(e):
                logger.warning("API limit reached. Pausing for 30 seconds...")
                time.sleep(30)
                
        time.sleep(4)

def ingest_data_from_csv(file_path: str) -> None:
    # Checks if the file exists. If not, logs and exits.
    if not os.path.exists(file_path):
        logger.info(f"Nenhum arquivo novo para ingerir. Pulando etapa: {file_path}")
        return

    logger.info(f"--- STARTING INGESTION OF FILE: {file_path} ---")
    
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        target_column = "client_text" 
        
        counter = 0
        for row in reader:
            client_text = row.get(target_column)
            if client_text: 
                insert_raw_ticket(client_text)
                counter += 1
                
    logger.info(f"Ingestion completed. {counter} records added to the queue.")
    
    # Rename the processed file to avoid reprocessing - ensure idempotency
    processed_path = file_path.replace(".csv", "_processado.csv")
    os.rename(file_path, processed_path)
    logger.info(f"Arquivo arquivado como '{processed_path}' para evitar duplicidade.")

if __name__ == "__main__":
    setup_database()
    
    logger.info("--- STARTING INGESTION PHASE ---")
    ingest_data_from_csv("synthetic_dataset.csv")

    logger.info("--- STARTING PROCESSING PHASE (AI) ---")
    worker_process_pending()