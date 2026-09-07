from fastapi import FastAPI

app = FastAPI(title="HoneyChain API", version="1.0.0")

@app.get("/")
def read_root():
    return {"status": "online", "system": "HoneyChain Core API"}
