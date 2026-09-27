import streamlit as st
from openai import OpenAI
import json
from dotenv import load_dotenv
import os

load_dotenv()  # loads variables from .env
API_KEY = os.getenv("OPENAI_API_KEY")
# API_KEY = "Your_api_key" # NOT GOOD PRACTISE

# ----------------------------
# Setup OpenAI Client
# ----------------------------
client = OpenAI(api_key=API_KEY)

# ----------------------------
#  Guardrails
# ----------------------------
blocked_words = ["hack", "illegal", "fraud"]

def is_safe(user_input):
    return not any(word in user_input.lower() for word in blocked_words)

# ----------------------------
# Intent Classification
# ----------------------------
def classify_intent(user_input):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Classify the user intent into one of: \
                 refund_request, product_query, complaint. \
                 Return only the label."
            },
            {"role": "user", "content": user_input}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# ----------------------------
#  Generate JSON Response
# ----------------------------
def get_bot_response(user_input):
    system_prompt = """
    You are a polite customer support assistant for an e-commerce company.
    
    Rules:
    - Be polite and professional
    - Ask for order ID when needed
    - Handle refunds, complaints, and product queries
    
    Always respond in JSON format:
    {
      "intent": "...",
      "message": "...",
      "action_required": true/false
    }
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.5
    )

    return response.choices[0].message.content

# ----------------------------
#  Streamlit UI
# ----------------------------
st.set_page_config(page_title="AI Customer Support Bot", layout="centered")

st.title(" AI Customer Support Chatbot")
st.write("Demo: Non-RAG chatbot using LLM")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
user_input = st.chat_input("Type your message...")

if user_input:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    #  Guardrail check
    if not is_safe(user_input):
        bot_reply = "I cannot assist with that request."
    else:
        #  Intent
        intent = classify_intent(user_input)
        # st.caption(f"Detected Intent: {intent}") # OPTIONAL
        
        #  LLM response
        raw_response = get_bot_response(user_input)

        try:
            parsed = json.loads(raw_response)
            bot_reply = parsed["message"]
        except:
            bot_reply = "Sorry, I had trouble understanding that."

        # Output Guardrail
        if "illegal" in bot_reply.lower():
            bot_reply = "I am not allowed to provide that information."

    # Display bot response
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    with st.chat_message("assistant"):
        st.markdown(bot_reply)
