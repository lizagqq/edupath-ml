"""FastAPI application. Install requirements.txt to run with uvicorn."""
from fastapi import FastAPI,HTTPException,Query
from src.api.service import Service
from src.api.contracts import APP_VERSION

app=FastAPI(title='EduPath ML',description='Оценка следующего ответа по истории LMS и учебная траектория',version=APP_VERSION)
service=Service()

def require_ready():
    if not service.ready():raise HTTPException(status_code=503,detail='Сначала выполните scripts/build_project.py')

@app.get('/health')
def health():return service.health()

@app.get('/students')
def students(limit:int=Query(20,ge=1,le=100)):require_ready();return service.students(limit)

@app.get('/students/{user_id}/profile')
def profile(user_id:str):
    require_ready()
    try:return service.profile(user_id)
    except KeyError:raise HTTPException(404,'Ученик не найден')

@app.get('/students/{user_id}/trajectory')
def trajectory(user_id:str):
    require_ready()
    try:return service.trajectory(user_id)
    except KeyError:raise HTTPException(404,'Ученик не найден')

@app.get('/skills')
def skills():require_ready();return service.skills()

@app.get('/materials')
def materials(skill:str|None=None,query:str='',limit:int=Query(3,ge=1,le=50)):
    require_ready();return service.materials(skill,query,limit)

@app.get('/model/info')
def info():require_ready();return service.info()
