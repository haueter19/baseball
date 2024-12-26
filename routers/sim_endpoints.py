from cache import cache
import math
from datetime import datetime
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
#from data_init import df, pit
import functions
import routers.projections as projections

router = APIRouter(prefix='/simulation', responses={404: {"description": "Not found"}})

@router.get("/", response_class=HTMLResponse)
async def run_sims(request: Request, org: Optional[str] = 'MABL', lg: Optional[str] = '35', innings: Optional[int] = 7, sims: Optional[int] = 1):
    if org=='MABL':
        if "+" in lg:
            pass
        else:
            lg = lg+"+"
    df = cache.get_hitting_data(org=org, league=lg)
    lg_mask = (df['Org']==org) & (df['League']==lg)
    yr = df.Year.max()
    #tm_mask = (df['Org']==org) & (df['League']==lg) & (df['Team']==tm)
    
    # Subset just the league data for the last 4 years
    lg_data_subset = df.loc[lg_mask & (df['Year'] >= yr-3)]
    print(lg_data_subset)
    stats = ['GP', 'PA', 'AB', 'R', 'H', 'single', 'double', 'triple', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']
    plyrs = projections.generate_player_projections(lg_data_subset, stats, teams=lg_data_subset['Team'].unique().tolist()).sort_values(['Team', 'Last', 'First'])
    plyrs = functions.add_rate_stats(plyrs)
    pit = cache.get_pitching_data(org=org, league=lg)
    lg_pitchers = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Year']==yr)]
    lg_pitchers['K_rate'] = lg_pitchers['K'] / lg_pitchers['ABA']
    return templates.TemplateResponse("sim.html", {'request': request, 'org':org, 'lg':lg, 'yr':yr, 'players':plyrs.to_json(orient='records'), 'plyrs':plyrs, 'lg_pitchers':lg_pitchers})



@router.post("/simulate", response_class=JSONResponse)
async def post_simulations(request:Request):
    data = await request.json()
    away_lineup = [int(i) for i in data['awayLineup']]
    home_lineup = [int(i) for i in data['homeLineup']]
    players = pd.DataFrame(data['players'])
    away_players = players[players['PID'].isin(away_lineup)].sort_values('PID', key=lambda x: x.map({k: v for v, k in enumerate(away_lineup)}))
    home_players = players[players['PID'].isin(home_lineup)].sort_values('PID', key=lambda x: x.map({k: v for v, k in enumerate(home_lineup)}))
    
    for stat in ['single', 'double', 'triple', 'HR', 'BB', 'HBP', 'K']:
        away_players[stat+'_per_PA'] = away_players[stat]/away_players['PA']
        home_players[stat+'_per_PA'] = home_players[stat]/home_players['PA']
    
    pit = cache.get_pitching_data(org=data['org'], league=data['lg'])
    pitcher_data = pit[(pit['PID'].isin([int(data['homePitcher']), int(data['awayPitcher'])])) & (pit['Org']==data['org']) & (pit['League']==data['lg']) & (pit['Year']==int(data['yr']))].reset_index()
    pitcher_data['K_rate'] = pitcher_data['K']/pitcher_data['PAA']
    pitcher_data['BB_rate'] = pitcher_data['BB']/pitcher_data['PAA']
    pitcher_data['HBP_rate'] = pitcher_data['HBP']/pitcher_data['PAA']
    pitcher_data['H_rate'] = pitcher_data['H']/pitcher_data['PAA']

    from sim_game import run_sim
    
    home_result = run_sim(home_players, pitcher_data[pitcher_data['PID']==int(data['awayPitcher'])], int(data['innings']), int(data['sims']))
    away_result = run_sim(away_players, pitcher_data[pitcher_data['PID']==int(data['homePitcher'])], int(data['innings']), int(data['sims']))
    game_result_wins = 0
    for j,k in zip(home_result['runs_scored'], away_result['runs_scored']):
        if j > k:
            game_result_wins += 1
    home_win_pct = round(game_result_wins / int(data['sims']),3)
    return {"data":data, 'type':str(type(data)), 'awayLineup':away_lineup, 'awayResult':away_result, 'homeLineup':home_lineup, 'homeResult':home_result, 'home_win_pct':home_win_pct}
    


@router.get('/optimized_lineup', response_class=JSONResponse)
async def optimized_lineup(request:Request):
    return {'status':'success'}

