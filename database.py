import csv
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
import sqlite3
import json
import os
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple

# ---------------------------------------------------------
# 1. INITIAL CONFIGURATIONS AND BEST PRACTICES
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
DB_NAME = "banco_bancario.db"

# Instantiating the client (global scope)
client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# 2. DATA MODELING (DATA CONTRACTS)
# ---------------------------------------------------------

@dataclass
class ProcessedTicket:
    """Structure that defines the data contract returned by the AI."""
    category: str        
    involved_value: Optional[float] 
    sentiment: str       

# ---------------------------------------------------------
# 3. DATABASE LAYER (SQLITE) - MEDALLION ARCHITECTURE
# ---------------------------------------------------------

def setup_database(db_path: str = DB_NAME) -> None:
    """Creates the raw data and processed data (LLM) tables."""
    
    query_tickets_table = """
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_text TEXT NOT NULL,
        received_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processing_status TEXT DEFAULT 'PENDENTE'
    )
    """
    
    query_llm_table = """
    CREATE TABLE IF NOT EXISTS llm_analyses (
        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        category TEXT,
        involved_value REAL,
        sentiment TEXT,
        llm_model TEXT,
        analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
    )
    """
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Enable Foreign Keys support in SQLite (disabled by default)
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            cursor.execute(query_tickets_table)
            cursor.execute(query_llm_table)
            conn.commit()
            logger.info("Database configured with two tables (Raw and Analyses).")
    except sqlite3.Error as e:
        logger.error(f"Error configuring the database: {e}")
        raise

