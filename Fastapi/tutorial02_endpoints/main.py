from fastapi import FastAPI
from models import Fruit

app = FastAPI()
fruits = []

# create a fruit
# handles POST request with URL 'http://127.0.0.1:8000/fruits' and body as {"id":1,"item":"apple"}.
@app.post("/fruits") 
async def create_fruits(fruit: Fruit):
    fruits.append(fruit)
    return {"message": "Successfully created a fruit"}

# handles GET request with URL 'http://127.0.0.1:8000'
@app.get("/") 
async def root():
    return {"message": "Hello World"}

# get a single fruit
# handles GET request with URL 'http://127.0.0.1:8000/fruits/<id>'
@app.get("/fruits/{fruit_id}") 
async def get_fruits(fruit_id: int):
    for fruit in fruits:
        if fruit.id == fruit_id:
            return {"fruit": fruit}
    return {"message": "No fruit found"}

# get all fruit
# handles GET request with URL 'http://127.0.0.1:8000/fruits'
@app.get("/fruits") 
async def get_fruits():
    return {"fruits": fruits}


# update fruit

# delete fruit