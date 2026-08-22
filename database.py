import sqlite3
import logging
from typing import List, Tuple
from models import ProcessedTicket

logger = logging.getLogger(__name__)
DB_NAME = "banking_tickets.db"

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
    query = "INSERT INTO tickets (client_text) VALUES (?)"
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(query, (text,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error inserting raw ticket: {e}")

def get_pending_tickets(db_path: str = DB_NAME) -> List[Tuple[int, str]]:
    query = "SELECT ticket_id, client_text FROM tickets WHERE processing_status IN ('PENDENTE', 'ERRO')"
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Error fetching pending tickets: {e}")
        return []

def insert_llm_analysis(ticket_id: int, ticket: ProcessedTicket, model: str, db_path: str = DB_NAME) -> None:
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
        raise

def update_ticket_status(ticket_id: int, status: str, db_path: str = DB_NAME) -> None:
    query = "UPDATE tickets SET processing_status = ? WHERE ticket_id = ?"
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(query, (status, ticket_id))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error updating ticket {ticket_id} status: {e}")
