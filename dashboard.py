import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# import the functions from other modules
from agent import ask_database
from main import ingest_data_from_csv, worker_process_pending

# PAGE CONFIGURATION
st.set_page_config(page_title="Banking AI Assistant", page_icon="🏦", layout="wide")
DB_NAME = "banking_tickets.db"

# DATA EXTRACTION (CACHED)
@st.cache_data(ttl=60)
def load_overview_data():
    """Loads validated data for the static Overview tab."""
    if not os.path.exists(DB_NAME):
        return pd.DataFrame()
        
    query = """
    SELECT a.category, a.involved_value, a.sentiment, t.client_text
    FROM tickets t
    JOIN llm_analyses a ON t.ticket_id = a.ticket_id
    WHERE t.processing_status = 'CONCLUIDO'
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# UI LAYOUT & TABS
st.title("🏦 AI Ticket Intelligence")
st.markdown("Analyze customer complaints, upload new batches, or ask natural language questions.")

# Creates the 2 tabs exactly as you requested
tab1, tab2 = st.tabs(["📊 Overview", "🤖 AI Chat Assistant"])

# TAB 1: OVERVIEW (Static & Descriptive)
with tab1:
    df = load_overview_data()
    
    if df.empty:
        st.info("No processed data available yet. Please upload a file in the next tab.")
    else:
        # Fixed KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tickets Processed", len(df))
        col2.metric("Total Financial Volume", f"$ {df['involved_value'].sum():,.2f}")
        col3.metric("Main Sentiment", df['sentiment'].mode()[0])
        
        st.divider()
        
        # Fixed Descriptive Charts
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("Tickets by Category")
            fig_pie = px.pie(df, names='category', hole=0.4)
            st.plotly_chart(fig_pie, width="stretch")
            
        with chart_col2:
            st.subheader("Sentiment Distribution")
            fig_bar = px.histogram(df, x='category', color='sentiment', barmode='group')
            st.plotly_chart(fig_bar, width="stretch")

# TAB 2: AI CHAT (Text-to-SQL)
with tab2:
    st.subheader("Ask the Database")
    st.markdown("Type your question in natural language and the AI will query the SQLite database for you.")
    
    # Simple chat layout
    user_query = st.chat_input("Ex: Qual é a média de valor dos chamados de Pix?")
    
    if user_query:
        # Show user message
        with st.chat_message("user"):
            st.write(user_query)
            
        # Show AI thinking and result
        with st.chat_message("assistant"):
            with st.spinner("Translating to SQL and fetching data..."):
                result_df = ask_database(user_query)
                
                if not result_df.empty:
                    st.dataframe(result_df, width="stretch")
                    st.caption("✅ Query generated and executed successfully.")
                else:
                    st.warning("No data found or the AI couldn't generate a valid query.")
