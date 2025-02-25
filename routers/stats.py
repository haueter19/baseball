from cache import cache
from database import get_db
#from data_init import df, pit, h_lg_avg
import functions
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import json
import math
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix='/stats', responses={404: {"description": "Not found"}})

@router.get("/zzz", response_class=JSONResponse)
async def tester():
    df = cache.get_hitting_data()
    return {'records':df.shape[0]}



@router.get("/hitting/{org}/{lg}/{tm}/projections")
async def league(request: Request, org: str, lg: str, tm: str):
    import routers.projections as projections
    df = cache.get_hitting_data(org=org, league=lg).sort_values(['Last', 'First'])
    print(df.head())
    yr = df['Year'].max()
    tm_mask = (df['Org']==org) & (df['League']==lg) & (df['Team']==tm)
    lg_mask = (df['Org']==org) & (df['League']==lg)
    # Subset just the team data for the last 4 years
    #team_data_subset = df.loc[tm_mask & (df['Year'] >= yr-3)]
    # Subset just the league data for the last 4 years
    lg_data_subset = df.loc[lg_mask & (df['Year'] >= yr-3)]

    stats = ['GP', 'PA', 'AB', 'R', 'H', 'single', 'double', 'triple', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']
    proj_df = projections.generate_player_projections(lg_data_subset, stats, teams=[tm])
    functions.add_rate_stats(proj_df)
    functions.add_woba(proj_df)
    return templates.TemplateResponse("projections.html", {"request": request, 'org':org, 'lg':lg, 'tm':tm, 'max_yr':yr, 'df':proj_df.to_html(index=False), 
                                                           'df2':proj_df,})



@router.get("/hitting/{org}/{lg}/league/{yr}")
async def stats_by_league(request: Request, org: str, lg: str, yr: int, sort: Optional[str] = None, asc: Optional[bool] = False):
    import plotly
    df2 = cache.get_hitting_data(org=org, league=lg, year=yr)
    print(df2.head())
    functions.add_rate_stats(df2)
    functions.add_runs_created(df2)
    lgtot = df2
    #lgSLG = lgtot['TB'].sum()/lgtot['AB'].sum()
    #lgOBP = (lgtot['H'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum())/(lgtot['AB'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum()+lgtot['SF'].sum())
    #lgwOBA = round(((0.691*lgtot['BB'].sum()) + (0.722*lgtot['HBP'].sum()) + (0.884*lgtot['1B'].sum()) + (1.257*lgtot['2B'].sum()) + (1.593*lgtot['3B'].sum()) + (2.058*lgtot['HR'].sum())) / (lgtot['AB'].sum() + lgtot['BB'].sum() + lgtot['HBP'].sum() + lgtot['SF'].sum()),3)
    #lgR = lgtot['R'].sum()
    #lgPA = lgtot['PA'].sum()
    #wOBAscale = lgOBP/lgwOBA
    functions.add_woba(df2)
    df2.fillna({'wRC+':0},inplace=True)
    df2['wRC+'] = df2['wRC+'].astype(int)
    if asc==None:
        asc=False
    if sort==None:
        df2 = df2.sort_values('WAR', ascending=asc)
    else:
        df2 = df2.sort_values(sort, ascending=asc)
    yrs = cache.get_hitting_data(org=org, league=lg)['Year'].sort_values(ascending=False).unique().tolist()
    trace1 = { 'x':df2['wRAAc'], 'y':df2['Team'], 'mode':'markers', 'text': df2['First']+' '+df2['Last']}
    plot_data = [trace1]
    scatter = json.dumps(plot_data, cls=plotly.utils.PlotlyJSONEncoder)
    return templates.TemplateResponse('league_stats.html', {"request": request, 'org':org, 'lg':lg, 'yr':yr, 'yrs':yrs, 'df':df2[['Last', 'wRAAc']].to_dict(orient="records"), 'df2':df2, 'scatter':scatter, 'pid':df2['PID'], 'sort': sort, 'asc': asc})



@router.get("/hitting/{org}/{lg}/teams/{yr}")
async def team_stats_year(request: Request, org: str, lg: str, yr: int):
    df2 = cache.get_hitting_data(org=org, league=lg, year=yr)
    df2 = df2.groupby('Team').agg({'Org':'first', 'League':'first', 'Year':'first', 'GP':'sum', 'PA':'sum', 'K':'sum', 'SB':'sum', 'CS':'sum', '1B':'sum', '2B':'sum', '3B':'sum', 'HR':'sum', 'R':'sum', 'RBI':'sum', 'H':'sum', 'BB':'sum', 'HBP':'sum', 'SF':'sum', 'TB':'sum', 'AB':'sum', 'SH':'sum', 'wRAAc':'sum'}).reset_index()
    functions.add_rate_stats(df2)
    functions.add_woba(df2)
    df2 = functions.add_ops_plus(df2, h_lg_avg)
    functions.add_wRC(df2, h_lg_avg)
    functions.add_wRC_plus(df2, h_lg_avg)
    df2['wRAAc'] = round(df2['wRAAc'],1)
    df2 = df2.sort_values('wRAAc', ascending=False)
    df2.drop(columns=['Org', 'League', 'Year'],inplace=True)
    st = pd.read_csv('standings.csv')
    st = st[(st['Org']==org) & (st['League']==lg) & (st['Year']==yr)]
    df2 = df2.merge(st, on='Team', how='left')
    maxYear = 2021#df2.Year.max()
    yrs = cache.get_hitting_data(org=org, league=lg).sort_values('Year', ascending=False)['Year'].unique().tolist()
    return templates.TemplateResponse("stats_team_view.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'yr':yr, 'yrs':yrs, 'maxYear':maxYear})
    


@router.get("/hitting/{org}/{lg}/{tm}/{yr}")
async def team_stats(request: Request, org: str, lg: str, tm: str, yr: int, sort: Optional[str] = 'wRAAc', asc: Optional[bool] = False):
    df2 = cache.get_hitting_data(org=org, league=lg, team=tm, year=yr).sort_values(sort, ascending=asc)
    df2['PID'] = df2['PID'].astype(int)
    functions.add_rate_stats(df2)
    print(df2.columns)
    functions.add_runs_created(df2)
    lgtot = cache.get_hitting_data(org=org, league=lg, year=yr)
    functions.add_woba(df2)
    h_lg_avg = functions.make_lg_avg(lgtot)
    lg_stats = h_lg_avg[(h_lg_avg['Org']==org) & (h_lg_avg['League']==lg) & (h_lg_avg['Year']==yr)]
    yrs = cache.get_hitting_data(org=org, league=lg, team=tm).sort_values('Year', ascending=False)['Year'].unique().tolist()
    df2['Name'] = df2['First']+' '+df2['Last']
    return templates.TemplateResponse("team_stats.html", {"request": request, 'org':org, 'lg':lg, 'tm':tm, 'yrs':yrs, 'yr':yr, 'df':df2.fillna('').to_dict(orient='records'), 'df2':df2, 'lg_stats':lg_stats, 'pid':df2['PID'], 'sort': sort, 'asc': asc})

@router.get("/pitching/{org}/{lg}/league/{yr}")
async def stats_by_league(request: Request, org: str, lg: str, yr: int):
    df2 = cache.get_pitching_data(org=org, league=lg, year=yr).sort_values('Outs', ascending=False)
    df2['IP'] = df2['Outs'].apply(lambda x: str(math.floor(x/3))+"."+str(x % 3))
    df2['WAR'] = round(df2['WAR'],2)
    df2['BAA'] = round(df2['BAA'],3)
    yrs = cache.get_pitching_data(org=org, league=lg).sort_values('Year', ascending=False)['Year'].unique().tolist()
    return templates.TemplateResponse('league_stats_pitching.html', {"request": request, 'org':org, 'lg':lg, 'yr':yr, 'yrs':yrs, 'df':df2.to_html(index=False, justify='right'), 'df2':df2.sort_values('WAR', ascending=False), 'pid':df2['PID']})

@router.get("/pitching/{org}/{lg}/{tm}/{yr}")
async def team_stats_year(request: Request, org: str, lg: str, tm: str, yr: int):
    df2 = cache.get_pitching_data(org=org, league=lg, team=tm, year=yr)
    df2['IP'] = df2['Outs'].apply(lambda x: str(math.floor(x/3))+"."+str(x % 3))
    df2['BAA'] = df2['BAA'].apply(lambda x: round(x,3))
    df2['WAR'] = round(df2['WAR'],2)
    yrs = cache.get_pitching_data(org=org, league=lg, team=tm).sort_values('Year', ascending=False)['Year'].unique().tolist()
    return templates.TemplateResponse("team_pitching.html", {'request': request, 'df2':df2.sort_values('Outs', ascending=False), 'org':org, 'lg':lg, 'tm':tm, 'yr':yr, 'yrs':yrs})
