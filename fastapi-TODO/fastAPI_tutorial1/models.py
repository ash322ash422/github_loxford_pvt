#from fastapi import FastAPI
from pydantic import BaseModel


class Fruit(BaseModel):
    id: int
    item: str
    