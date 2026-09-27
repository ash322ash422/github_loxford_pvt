import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

import os
from dotenv import load_dotenv
load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

model = ChatGroq(model="qwen/qwen3-32b")

st.header("Research Summarizer Tool")

paper_input = st.selectbox( "Select Research Paper Name", ["Attention Is All You Need", "BERT: Pre-training of Deep Bidirectional Transformers", "GPT-3: Language Models are Few-Shot Learners", "Diffusion Models Beat GANs on Image Synthesis"] )

style_input = st.selectbox( "Select Explanation Style", ["Beginner-Friendly", "Technical", "Code-Oriented", "Mathematical"] ) 

length_input = st.selectbox( "Select Explanation Length", ["Short (1-2 paragraphs)", "Medium (3-5 paragraphs)", "Long (detailed explanation)"] )

input_variables = {
    "paper": paper_input,
    "style": style_input,
    "length": length_input
}

template = PromptTemplate(
    template='''
    Summarize the research paper titled "{paper}" with the following specifications:
    1. Explantion style - "{style}" 
    2. Explanation length - "{length}"
    3. Mathematical details: Include relavent mathematical equations if
    present in the paper.Explain mathematical concept using simple, intuitive code snippets where applicable.

    4. Analogies:Use relatable analogies to simplify complex ideas.

    If certain information is not available in the paper respond with "Insufficient information available" instead of guessing. 
    Ensure the summary is clear, accurate and alinged with the provided style and length.''',
    input_variables=list(input_variables.keys()) 
)

#prompt = template.invoke(input_variables)

if st.button("Summarize"):
    st.write("Summarizing your research...")
    chain = template | model
    result = chain.invoke(input_variables)
    st.subheader("Summary:")
    st.write(result.content)
