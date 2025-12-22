from fastapi import FastAPI

app = FastAPI(title="Prompt Manager API")

@app.get("/health")
async def health_check():
    return {"status": "up"}
