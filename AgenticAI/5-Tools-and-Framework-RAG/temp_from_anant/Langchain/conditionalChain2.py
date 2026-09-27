from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnableBranch
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal

import os
from dotenv import load_dotenv
load_dotenv()

class Feedback(BaseModel):
    
    sentiment: Literal['positive', 'negative', 'neutral'] = Field(description='Give the sentiment of the feedback')


os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

model1 = ChatOpenAI()
model2 = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)

parser = StrOutputParser()
parser2 = PydanticOutputParser(pydantic_object=Feedback)

prompt1 = PromptTemplate(
    template='Classify the sentiment of the following feedback text into positive, negative, or neutral \n {feedback} \n {format_instruction}',
    input_variables=['feedback'],
    partial_variables={'format_instruction':parser2.get_format_instructions()}
)

classification_chain = prompt1 | model2 | parser2

prompt2 = PromptTemplate(
    template='Write an appropriate response to this positive feedback \n {feedback}',
    input_variables=['feedback']
)

prompt3 = PromptTemplate(
    template='Write an appropriate response to this negative feedback \n {feedback}',
    input_variables=['feedback']
)

prompt4 = PromptTemplate(
    template='Write an appropriate response to this neutral feedback \n {feedback}',
    input_variables=['feedback']
)

branch_chain = RunnableBranch(
    (lambda x:x.sentiment == 'positive', prompt2 | model1 | parser),
    (lambda x:x.sentiment == 'negative', prompt3 | model1 | parser),
    (lambda x:x.sentiment == 'neutral', prompt4 | model1 | parser),
    RunnableLambda(lambda x: "could not find sentiment")
)

chain = classification_chain | branch_chain

result = chain.invoke({"feedback": "Recently I have purchased a new smart watch, it is good but as promised it is not multifunctional, can't set multiple alarms, Overall it is good but not up to the mark."})

print(result)
chain.get_graph().print_ascii()