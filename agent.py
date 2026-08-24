import sqlite3
import pandas as pd
import os
import logging
from dotenv import load_dotenv
from google import genai

logger = logging.getLogger(__name__)

# API configuration
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
DB_NAME = "banking_tickets.db"

# NLP TO SQL translation layer
def translate_to_sql(natural_query: str, model: str = "gemini-3.6-flash") -> str:
    """
    Translates a natural language question into a SQL query based on the database schema.
    """
    
    # passing the database schema context to the AI
    database_schema = """
    Table 1: tickets (ticket_id, client_text, received_date, processing_status)
    Table 2: llm_analyses (analysis_id, ticket_id, category, involved_value, sentiment, llm_model, analysis_date)
    Note: The 'llm_analyses' table has a foreign key 'ticket_id' referencing the 'tickets' table.
    """
    
    system_prompt = f"""
    You are a Senior SQL Data Analyst. Your task is to take a natural language question 
    (which might be in Portuguese) and return EXCLUSIVELY the SQLite-compatible query to answer it.
    DO NOT use markdown formatting (```sql). DO NOT include explanations. 
    Return ONLY the raw SELECT query text.
    
    Database schema:
    {database_schema}
    """
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\nUser Question: {natural_query}\nSQL Query:",
        )
        
        # Defensive cleaning (in case the model insists on markdown wrapping)
        sql_query = response.text.strip()
        if sql_query.startswith("```sql"): sql_query = sql_query[6:]
        if sql_query.startswith("```"): sql_query = sql_query[3:]
        if sql_query.endswith("```"): sql_query = sql_query[:-3]
            
        return sql_query.strip()
        
    except Exception as e:
        logger.error(f"Error generating SQL from LLM: {e}")
        return ""

# DATABASE EXECUTION layer 
def ask_database(natural_query: str) -> pd.DataFrame:
    """
    Generates the SQL and executes it on the local SQLite database, returning a Pandas DataFrame.
    """
    sql_query = translate_to_sql(natural_query)
    
    if not sql_query:
        return pd.DataFrame()
        
    print(f"\n🤖 AI Generated Query:\n{sql_query}\n")
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            # Basic Security: Prevent the AI from dropping or modifying the database (Read-Only guard)
            upper_query = sql_query.upper()
            if any(forbidden in upper_query for forbidden in ["DROP", "DELETE", "UPDATE", "INSERT"]):
                raise ValueError("Write/Delete operations are not allowed for security reasons. SELECT only.")
                
            return pd.read_sql(sql_query, conn)
            
    except Exception as e:
        logger.error(f"Error executing query on database: {e}")
        return pd.DataFrame()
