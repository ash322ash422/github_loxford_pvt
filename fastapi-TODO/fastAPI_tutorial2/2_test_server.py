

import requests
#After running uvicorn server , you should see some output here.
print(requests.get("http://127.0.0.1:8000/").json())

print("#####################################################")
print(requests.get("http://127.0.0.1:8000/items/1").json())
print(requests.get("http://127.0.0.1:8000/items/15").json())
print(requests.get("http://127.0.0.1:8000/items/gibberish").json())

print("=======================================================")
print(requests.get("http://127.0.0.1:8000/items?count=50").json()) #outputs all rec whose count is NOT 50
print(requests.get("http://127.0.0.1:8000/items?name=Drills").json()) #outputs all rec whose name=Drills
print(requests.get("http://127.0.0.1:8000/items?price=2.99").json()) #outputs all rec whose price=2.99
print(requests.get("http://127.0.0.1:8000/items?category=tools").json()) #outputs all rec whose category=tools

print("-----------------------------------------------------")
# These requests will result in an error, since count are negative:
print(requests.put("http://127.0.0.1:8000/update/0?count=-1").json())
print(requests.put("http://127.0.0.1:8000/update/0?price=-1").json())

# Similarly, an item_id must not be negative:
print(requests.put("http://127.0.0.1:8000/update/-1").json())

#And name cannot exceed 8 characters:
print(requests.put("http://127.0.0.1:8000/update/1?name=CrazyNamedTooool").json())

print(requests.put("http://127.0.0.1:8000/update/2?name=UpdatedTool").json())

print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
print("Adding an item:")
print(requests.post( "http://127.0.0.1:8000/",
                     json={"name": "Screwdriver", "price": 3.99, "count": 10, "id": 4, "category": "tools" },).json()
                   )

print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
print("Deleting an item:")
print(requests.delete("http://127.0.0.1:8000/delete/0").json())
print(requests.get("http://127.0.0.1:8000/").json())
