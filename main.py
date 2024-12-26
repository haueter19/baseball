import asyncio
from cache import cache, periodic_cache_update
from contextlib import asynccontextmanager
from database import SessionLocal, get_db
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
from routers import nav, player_page, fantasy, stats, standings, records, sim_endpoints
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    # Initial cache update
    await periodic_cache_update(db)
    
    # Schedule periodic updates every 5 minutes (adjust as needed)
    async def periodic_update():
        while True:
            await asyncio.sleep(300)  # 5 minutes
            await periodic_cache_update(db)
    
    cache_update_task = asyncio.create_task(periodic_update())
    
    yield 
    
    cache_update_task.cancel()
    try:
        await cache_update_task
    except asyncio.CancelledError:
        pass  
    finally:
        db.close()

app = FastAPI(lifespan=lifespan)


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



@app.get('/healthz')
async def health_check():
    return {'status':'good'}



@app.get("/home")
async def home(request: Request):
    df = cache.get_hitting_data()
    if df.empty:
        return {"error": "Cache not initialized"}
    else:
        print(df.head())
    orgs = df['Org'].sort_values().unique()
    gp = df.sort_values(by=['Org', 'League']).groupby('Org')['League'].unique().reset_index()
    return templates.TemplateResponse("home.html", {"request": request, 'orgs':orgs, 'lgs':gp})



@app.get("/pid")
async def pid_list():
    players = cache.get_players_data()
    return players.set_index('PID').to_dict(orient='index')



def run():
    uvicorn.run(app, port=10000)
    
if __name__=='__main__':
    run()
    
