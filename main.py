import database
from llama_index.core import SQLDatabase
from llama_index.llms.ollama import Ollama
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import NLSQLRetriever
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
import streamlit as st

llm = Ollama(model="llama3", request_timeout=300.0, streaming=True)

engine = database.create_database()

sql_database = SQLDatabase(engine, include_tables=[database.TABLE_NAME])

nl_sql_retriever = NLSQLRetriever(sql_database, tables=[database.TABLE_NAME])

query_engine = RetrieverQueryEngine(nl_sql_retriever)

query_engine_tools = [
    QueryEngineTool(
        query_engine,
        metadata=ToolMetadata(
            name="ygo_card_db",
            description=(
                "Provides information about every YuGiOh card up to June 2024. "
                "Use a detailed plain text question as input to the tool."
            ),
        ),
    )
]

context = """
You are an expert on the YuGiOh Card game.
You will answer questions about cards used in the game from a technical perspective.
"""

agent = ReActAgent.from_tools(
    query_engine_tools,
    llm=llm,
    verbose=True,
    context=context
)

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
                response = st.write_stream(stream_wrapper(agent.stream_chat(prompt).response_gen))
            st.session_state.messages.append({"role": "assistant", "content": response})