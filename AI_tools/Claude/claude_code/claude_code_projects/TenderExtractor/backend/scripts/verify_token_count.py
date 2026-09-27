# To run (from the backend/ directory): python -m scripts.verify_token_count

from langchain_community.callbacks.manager import get_openai_callback
# from langchain_core.callbacks import get_openai_callback
from app.services.llm import get_llm

def test_llm_token_count():
    print("Initializing ChatOpenAI model from factory...")
    # 1. Invoke your factory function to get the configured model instance
    llm = get_llm()
    
    # 2. Define a simple testing prompt
    sample_prompt = "Machine learning is powerful. Reply with a short sentence explaining why."
    
    print(f"Sending prompt to Azure OpenAI: '{sample_prompt}'")
    
    # 3. Wrap the invocation block inside the LangChain callback manager
    with get_openai_callback() as cb:
        # The actual API network call executes here
        response = llm.invoke(sample_prompt)
        
        # 4. Extract token metrics from the callback manager *inside* or *immediately after* the block
        prompt_tokens = cb.prompt_tokens
        completion_tokens = cb.completion_tokens
        total_tokens = cb.total_tokens

    # --- Print out the detailed extraction results ---
    print("\n================ TEST RESULTS ================")
    print(f"Model Raw Response:   {response.content.strip()}")
    print("----------------------------------------------")
    print(f"Prompt Tokens (Input):       {prompt_tokens}")
    print(f"Completion Tokens (Output):  {completion_tokens}")
    print(f"Total Tokens Consumed:       {total_tokens}")
    print("==============================================\n")
    
    # You can return the total tokens to update your PipelineContext or JSON status files
    return total_tokens

if __name__ == "__main__":
    test_llm_token_count()
