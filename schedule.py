import pandas as pd
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
from data_init import st

router = APIRouter(prefix='/schedule', responses={404: {"description": "Not found"}})

@router.get("/list/{org}/{lg}/{tm}/{yr}")
async def schedule(request: Request, org: str, lg: str, tm: str, yr: int):
    yrs = st[(st['Org']==org) & (st['League']==lg) & (st['Team']==tm)].sort_values('Year', ascending=False)['Year'].unique().tolist()
    return templates.TemplateResponse('schedule.html', {'request':request, 'org':org, 'lg':lg, 'tm':tm, 'yr':yr, 'yrs':yrs})

@router.get("/box/{game_num}")
async def schedule(request: Request, game_num: int):
    
    return templates.TemplateResponse('box.html', {'request':request, 'gmae_num':game_num})