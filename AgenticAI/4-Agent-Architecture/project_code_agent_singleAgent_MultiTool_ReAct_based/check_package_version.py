import sys
import pydantic
import langchain
import langchain_community
from importlib import metadata

print(f"Python version: {sys.version.split()[0]}")
print(f"pydantic version: {pydantic.__version__}")
print(f"langchain version: {langchain.__version__}")
print(f"langchain-community version: {langchain_community.__version__}")

try:
    lc_openai_version = metadata.version("langchain-openai")
    print(f"langchain-openai version: {lc_openai_version}")
except metadata.PackageNotFoundError:
    print("langchain-openai version: Not installed")