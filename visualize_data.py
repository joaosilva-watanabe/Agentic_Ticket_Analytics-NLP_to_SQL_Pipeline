import sqlite3
import os

DB_NAME = "banking_tickets.db"

def print_database_report():
    """
    Connects to SQLite, joins the raw and processed tables, 
    and prints a formatted report in the terminal.
    """
    if not os.path.exists(DB_NAME):
        print(f"Database '{DB_NAME}' not found. Please run main.py first!")
        return

    query = """
    SELECT 
        t.ticket_id,
        t.processing_status,
        a.category,
        a.involved_value,
        a.sentiment,
        t.client_text
    FROM tickets t
    LEFT JOIN llm_analyses a ON t.ticket_id = a.ticket_id
    ORDER BY t.ticket_id ASC
    """
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                print("The database is empty. Queue might be pending.")
                return

            # Header
            print(f"\n{'ID':<4} | {'STATUS':<10} | {'CATEGORY':<13} | {'VALUE':<12} | {'SENTIMENT':<10} | {'TEXT'}")
            print("-" * 115)
            
            for row in results:
                ticket_id, status, category, value, sentiment, text = row
                
                # Handling Nulls/Nones from Pydantic or pending rows
                cat_str = category if category else "N/A"
                sent_str = sentiment if sentiment else "N/A"
                val_str = f"$ {value:.2f}" if value is not None else "N/A"
                
                # Truncate text for terminal display
                short_text = text[:50] + "..." if text and len(text) > 50 else text
                
                print(f"{ticket_id:<4} | {status:<10} | {cat_str:<13} | {val_str:<12} | {sent_str:<10} | {short_text}")
            print("\n")
            
    except sqlite3.Error as e:
        print(f"Error accessing the database: {e}")

if __name__ == "__main__":
    print_database_report()