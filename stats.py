import math
import json
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
from data_init import df, pit, h_lg_avg
import functions

router = APIRouter(prefix='/stats', responses={404: {"description": "Not found"}})

@router.get("/hitting/{org}/{lg}/{tm}/projections")
async def league(request: Request, org: str, lg: str, tm: str):
    yr = df.Year.max()
    df2 = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Team']==tm) & (df['Year'].isin(list(range(yr-5,yr+1))))]
    from projections import make_projections
    pa = 50
    df2 = make_projections(df2, pa)
    functions.add_woba(df2)
    return templates.TemplateResponse("projections.html", {"request": request, 'org':org, 'lg':lg, 'tm':tm, 'max_yr':df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Team']==tm)]['Year'].max(), 'df':df2.to_html(index=False), 'df2':df2, 'pid':df2['PID']})

@router.get("/hitting/{org}/{lg}/league/{yr}")
async def stats_by_league(request: Request, org: str, lg: str, yr: int, sort: Optional[str] = None, asc: Optional[bool] = False):
    import plotly
    df2 = df[(df['Org']==org) & (df['League']==lg) & (df['Year']==yr)]
    functions.add_rate_stats(df2)
    functions.add_runs_created(df2)
    lgtot = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Year']==yr)]
    lgSLG = lgtot['TB'].sum()/lgtot['AB'].sum()
    lgOBP = (lgtot['H'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum())/(lgtot['AB'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum()+lgtot['SF'].sum())
    lgwOBA = round(((0.691*lgtot['BB'].sum()) + (0.722*lgtot['HBP'].sum()) + (0.884*lgtot['1B'].sum()) + (1.257*lgtot['2B'].sum()) + (1.593*lgtot['3B'].sum()) + (2.058*lgtot['HR'].sum())) / (lgtot['AB'].sum() + lgtot['BB'].sum() + lgtot['HBP'].sum() + lgtot['SF'].sum()),3)
    lgR = lgtot['R'].sum()
    lgPA = lgtot['PA'].sum()
    wOBAscale = lgOBP/lgwOBA
    #add_ops_plus(df2, lgOBP, lgSLG)
    functions.add_woba(df2)
    #add_wRAA(df2, lgwOBA, wOBAscale)
    #add_wRC(df2, lgwOBA, wOBAscale, lgR, lgPA)
    #add_wRC_plus(df2, lgR, lgPA)
    df2['wRC+'].fillna(0,inplace=True)
    df2['wRC+'] = df2['wRC+'].astype(int)
    if asc==None:
        asc=False
    if sort==None:
        df2 = df2.sort_values('WAR', ascending=asc)
    else:
        df2 = df2.sort_values(sort, ascending=asc)
    yrs = df[(df['Org']==org) & (df['League']==lg)]['Year'].sort_values(ascending=False).unique().tolist()
    trace1 = { 'x':df2['wRAAc'], 'y':df2['Team'], 'mode':'markers', 'text': df2['First']+' '+df2['Last']}
    plot_data = [trace1]
    scatter = json.dumps(plot_data, cls=plotly.utils.PlotlyJSONEncoder)
    return templates.TemplateResponse('league_stats.html', {"request": request, 'org':org, 'lg':lg, 'yr':yr, 'yrs':yrs, 'df':df2[['Last', 'wRAAc']].to_dict(orient="records"), 'df2':df2, 'scatter':scatter, 'pid':df2['PID'], 'sort': sort, 'asc': asc})

@router.get("/hitting/{org}/{lg}/teams/{yr}")
async def team_stats_year(request: Request, org: str, lg: str, yr: int):
    df2 = df[(df['Org']==org) & (df['League']==lg) & (df['Year']==yr)]
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
    yrs = df[(df['Org']==org) & (df['League']==lg)].sort_values('Year', ascending=False)['Year'].unique().tolist()
    return templates.TemplateResponse("stats_team_view.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'yr':yr, 'yrs':yrs, 'maxYear':maxYear})
    
@router.get("/hitting/{org}/{lg}/{tm}/{yr}")
async def team_stats(request: Request, org: str, lg: str, tm: str, yr: int, sort: Optional[str] = None, asc: Optional[bool] = False):
    df2 = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Team']==tm) & (df['Year']==yr)][['PID', 'First', 'Last', 'GP', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB', 'wRAA', 'BA', 'OBP', 'SLG', 'OPS', 'OPS+', 'wRAAc', 'wOBA', 'wRC', 'wRC+', 'WAR']]
    df2['PID'] = df2['PID'].astype(int)
    functions.add_rate_stats(df2)
    functions.add_runs_created(df2)
    lgtot = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Year']==yr)]
    lgSLG = lgtot['TB'].sum()/lgtot['AB'].sum()
    lgOBP = (lgtot['H'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum())/(lgtot['AB'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum()+lgtot['SF'].sum())
    lgwOBA = round(((0.691*lgtot['BB'].sum()) + (0.722*lgtot['HBP'].sum()) + (0.884*lgtot['1B'].sum()) + (1.257*lgtot['2B'].sum()) + (1.593*lgtot['3B'].sum()) + (2.058*lgtot['HR'].sum())) / (lgtot['AB'].sum() + lgtot['BB'].sum() + lgtot['HBP'].sum() + lgtot['SF'].sum()),3)
    lgR = lgtot['R'].sum()
    lgPA = lgtot['PA'].sum()
    wOBAscale = lgOBP/lgwOBA
    #add_ops_plus(df2, lgOBP, lgSLG)
    functions.add_woba(df2)
    #add_wRAA(df2, lgwOBA, wOBAscale)
    #add_wRC(df2, lgwOBA, wOBAscale, lgR, lgPA)
    #add_wRC_plus(df2, lgR, lgPA)
    #df2['wRC+'].fillna(0,inplace=True)
    #df2['wRC+'] = df2['wRC+'].astype(int)
    #df2.append({'Team Totals', df2['GP'].sum(), df2['PA'].sum(), df2['AB'].sum(), df2['R'].sum(), df2['H'].sum(), df2['1B'].sum(), df2['2B'].sum(), df2['3B'].sum(), df2['HR'].sum(), df2['RBI'].sum(), df2['BB'].sum(), df2['K'].sum(), df2['HBP'].sum(), df2['SB'].sum(), df2['CS'].sum(), df2['SF'].sum(), df2['SH'].sum(), df2['TB'].sum(), df2['wRAA'].sum(), df2['RC'].sum(), round(df2['H'].sum()/df2['AB'].sum(),3), '-', '-', '-', '-', '-', '-', '-', '-']
    if asc==None:
        asc=False
    if sort==None:
        df2 = df2.sort_values('WAR', ascending=False)
    else:
        df2 = df2.sort_values(sort, ascending=asc)
    df2 = functions.add_team_totals(df2)
    lg_stats = h_lg_avg[(h_lg_avg['Org']==org) & (h_lg_avg['League']==lg) & (h_lg_avg['Year']==yr)]
    yrs = df[(df['Org']==org) & (df['League']==lg) & (df['Team']==tm)].sort_values('Year', ascending=False)['Year'].unique().tolist()
    df2['Name'] = df2['First']+' '+df2['Last']
    return templates.TemplateResponse("team_stats.html", {"request": request, 'org':org, 'lg':lg, 'tm':tm, 'yrs':yrs, 'yr':yr, 'df':df2.fillna('').to_dict(orient='records'), 'df2':df2, 'lg_stats':lg_stats, 'pid':df2['PID'], 'sort': sort, 'asc': asc})

@router.get("/pitching/{org}/{lg}/league/{yr}")
async def stats_by_league(request: Request, org: str, lg: str, yr: int):
    df2 = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Year']==yr)].sort_values('Outs', ascending=False)
    df2['IP'] = df2['Outs'].apply(lambda x: str(math.floor(x/3))+"."+str(x % 3))
    df2['BAA'] = round(df2['BAA'],3)
    yrs = pit[(pit['Org']==org) & (pit['League']==lg)].sort_values('Year', ascending=False)['Year'].unique().tolist()
    return templates.TemplateResponse('league_stats_pitching.html', {"request": request, 'org':org, 'lg':lg, 'yr':yr, 'yrs':yrs, 'df':df2.to_html(index=False, justify='right'), 'df2':df2, 'pid':df2['PID']})

@router.get("/pitching/{org}/{lg}/{tm}/{yr}")
async def team_stats_year(request: Request, org: str, lg: str, tm: str, yr: int):
    df2 = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Team']==tm) & (pit['Year']==yr)]
    #df2 = df2.groupby('Team').agg({'Org':'first', 'League':'first', 'Year':'first', 'First':'first', 'Last':'first', 'GP':'sum', 'IP':'sum', 'Outs':'sum', 'R':'sum', 'ER':'sum', 'H':'sum', 'BB':'sum', 'K':'sum', 'HBP':'sum', 'CG':'sum', 'W':'sum', 'L':'sum', 'Sv':'sum', 'HR':'sum', 'IBB':'sum', 'AB':'sum', 'BAA':'sum', 'HLD':'sum'}).reset_index()
    df2['IP'] = df2['Outs'].apply(lambda x: str(math.floor(x/3))+"."+str(x % 3))
    df2['BAA'] = df2['BAA'].apply(lambda x: round(x,3))
    yrs = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Team']==tm)].sort_values('Year', ascending=False)['Year'].unique().tolist()
    return templates.TemplateResponse("team_pitching.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'tm':tm, 'yr':yr, 'yrs':yrs})
