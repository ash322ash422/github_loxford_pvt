from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from langchain_core.runnables import RunnableSequence, RunnableLambda, RunnablePassthrough, RunnableParallel

load_dotenv()

def word_count(text):
    return len(text.split())

prompt = PromptTemplate(
    template='Write a short paragraph about {topic}',
    input_variables=['topic']
)

model = ChatGroq(model="qwen/qwen3-32b")

parser = StrOutputParser()

paragraph_chain = RunnableSequence(prompt, model, parser)

parallel_chain = RunnableParallel({
    'paragraph': RunnablePassthrough(),
    'word_count': RunnableLambda(word_count)
})

final_chain = RunnableSequence(paragraph_chain, parallel_chain)

result = final_chain.invoke({'topic':'AI'})

final_result = """Paragraph:\n {}\nWord Count: {}""".format(result['paragraph'], result['word_count'])

print(final_result)