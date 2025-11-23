from fastapi import FastAPI, Request
import requests

app = FastAPI()

@app.post("/submit-query")
async def submit_query(request: Request):
    data = await request.json()
    response = requests.post("http://mcp:8001/route-query", json=data)
    return {"response": response.json()}
