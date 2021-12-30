import math
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
from data_init import df, pit

router = APIRouter(prefix='/simulation', responses={404: {"description": "Not found"}})

@router.get("/", response_class=HTMLResponse)
async def run_sims(request: Request, org: Optional[str] = 'MABL', lg: Optional[str] = '35', innings: Optional[int] = 7, sims: Optional[int] = 1, go: Optional[int] = 0, away_lineup: Optional[str] = '2432+1781+304+876+2019+1125+750+2043+484+376', away_pitcher: Optional[int] = 484, home_lineup: Optional[str] = '579+492+391+825+1632+495+1605+1978+509', home_pitcher: Optional[int] = 825):
    if org=='MABL':
        if "+" in lg:
            pass
        else:
            lg = lg+"+"
    from projections import make_projections
    plyrs = make_projections(df[(df['Org']==org) & (df['League']==lg) & (df['Year']>2015)], 50)
    plyrs.drop(columns='PID',inplace=True)
    plyrs = plyrs.reset_index()
    lg_pitchers = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]
    
    if go==0:
        score = 'No sims run'
        away_lineup = plyrs['PID'][:10].to_list()
        away_pitcher = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]['PID'].iloc[0]
        home_lineup = plyrs['PID'][:10].to_list()
        home_pitcher = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]['PID'].iloc[1]
        game_log_away = ''
        game_log_home = ''
        ab_results_away = ['']
        ab_results_home = ['']
        prj_away = pd.DataFrame()#['']
        prj_home = pd.DataFrame()#['']
    else:
        import urllib.parse
        away_lineup = urllib.parse.unquote(away_lineup)
        home_lineup = urllib.parse.unquote(home_lineup)
        
        away_lineup = away_lineup.split('+')
        for i in range(len(away_lineup)):
            away_lineup[i] = int(away_lineup[i])
        home_lineup = home_lineup.split('+')
        for i in range(len(home_lineup)):
            home_lineup[i] = int(home_lineup[i])
        prj_away = plyrs[plyrs['PID'].isin(away_lineup)].set_index('PID').reindex(away_lineup).reset_index()

        for i in ['1B', '2B', '3B', 'HR', 'BB', 'HBP', 'K']:
            prj_away[i+'_per_PA'] = round(prj_away[i]/prj_away['PA'],3)
        prj_home = plyrs[plyrs['PID'].isin(home_lineup)].set_index('PID').reindex(home_lineup).reset_index()
        for i in ['1B', '2B', '3B', 'HR', 'BB', 'HBP', 'K']:
            prj_home[i+'_per_PA'] = round(prj_home[i]/prj_home['PA'],3)
        
        home_pitcher_df = pit[(pit['PID']==home_pitcher) & (pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]
        away_pitcher_df = pit[(pit['PID']==away_pitcher) & (pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]
        from sim_game import run_sim
        rpg_away, game_log_away, ab_results_away = run_sim(prj_away, home_pitcher_df, innings, sims)
        rpg_home, game_log_home, ab_results_home = run_sim(prj_home, away_pitcher_df, innings, sims)
        score = str(rpg_away)+' - '+str(rpg_home)
        
    return templates.TemplateResponse("sim.html", {'request': request, 'org':org, 'lg':lg, 'score':score, 'plyrs':plyrs, 'lg_pitchers':lg_pitchers, 'away_team':away_lineup, "away_pitcher":away_pitcher, "home_team":home_lineup, "home_pitcher":home_pitcher, 'game_log_away':game_log_away, 'game_log_home':game_log_home, 'ab_results_away':ab_results_away, 'away_proj':prj_away, 'home_proj':prj_home, 'ab_results_home':ab_results_home})