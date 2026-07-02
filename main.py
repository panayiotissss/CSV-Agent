from pydantic import BaseModel
from fastapi import FastAPI
from app.agent import run_agent
from app.schema import Finding




class AskRequest(BaseModel):
    question: str

app = FastAPI(title="CSV Analyst Agent")

@app.post("/ask", response_model=Finding)
def ask(request: AskRequest) -> Finding:
    return run_agent(request.question)
