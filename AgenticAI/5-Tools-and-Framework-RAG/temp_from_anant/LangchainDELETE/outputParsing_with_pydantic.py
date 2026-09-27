# with the help of pydantic output parser
# Create a functional person with name, age and city as attributes. Use the pydantic output parser to structure the output of the model in the form of a person object.

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal
import warnings
warnings.filterwarnings("ignore")

load_dotenv()

# Define the model
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.8)

class Student(BaseModel):

    name: str = Field(description='Name of the student')
    age: int = Field(gt=20, description='Age of the student')
    branch: Literal['Computer Science', 'Mechanical', 'Electrical'] = Field(description='Branch of the student')

parser = PydanticOutputParser(pydantic_object=Student)

template = PromptTemplate(
    template='Generate the record of a student {name} \n {format_instruction}',
    input_variables=['name'],
    partial_variables={'format_instruction':parser.get_format_instructions()}
)

chain = template | llm | parser

final_result = chain.invoke({'name': 'Raavi'})

print(final_result)