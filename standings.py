import pandas as pd
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix='/standings', responses={404: {"description": "Not found"}})

@router.get("/{org}/{lg}/{yr}")
async def standings(request: Request, org: str, lg: str, yr: int, sort: Optional[str] = 'Pct', asc: Optional[bool] = False):
    from data_init import st
    yrs = st[(st['Org']==org) & (st['League']==lg)].sort_values('Year', ascending=False)['Year'].unique().tolist()
    st = st[(st['Org']==org) & (st['League']==lg) & (st['Year']==yr)].sort_values(sort, ascending=asc)
    st['GP'] = st['W']+st['L']+st['T']
    st['Pyth'] = round(((st['RF']*st['RF']) / ((st['RF']*st['RF']) + (st['RA']*st['RA']))),3)
    st['xW'] = round(st['Pyth']*st['GP'],1)
    st['Pct'] = round(st['Pct'],3)
    #df2 = df[(df['Org']==org) & (df['League']==lg) & (df['Year']==yr)]
    return templates.TemplateResponse("standings.html", {'request': request, 'st':st, 'org':org, 'lg':lg, 'yr':yr, 'yrs':yrs, 'df':st.fillna('').to_dict(orient='records'),})