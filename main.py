import uvicorn
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from logos import logos
from data_init import df, pit, st, h_lg_avg, oly
import nav, player_page, stats, records, standings, sim_endpoints, fantasy

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(player_page.router)
app.include_router(fantasy.router)
app.include_router(stats.router)
app.include_router(records.router)
app.include_router(standings.router)
app.include_router(sim_endpoints.router)
app.include_router(nav.router)

@app.get('/')
async def slash():
    return RedirectResponse("/home")

@app.get("/home")
async def home(request: Request):
    orgs = df['Org'].sort_values().unique()
    gp = df.sort_values(by=['Org', 'League']).groupby('Org')['League'].unique().reset_index()
    return templates.TemplateResponse("home.html", {"request": request, 'orgs':orgs, 'lgs':gp})

@app.get("/pid")
async def pid_list():
    h = df[['PID', 'First', 'Last']]
    p = pit[['PID', 'First', 'Last']]
    df2 = h.append(p)
    df2 = df2.groupby('PID').agg({'First':'first', 'Last':'first'}).reset_index()
    df2 = df2.dropna()
    return {'PID':df2.PID.tolist(), 'First':df2.First.tolist(), 'Last':df2.Last.tolist()}

if __name__=='__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8001, reload=True)
    
