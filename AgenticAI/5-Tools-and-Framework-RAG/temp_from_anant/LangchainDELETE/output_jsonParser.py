from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import TypedDict

import warnings
warnings.filterwarnings("ignore")

load_dotenv()

# Define the model
llm = ChatGroq(model="qwen/qwen3-32b")

# TypedDict for Student
class StudentDict(TypedDict):
    name: str
    grade: int
    school: str

# JSON Output Parser
parser = JsonOutputParser()

# Prompt
template = PromptTemplate(
    template='''
Generate details of a school student from {place}.

Return the result in JSON format with the following keys:
name, grade, school

{format_instructions}
''',
    input_variables=['place'],
    partial_variables={'format_instructions': parser.get_format_instructions()}
)

# Chain
chain = template | llm | parser

# Invoke
result = chain.invoke({'place': 'China'})

print(result.content)