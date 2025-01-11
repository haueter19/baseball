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
from sim_game import BaseballGame, PlayerStats, PitcherStats

router = APIRouter(prefix='/sim', responses={404: {"description": "Not found"}})

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

    stats = ['GP', 'PA', 'AB', 'R', 'H', 'single', 'double', 'triple', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']
    plyrs = projections.generate_player_projections(lg_data_subset, stats, teams=lg_data_subset['Team'].unique().tolist()).sort_values(['Team', 'Last', 'First'])
    plyrs = functions.add_rate_stats(plyrs)
    pit = cache.get_pitching_data(org=org, league=lg, year=int(yr))
    #lg_pitchers = pit[(pit['Year']==yr)].copy()
    #lg_pitchers['K_rate'] = lg_pitchers['K'] / lg_pitchers['ABA']
    return templates.TemplateResponse("sim.html", {'request': request, 'org':org, 'lg':lg, 'yr':yr, 'players':plyrs.to_json(orient='records'), 'plyrs':plyrs, 'lg_pitchers':pit})



@router.post("/simulate", response_class=JSONResponse)
async def post_simulations(request:Request):
    data = await request.json()
    away_lineup_ids = [int(i) for i in data['awayLineup']]
    home_lineup_ids = [int(i) for i in data['homeLineup']]
    players = pd.DataFrame(data['players'])
    away_players = players[players['PID'].isin(away_lineup_ids)].sort_values('PID', key=lambda x: x.map({k: v for v, k in enumerate(away_lineup_ids)}))
    home_players = players[players['PID'].isin(home_lineup_ids)].sort_values('PID', key=lambda x: x.map({k: v for v, k in enumerate(home_lineup_ids)}))
    
    pit = cache.get_pitching_data(org=data['org'], league=data['lg'])
    #pitcher_data = pit[(pit['PID'].isin([int(data['homePitcher']), int(data['awayPitcher'])])) & (pit['Org']==data['org']) & (pit['League']==data['lg']) & (pit['Year']==int(data['yr']))].reset_index()

    
    games = int(data['sims'])
    user_innings = int(data['innings'])

    home_lineup = []
    for i, rec in home_players.iterrows():
        home_lineup.append(PlayerStats(rec['First']+' '+rec['Last'], rec['PA'], rec['single'], rec['double'], rec['triple'], rec['HR'], rec['BB'], rec['HBP'], rec['K']))

    away_lineup = []
    for i, rec in away_players.iterrows():
        away_lineup.append(PlayerStats(rec['First']+' '+rec['Last'], rec['PA'], rec['single'], rec['double'], rec['triple'], rec['HR'], rec['BB'], rec['HBP'], rec['K']))

    dh = pit[(pit['PID']==int(data['homePitcher'])) & (pit['Year']==int(data['yr']))].rename(columns={'Last':'name', 'PAA':'batters_faced', 'H':'hits_allowed', 'BB':'bb_allowed', 'HBP':'hbp_allowed', 'K':'so_achieved'})\
        [['name', 'batters_faced', 'hits_allowed', 'bb_allowed', 'hbp_allowed', 'so_achieved']].to_dict(orient='records')

    for rec in dh:
        home_pitcher = PitcherStats(**rec)
    
    dh = pit[(pit['Year']==int(data['yr'])) & (pit['PID']==int(data['awayPitcher']))].rename(columns={'Last':'name', 'PAA':'batters_faced', 'H':'hits_allowed', 'BB':'bb_allowed', 'HBP':'hbp_allowed', 'K':'so_achieved'})\
        [['name', 'batters_faced', 'hits_allowed', 'bb_allowed', 'hbp_allowed', 'so_achieved']].to_dict(orient='records')

    for rec in dh:
        away_pitcher = PitcherStats(**rec)

    game = BaseballGame(home_lineup, away_lineup, home_pitcher, away_pitcher, user_innings)
    home_scores = []
    away_scores = []

    for g in range(games):
        game.reset_game()
        game_log = game.simulate_game()
        home_scores.append(game.home_score)
        away_scores.append(game.away_score)
    
    home_wins = 0
    for a,b in zip(home_scores, away_scores):
        if a>b:
            home_wins += 1
    home_win_pct = round((home_wins / games)*100,1)

    game.results()
    game.create_box_score()
    fig = game.plot_win_exp()
    print(game.box_score)
    if len(game.box_score['home_runs']) < len(game.box_score['away_runs']):
        game.box_score['home_runs'].extend(['']*(len(game.box_score['away_runs'])-len(game.box_score['home_runs'])))
    game.box_score['home_team'] = home_players['Team'].iloc[0]
    game.box_score['away_team'] = away_players['Team'].iloc[0]
    game.results()
    return {"data":data, 'type':str(type(data)), 'awayLineup':away_lineup, 'homeLineup':home_lineup, 'home_win_pct':home_win_pct, 'homeScore':round(sum(home_scores)/games,1), 
            'awayScore':round(sum(away_scores)/games,1), 'gameLog':game_log, 'fig':fig.to_json(), 'boxScore':game.box_score, 'results':game.result_df.to_json(orient='records')}
    


@router.get('/optimized_lineup', response_class=JSONResponse)
async def optimized_lineup(request:Request):
    return {'status':'success'}

