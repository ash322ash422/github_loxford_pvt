import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import Runnable, RunnableSequence
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# UI header
st.title("Chatbot using LangChain + Memory")

# Create an instance of the ChatOpenAI class, which will be used to interact with the OpenAI API for chatbot functionality
model = ChatOpenAI(temperature=0.7)

# output parser instance
parser = StrOutputParser()

# Initialize session state for memory
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(return_messages=True)
    
# Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant. Use previous context when relevant."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}")
])

# Pipeline using Runnable
chain = prompt | model | parser

# Display previous messages
for msg in st.session_state.memory.chat_memory.messages:
    with st.chat_message("user" if msg.type == "human" else "assistant"):
        st.write(msg.content)

# User input box
user_input = st.chat_input("Type your message...")

      
if user_input:
    # Display user message
    with st.chat_message("user"):
        st.write(user_input)

    # Add user message to memory
    st.session_state.memory.chat_memory.add_user_message(user_input)

    # Run chain
    response = chain.invoke({
        "input": user_input,
        "chat_history": st.session_state.memory.chat_memory.messages
    })

    # Display assistant response
    with st.chat_message("assistant"):
        st.write(response)

    # Save response in memory
    st.session_state.memory.chat_memory.add_ai_message(response)