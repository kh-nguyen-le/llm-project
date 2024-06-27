import database
from llama_index.core import SQLDatabase
from llama_index.llms.ollama import Ollama
from llama_index.core.query_engine import NLSQLTableQueryEngine
import streamlit as st

llm = Ollama(model="llama3", streaming=True)

engine = database.create_database()

sql_database = SQLDatabase(engine, include_tables=[database.TABLE_NAME])

query_engine = NLSQLTableQueryEngine(sql_database, llm, tables=[database.TABLE_NAME], streaming=True)

def stream_wrapper(gen):
    for token in gen:
        yield str(token)

if "messages" not in st.session_state:
  st.session_state.messages = [
      {"role": "assistant", "content": "Ask a Question about the YuGiOh card game!"}
  ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Question: "):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.spinner("Thinking..."):
            with st.chat_message("assistant"):
                stream = query_engine.query(prompt)
                response = st.write_stream(stream_wrapper(stream.response_gen))
            st.session_state.messages.append({"role": "assistant", "content": response})