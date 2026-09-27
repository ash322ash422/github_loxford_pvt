from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
import os
load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

model = ChatGroq(model="qwen/qwen3-32b")

# 1st prompt to generate a detailed report
template1 = PromptTemplate(
    template='Write an essay on the {topic}',
    input_variables=['topic']
)

# 2nd prompt to generate a summary
template2 = PromptTemplate(
    template='Write summary in 5 bullets on the following text. /n {text}',
    input_variables=['text']
)

prompt1 = template1.invoke({'topic':'Dewali'})

result1 = model.invoke(prompt1)

prompt2 = template2.invoke({'text':result1.content})

result2 = model.invoke(prompt2)

print(result2.content)