def insert_raw_ticket(text: str, db_path: str = DB_NAME) -> None:
    """Phase 1: Saves the original text with 'PENDENTE' status."""
    query = "INSERT INTO tickets (client_text) VALUES (?)"
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(query, (text,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error inserting raw ticket: {e}")

def get_pending_tickets(db_path: str = DB_NAME) -> List[Tuple[int, str]]:
    """Fetches all tickets that have not yet passed through the LLM."""
    query = "SELECT ticket_id, client_text FROM tickets WHERE processing_status = 'PENDENTE'"
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Error fetching pending tickets: {e}")
        return []

def insert_llm_analysis(ticket_id: int, ticket: ProcessedTicket, model: str, db_path: str = DB_NAME) -> None:
    """Phase 2: Inserts the analysis linked to the raw ticket ID."""
    query = """
    INSERT INTO llm_analyses (ticket_id, category, involved_value, sentiment, llm_model)
    VALUES (?, ?, ?, ?, ?)
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(query, (ticket_id, ticket.category, ticket.involved_value, ticket.sentiment, model))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error inserting LLM analysis: {e}")
        raise # Raise the error for the main worker to handle

def update_ticket_status(ticket_id: int, status: str, db_path: str = DB_NAME) -> None:
    """Updates the ticket status in the raw table (CONCLUIDO or ERRO)."""
    query = "UPDATE tickets SET processing_status = ? WHERE ticket_id = ?"
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(query, (status, ticket_id))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error updating ticket {ticket_id} status: {e}")

# ---------------------------------------------------------
# 4. INTELLIGENCE LAYER (NLP / LLM API)
# ---------------------------------------------------------

def extract_information_via_api(text: str, model: str = "gemini-3.5-flash") -> dict:
    """
    Sends the text to the API and ensures the return is in strict JSON.
    """
    system_prompt = """
    Você é um extrator de dados transacionais bancários. 
    Sua única função é receber o texto do cliente e retornar EXCLUSIVAMENTE um objeto JSON válido.
    NÃO inclua saudações, NÃO inclua explicações, NÃO envolva a resposta em blocos de código markdown.
    
    Esquema JSON obrigatório:
    {
      "category": "string (Pix, Cartão, Empréstimo, Atendimento, Outros)",
      "involved_value": "float (use null se nenhum valor for mencionado)",
      "sentiment": "string (Positivo, Negativo, Neutro)"
    }
    
    Exemplo 1:
    Entrada: "Fiz um pix de R$ 150,50 ontem mas não caiu na conta, estou revoltado!"
    Saída: {"category": "Pix", "involved_value": 150.50, "sentiment": "Negativo"}
    
    Exemplo 2:
    Entrada: "O gerente João foi muito educado hoje."
    Saída: {"category": "Atendimento", "involved_value": null, "sentiment": "Positivo"}
    """
    logger.info("Sending text for analysis in LLM...")
    
    try:
        # The actual API call
        response = client.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\nEntrada: {text}\nSaída: ",
            config=types.GenerateContentConfig(
                response_mime_type="application/json", # The Gemini lock
                temperature=0.0, # Zero creativity
            ),
        )
        
        # Extracts the string returned by the model
        content_str = response.text

        # DEFENSIVE PROGRAMMING: Fallback cleaning        
        clean_content = content_str.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
            
        # Converts the clean string to a Python dictionary
        return json.loads(clean_content.strip())
        
    except Exception as e:
        # If the API goes down, times out, or the request limit is exceeded,
        # we log the error and raise it so the worker_process_pending()
        # can mark the row in the database as 'ERRO'.
        logger.error(f"Failed to communicate with LLM: {e}")
        raise
    
# ---------------------------------------------------------
# 5. ORCHESTRATION (MAIN PIPELINE)
# ---------------------------------------------------------

def worker_process_pending() -> None:
    """
    The Maestro: Consumes the PENDENTE queue, passes it through LLM, and saves the results.
    """
    tickets = get_pending_tickets()
    
    if not tickets:
        logger.info("No pending tickets in the queue.")
        return
        
    logger.info(f"Starting processing of {len(tickets)} pending tickets...")
    current_model = "gemini-1.5-flash" # model name for traceability 
    
    for ticket_id, client_text in tickets:
        try:
            # 1. Hit the API
            json_data = extract_information_via_api(client_text)
            
            if isinstance(json_data, str):
                json_data = json.loads(json_data)
                
            # 2. Validate in the Data Contract
            processed_ticket = ProcessedTicket(
                category=json_data.get("category", "Desconhecida"),
                involved_value=json_data.get("involved_value"),
                sentiment=json_data.get("sentiment", "Neutro")
            )
            
            # 3. Save the LLM response in the llm_analyses table
            insert_llm_analysis(ticket_id, processed_ticket, current_model)
            
            # 4. Mark as CONCLUIDO in the tickets table
            update_ticket_status(ticket_id, "CONCLUIDO")
            logger.info(f"Ticket {ticket_id} processed successfully!")
            
        except json.JSONDecodeError:
            logger.error(f"JSON error in ticket {ticket_id}.")
            update_ticket_status(ticket_id, "ERRO")
            
        except Exception as e:
            logger.error(f"Unexpected error in ticket {ticket_id}: {e}")
            update_ticket_status(ticket_id, "ERRO")
            
            # If the error is rate limit (429), we apply 'Exponential Backoff'
            if "429" in str(e):
                logger.warning("API limit reached. Pausing for 30 seconds...")
                time.sleep(30)
                
        # Mandatory breath for free accounts (15 Requests Per Minute = 1 every 4 sec)
        time.sleep(4)

# ---------------------------------------------------------
# 6. EXECUTION
# ---------------------------------------------------------

# ---------------------------------------------------------
# 6.1 Data Ingestion (csv - Reclame Aqui)

def ingest_data_from_csv(file_path: str) -> None:
    """
    Reads a CSV file and sends the rows to the raw ingestion table.
    We assume the CSV has a column named 'client_text' (or 'texto_cliente' originally).
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    logger.info(f"--- STARTING INGESTION OF FILE: {file_path} ---")
    
    # encoding='utf-8' is vital for reading Portuguese accents correctly
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
    
        target_column = "client_text" 
        
        counter = 0
        for row in reader:
            client_text = row.get(target_column)
            
            if client_text: # Ignores empty lines
                insert_raw_ticket(client_text)
                counter += 1
                
        logger.info(f"Ingestion completed. {counter} records added to the queue.")

# ---------------------------------------------------------

if __name__ == "__main__":
    # 1. Initializes the database with the two-table structure
    setup_database()
    
    # 2. We receive new comments (Ingestion)
    logger.info("--- STARTING INGESTION PHASE ---")
    ingest_data_from_csv("synthetic_dataset.csv")

    # 3. We process the queue (Enrichment)
    logger.info("--- STARTING PROCESSING PHASE (AI) ---")
    worker_process_pending()
