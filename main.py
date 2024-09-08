from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding

import database
from llama_index.core import SQLDatabase, Settings
from llama_index.llms.ollama import Ollama
from llama_index.core.query_engine import NLSQLTableQueryEngine, SQLJoinQueryEngine, SubQuestionQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
import streamlit as st

import nest_asyncio

nest_asyncio.apply()

Settings.llm = Ollama(model="gemma2", request_timeout=300.0, streaming=True)

Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")

engine = database.create_database()

sql_database = SQLDatabase(engine, include_tables=[database.TABLE_NAME])

query_engine = NLSQLTableQueryEngine(sql_database=sql_database,
                                     tables=[database.TABLE_NAME],
                                     verbose=True)

reader = SimpleDirectoryReader(input_dir="./docs/rulebook/")

rulebook = reader.load_data()

splitter = SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95,
                                      include_metadata=True, embed_model=Settings.embed_model)

nodes = splitter.get_nodes_from_documents(rulebook)

rule_index = VectorStoreIndex(nodes)

rule_qe = rule_index.as_query_engine()

query_engine_tools = [
    QueryEngineTool(
        query_engine,
        metadata=ToolMetadata(
            name="ygo_card_db",
            description=(
                "Provides information about every YuGiOh card since last update."
                "Used for translating a natural language query into SQL over a table"
                "containing the data of each card including name and description."
            ),
        ),
    ),
    QueryEngineTool(
        rule_qe,
        metadata=ToolMetadata(
            name="ygo_rulebook",
            description=(
                "Contains latest information on general game mechanics and rules for YuGiOh TCG."
                "Use a detailed plain text question as input to the tool."
            ),
        ),
    ),
]

sqe = SubQuestionQueryEngine.from_defaults(query_engine_tools, verbose=True)



tools = [
    QueryEngineTool(
        sqe,
        metadata=ToolMetadata(
            name="ygo_sqe",
            description=(
                "Breaks up questions about YuGiOh into sub queries to run with underlying tools"
                "and then combine results in order to better answer the question."
                "Use a detailed plain text question as input to the tool."
                "Used internally by ygo_jqe tool."
            ),
        ),
    ),
]

jqe = SQLJoinQueryEngine(query_engine_tools[0], tools[0],verbose=True)
tools.append(
    QueryEngineTool(
        jqe,
        metadata=ToolMetadata(
            name="ygo_jqe",
            description=(
                "Prioritize this tool first."
                "Utilizes all of previous tools to provide best answer."
                "Useful for answering interactions between multiple cards and effects."
                "As well as for answering complex questions in general."
                "Use a detailed plain text question as input to the tool."
            ),
        ),
    ),
)

context = """
You are an expert on the YuGiOh Card game.
You will answer questions about cards used in the game from a technical perspective.
You must use tools when specific card names are mentioned.
Try searching for card description first.
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
    chat_store=chat_store,
    chat_store_key="user"
    )

agent = ReActAgent.from_tools(
    [t for t in query_engine_tools + tools],
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
