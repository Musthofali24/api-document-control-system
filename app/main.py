from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

app = FastAPI()


@app.get("/ping")
def ping():
    return {"Halo"}
