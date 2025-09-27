import os
import sqlite3
import urllib.parse
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine

# LangChain bits
from langchain.agents import create_sql_agent
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler

# Toolkit (newer LC lives under langchain_community)
try:
    from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
except ImportError:
    from langchain.agents.agent_toolkits import SQLDatabaseToolkit

try:
    from langchain_community.utilities import SQLDatabase
except ImportError:
    from langchain.sql_database import SQLDatabase

# Gemini (free) via Google AI Studio
from langchain_google_genai import ChatGoogleGenerativeAI

# Load API key from .env
from dotenv import load_dotenv
load_dotenv()  

# ──────────────────────────────────────────────────────────────────────────────
# Streamlit Page Setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LangChain: Chat with SQL DB", page_icon="🦜")
st.title("🦜 LangChain: Chat with SQL DB")

# Define constants for database types
LOCALDB = "USE_LOCALDB"
POSTGRES = "USE_POSTGRES"
MYSQL = "USE_MYSQL"

# Sidebar - Choose database
radio_opt = [
    "Use SQLite3 Database - student.db",
    "Connect to PostgreSQL Database",
    "Connect to MySQL Database",
]
selected_opt = st.sidebar.radio("Choose the DB you want to chat with", radio_opt)

# Read Gemini API key from environment
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ Missing API key. Add GOOGLE_API_KEY (or GEMINI_API_KEY) to your .env file.")
    st.stop()
else:
    st.sidebar.success("Gemini API key loaded from .env")

# ──────────────────────────────────────────────────────────────────────────────
# LLM Model: Google Gemini (free API)
# ──────────────────────────────────────────────────────────────────────────────
# Good default: 1.5-flash for speed. Switch to 1.5-pro for deeper reasoning.
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=api_key,
    streaming=True,
)

# Initialize Database Variables
db_uri = None
pg_host = pg_user = pg_password = pg_db = None
mysql_host = mysql_user = mysql_password = mysql_db = None

if selected_opt == radio_opt[0]: 
    db_uri = LOCALDB
elif selected_opt == radio_opt[1]: 
    db_uri = POSTGRES
    pg_host = st.sidebar.text_input("PostgreSQL Host", value="127.0.0.1").strip()
    pg_user = st.sidebar.text_input("PostgreSQL User", value="postgres").strip()
    pg_password = st.sidebar.text_input("PostgreSQL Password", type="password")
    pg_db = st.sidebar.text_input("PostgreSQL Database Name").strip()
elif selected_opt == radio_opt[2]:  
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("MySQL Host", value="127.0.0.1").strip()
    mysql_user = st.sidebar.text_input("MySQL User").strip()
    mysql_password = st.sidebar.text_input("MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("MySQL Database").strip()

if not db_uri:
    st.info("Please enter/select the database information.")

# ──────────────────────────────────────────────────────────────────────────────
# Function to configure database connection
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource(ttl=7200)  
def configure_db(
    db_uri,
    pg_host=None, pg_user=None, pg_password=None, pg_db=None,
    mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None
):
    """Returns a SQLDatabase instance based on the selected configuration."""

    if db_uri == LOCALDB:
       
        dbfilepath = (Path(__file__).parent / "student.db").absolute()
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))

    elif db_uri == POSTGRES:
        if not (pg_host and pg_user and pg_password and pg_db):
            st.error("❌ Please provide all PostgreSQL connection details.")
            st.stop()
        try:
            encoded_password = urllib.parse.quote(pg_password)
            db_url = f"postgresql+psycopg2://{pg_user}:{encoded_password}@{pg_host}/{pg_db}"
            engine = create_engine(db_url)
            return SQLDatabase(engine)
        except Exception as e:
            st.error(f"❌ PostgreSQL connection failed: {e}")
            st.stop()

    elif db_uri == MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("❌ Please provide all MySQL connection details.")
            st.stop()
        try:
            encoded_password = urllib.parse.quote(mysql_password)
            db_url = f"mysql+mysqlconnector://{mysql_user}:{encoded_password}@{mysql_host}/{mysql_db}"
            engine = create_engine(db_url)
            return SQLDatabase(engine)
        except Exception as e:
            st.error(f"❌ MySQL connection failed: {e}")
            st.stop()

# Initialize database connection
if db_uri == LOCALDB:
    db = configure_db(db_uri)
elif db_uri == POSTGRES:
    db = configure_db(db_uri, pg_host, pg_user, pg_password, pg_db)
elif db_uri == MYSQL:
    db = configure_db(db_uri, mysql_host=mysql_host, mysql_user=mysql_user, mysql_password=mysql_password, mysql_db=mysql_db)

# Toolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# Create SQL Agent
agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

# Message history
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# User query input
user_query = st.chat_input(placeholder="Ask anything from the database")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query, callbacks=[streamlit_callback])
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)
