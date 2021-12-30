import os
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
from data_init import df
from logos import logos

router = APIRouter(prefix='/{org}', responses={404: {"description": "Not found"}})

@router.get("/")
async def org(request: Request, org: str):
    df2 = df[df['Org']==org.upper()]
    lgs = df2['League'].sort_values().unique()
    if org=='MABL':
        lg = '18+'
    elif org=='RRL':
        lg = 'Southern'
    elif org=='MSCR':
        lg = 'Pacific'
    else:
        lg = '18+'
    return templates.TemplateResponse("org.html", {"request": request, 'org':org, 'lgs':lgs, 'lg': lg, 'max_yr':df2.Year.max()})

@router.get("/{lg}/champions")
async def standings(request: Request, org: str, lg: str):
    standings = pd.read_csv('standings.csv')
    post_winners = standings[(standings['Org']==org.upper()) & (standings['League']==lg) & (standings['Postseason']==1)][['Year', 'Team']].sort_values('Year', ascending=False)
    post_winners.columns=['Year', 'Playoffs']
    season_winners = standings[(standings['Org']==org.upper()) & (standings['League']==lg) & (standings['Season']==1)][['Year', 'Team']].sort_values('Year', ascending=False)
    season_winners.columns=['Year', 'Season']
    champs = post_winners.merge(season_winners, on='Year', how='outer')
    return templates.TemplateResponse("champions.html", {'request': request, 'org': org, 'lg': lg, "champs": champs, 'logos':logos})

@router.get("/{lg}")
async def league(request: Request, org: str, lg: str):
    df2 = df[(df['Org']==org.upper()) & (df['League']==lg)]
    _list = df[(df['Org']==org.upper()) & (df['League']==lg)].sort_values('Year').groupby('Team')['Year'].unique()#.reset_index()
    print(df2['Team'].unique())
    tms = df2['Team'].sort_values().unique()
    maxYear = df2.Year.max()
    minYear = df2.Year.min()
    yrs = df[(df['Org']==org) & (df['League']==lg)]['Year'].sort_values().unique().tolist()
    return templates.TemplateResponse("league.html", {"request": request, 'org':org, 'lg':lg, 'tms':tms, 'maxYear':maxYear, 'minYear':minYear, 
                                        'yrs':yrs, 'yr_list': _list.to_dict(), 'logos':logos})


@router.get("/{lg}/{tm}/gallery")
async def orglgtm(request: Request, org: str, lg: str, tm: str):
    path = os.path.join('static', 'images', org, lg, tm)
    img_list = os.listdir(path)
    return templates.TemplateResponse('gallery.html', {'request':request, 'org':org, 'lg':lg, 'tm':tm, 'len':len(img_list), 'img_list':img_list})