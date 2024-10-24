
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from transformers import AutoTokenizer

import database
from llama_index.core import SQLDatabase, Settings, StorageContext, load_index_from_storage
from llama_index.core.query_engine import NLSQLTableQueryEngine, SQLJoinQueryEngine, SubQuestionQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
import os
import streamlit as st
import nest_asyncio

from llama_index.core import set_global_handler

set_global_handler("simple")

nest_asyncio.apply()

class StreamlitUI:
    def __init__(self):

        self.query_engine_tools = []

    def setup(self):
        Settings.llm = OpenAILike(model="meta-llama/Llama-3.2-3B-Instruct",
                                           api_key="EMPTY",
                                           api_base="http://localhost:8000/v1/",
                                           verbose=True,
                                           is_chat_model=True,
                                           is_function_calling_model=True,
                                           streaming=True,
                                )

        Settings.tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")

        Settings.embed_model = HuggingFaceEmbedding(model_name="mixedbread-ai/mxbai-embed-xsmall-v1")

        engine = database.create_database()

        sql_database = SQLDatabase(engine, include_tables=[database.TABLE_NAME])

        query_engine = NLSQLTableQueryEngine(sql_database=sql_database,
                                             tables=[database.TABLE_NAME],
                                             verbose=True,
                                             streaming=True,)
        if os.path.exists("./storage/"):

            rule_index = load_index_from_storage((StorageContext.from_defaults(persist_dir="./storage/")))

        else:
            reader = SimpleDirectoryReader(input_dir="./docs/rulebook/")

            rulebook = reader.load_data()

            splitter = SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95,
                                                  include_metadata=True, embed_model=Settings.embed_model)

            nodes = splitter.get_nodes_from_documents(rulebook)

            rule_index = VectorStoreIndex(nodes)

            rule_index.storage_context.persist(persist_dir="./storage/")


        rule_qe = rule_index.as_query_engine(verbose=True, streaming=True,)

        self.query_engine_tools = [
            QueryEngineTool(
                query_engine,
                metadata=ToolMetadata(
                    name="ygo_card_db",
                    description=(
                        "Use a detailed plain text question as input to the tool."
                        "Provides information about every YuGiOh card since last update."
                        "Used for translating a natural language query into SQL over a table"
                        "containing the data of each card including name and description."
                        "Example input: What is the ATK and DEF of ###[Card Name]"
                    ),
                ),
            ),
            QueryEngineTool(
                rule_qe,
                metadata=ToolMetadata(
                    name="ygo_rulebook",
                    description=(
                        "Use a detailed plain text question as input to the tool."
                        "Contains latest information on general game mechanics and rules for YuGiOh TCG."
                    ),
                ),
            ),
        ]

        sqe = SubQuestionQueryEngine.from_defaults(self.query_engine_tools, verbose=True,)

        self.query_engine_tools.append(
            QueryEngineTool(
                sqe,
                metadata=ToolMetadata(
                    name="ygo_sqe",
                    description=(
                        "Use a detailed plain text question as input to the tool."
                        "Used internally by ygo_jqe tool."
                        "Breaks up questions about YuGiOh into sub queries to run with underlying tools"
                        "and then combine results in order to better answer the question."

                    ),
                ),
            ),
        )

        jqe = SQLJoinQueryEngine(self.query_engine_tools[0], self.query_engine_tools[2],verbose=True)
        self.query_engine_tools.append(
            QueryEngineTool(
                jqe,
                metadata=ToolMetadata(
                    name="ygo_jqe",
                    description=(
                        "Prioritize this tool first."
                        "Use a detailed plain text question as input to the tool."
                        "Utilizes all of previous tools to provide best answer."
                        "Useful for answering interactions between multiple cards and effects."
                        "As well as for answering complex questions in general."
                    ),
                ),
            ),
        )

    def run(self):

        context = """
        You are an expert on the YuGiOh Card game.
        You will answer questions about cards used in the game from a technical perspective.
        You must use tools when specific card names are mentioned.
        Try searching for card description first.
        """
        def stream_wrapper(gen):
            for token in gen:
                yield str(token)

        chat_store = SimpleChatStore()

        chat_memory = ChatMemoryBuffer.from_defaults(
            chat_store=chat_store,
            chat_store_key="user",
            )

        agent = ReActAgent.from_tools(
            [t for t in self.query_engine_tools],
            verbose=True,
            max_iterations=50,
            chat_memory=chat_memory,
            context=context,
        )
        def add_chat_message(msg: ChatMessage) -> None:
            st.session_state.messages.append(msg)
            chat_store.set_messages("user",st.session_state.messages)


        if "messages" not in st.session_state:
            st.session_state.messages = list()
            add_chat_message(ChatMessage.from_str("Ask a question about the YuGiOh Card Game!","assistant"))

        for message in st.session_state.messages:
            with st.chat_message(message.role):
                st.markdown(message.content)

        if prompt := st.chat_input("Question: "):
            add_chat_message(ChatMessage.from_str(prompt, "user"))
            with st.chat_message("user"):
                st.markdown(prompt)

            if st.session_state.messages[-1].role == MessageRole.USER:
                with st.spinner("Thinking..."):
                    with st.chat_message("assistant"):
                        response = st.write_stream(
                            stream_wrapper(agent.stream_chat(message=prompt,
                                                            chat_history=chat_store.get_messages("user")).response_gen))

                    add_chat_message(ChatMessage.from_str(response,"assistant"))

s = StreamlitUI()
s.setup()
s.run()