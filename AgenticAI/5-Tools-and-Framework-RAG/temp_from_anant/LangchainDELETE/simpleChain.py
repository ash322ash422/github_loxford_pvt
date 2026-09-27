from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

model = ChatGroq(model="qwen/qwen3-32b")

prompt_template = 'Generate 5 interesting facts about {topic}'
prompt = PromptTemplate(
    template=prompt_template,
    input_variables=['topic']
)

parser = StrOutputParser()

# Simple Sequential Chain
chain = prompt | model | parser

result = chain.invoke({"topic": "Linear Regression"})

print(result)

chain.get_graph().print_ascii()