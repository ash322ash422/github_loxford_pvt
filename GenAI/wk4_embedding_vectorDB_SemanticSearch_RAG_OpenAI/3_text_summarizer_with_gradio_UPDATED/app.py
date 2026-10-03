import gradio as gr
from transformers import pipeline

# Hugging Face will automatically handle the framework and data type in the background
text_summary = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6") # This will download 1.2 GB model

def summary(input):
    output = text_summary(input)
    return output[0]['summary_text']

gr.close_all()

demo = gr.Interface(
    fn=summary,
    inputs=[gr.Textbox(label="Input text to summarize", lines=6)],
    outputs=[gr.Textbox(label="Summarized text", lines=4)],
    title="@GenAILearniverse Project 1: Text Summarizer",
    description="THIS APPLICATION WILL BE USED TO SUMMARIZE THE TEXT"
)

demo.launch()
