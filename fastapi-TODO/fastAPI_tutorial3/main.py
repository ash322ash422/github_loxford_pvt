from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID

app = FastAPI()


class Book(BaseModel):
    id: UUID
    title: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=100)
    rating: int = Field(gt=-1, lt=101)


BOOKS = []


@app.get("/") #works
def read_api():
    return BOOKS

#Following would process POST request with body={"id": "1234567890-1234567890-1234567890","title": "Book1", "author": "auth1","description": "desc1", "rating": 3}
@app.post("/")
def create_book(book: Book):
    BOOKS.append(book)
    return book

#Following would process PUT request with body={"id": "1234567890-1234567890-1234567890","title": "New Book", "author": "New auth1","description": "new desc1", "rating": 5}
@app.put("/{book_id}")
def update_book(book_id: UUID, book: Book):
    counter = 0

    for x in BOOKS:
        counter += 1
        if x.id == book_id:
            BOOKS[counter - 1] = book
            return BOOKS[counter - 1]
    raise HTTPException(
        status_code=404,
        detail=f"ID {book_id} : Does not exist"
    )

#Following would process PUT request with body={"id": "1234567890-1234567890-1234567890","title": "New Book", "author": "New auth1","description": "new desc1", "rating": 5}
@app.delete("/{book_id}")
def delete_book(book_id: UUID):
    counter = 0

    for x in BOOKS:
        counter += 1
        if x.id == book_id:
            del BOOKS[counter - 1]
            return f"ID: {book_id} deleted"
    raise HTTPException(
        status_code=404,
        detail=f"ID {book_id} : Does not exist"
    )
