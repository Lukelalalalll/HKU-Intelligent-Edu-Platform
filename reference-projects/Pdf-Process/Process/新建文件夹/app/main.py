from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base,engine,ensure_schema
from .api import documents,jobs,search,chat
ensure_schema()
app=FastAPI(title='Local MinerU PDF Processor',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
app.include_router(documents.router); app.include_router(jobs.router); app.include_router(search.router)
app.include_router(chat.router)
@app.get('/health')
def health(): return {'ok':True,'mineru':'configured'}
