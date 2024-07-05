import database
from llama_index.core import SQLDatabase
from llama_index.llms.ollama import Ollama
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.memory import ChatMemoryBuffer
import streamlit as st

llm = Ollama(model="llama3", request_timeout=300.0, streaming=True)

engine = database.create_database()

sql_database = SQLDatabase(engine, include_tables=[database.TABLE_NAME])

query_engine = NLSQLTableQueryEngine(sql_database=sql_database, 
                                     llm=llm, tables=[database.TABLE_NAME],
                                     verbose=True)

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


def stream_wrapper(gen):
    for token in gen:
        yield str(token)

if "messages" not in st.session_state:
  st.session_state.messages = [
      ChatMessage.from_str(content="Ask a Question about the YuGiOh card game!",
                           role=MessageRole.ASSISTANT)]
  
for message in st.session_state.messages:
    with st.chat_message(message.role):
        st.markdown(message.content)
chat_store = SimpleChatStore()

chat_memory = ChatMemoryBuffer.from_defaults(
    chat_history=st.session_state.messages,
    llm=llm,
    chat_store=chat_store,
    chat_store_key="user"
    )

agent = ReActAgent.from_tools(
    query_engine_tools,
    llm=llm,
    verbose=True,
    max_iterations=100,
    context=context,
    chat_history=st.session_state.messages,
    memory=chat_memory
)

if prompt := st.chat_input("Question: "):
    st.session_state.messages.append(ChatMessage.from_str(role=MessageRole.USER, content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    
    if st.session_state.messages[-1].role == MessageRole.USER:
        with st.spinner("Thinking..."):
            with st.chat_message("assistant"):
                response = st.write_stream(stream_wrapper(agent.stream_chat(message=prompt, chat_history=st.session_state.messages).response_gen))

            st.session_state.messages.append(ChatMessage.from_str(role=MessageRole.ASSISTANT, content=response))