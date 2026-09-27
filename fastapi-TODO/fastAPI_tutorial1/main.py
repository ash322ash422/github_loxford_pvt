from fastapi import FastAPI
from  models import Fruit

app = FastAPI()

fruits = []

@app.get("/") #handles GET request with URL 'http://127.0.0.1:8000'
async def root():
    return {"message": "Hello World"}

#get a single fruit
@app.get("/fruits/{fruit_id}") #handles GET request with URL 'http://127.0.0.1:8000/fruits/<id>'
async def get_fruits(fruit_id: int):
    for fruit in fruits:
        if fruit.id == fruit_id:
            return {"fruit": fruit}
    return {"message": "No fruit found"}

#get all fruit
@app.get("/fruits") #handles GET request with URL 'http://127.0.0.1:8000/fruits'
async def get_fruits():
    return {"fruits": fruits}

#create a fruit
#handles POST request with URL 'http://127.0.0.1:8000/fruits' and body as {"id":1,"item":"apple"}. Tested with postman.
@app.post("/fruits") 
async def create_fruits(fruit: Fruit):
    fruits.append(fruit)
    return {"message": "Successfully created a fruit"}

#update fruit

#delete fruit