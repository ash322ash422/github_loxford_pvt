from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import StrOutputParser
import os
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)

prompt1 = PromptTemplate(
    template= "What is {topic}?",
    input_variables=["topic"]
)

prompt2 = PromptTemplate(
    template= "What are 5 common challenges about {topic}?",
    input_variables=["topic"]
)

parser = StrOutputParser()

chain = RunnableSequence(prompt1, model, parser, prompt2, model, parser)

print(chain.invoke({'topic':'Prompt Engineering'}))