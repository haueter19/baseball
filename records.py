import math
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
from data_init import df, pit
import functions

router = APIRouter(prefix='/records', responses={404: {"description": "Not found"}})

@router.get("/hitting/season/{org}/{lg}")
async def season_records(request: Request, org: str, lg: str, stat: Optional[str] = 'WAR', qual: Optional[int] = 25):
    df2 = df[(df['Org']==org) & (df['League']==lg) & (df['PA']>qual)].sort_values([stat, 'PA'], ascending=[False, True]).head(50)
    df2.drop(columns=['wRCPlus', 'All-Star', 'Outs', 'den', 'lgR', 'lgPA', 'BA_lg', 'OBP_lg', 'SLG_lg', 'OPS_lg', 'wOBA_lg', 'wOBAscale', 'OPS+', 'replacement_runs', 'wRC+'], inplace=True)
    df2['stat'] = df2[stat]
    return templates.TemplateResponse("season_records.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'stat':stat, 'type':'hitting', 'qual':qual})

@router.get("/pitching/season/{org}/{lg}")
async def season_records(request: Request, org: str, lg: str, stat: Optional[str] = 'WAR', qual: Optional[int] = 63):
    df2 = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Outs']>qual)].sort_values([stat, 'Outs'], ascending=[False, True]).head(50)
    df2.drop(columns=['CoreWAR', 'BB_rate', 'H_rate', 'HBP_rate', 'K_rate'], inplace=True)
    df2['stat'] = df2[stat]
    return templates.TemplateResponse("season_records.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'stat':stat, 'type':'pitching', 'qual':qual})

@router.get("/hitting/career/{org}/{lg}")
async def career_records(request: Request, org: str, lg: str, stat: Optional[str] = 'WAR', qual: Optional[int] = 100):
    if stat in ['BA', 'OBP', 'SLG', 'OPS']:
        df2 = df[(df['Org']==org) & (df['League']==lg)].groupby('PID').agg({'First':'last', 'Last':'last', 'Team':'last', 'PA':'sum', 'R':'sum', 'RBI':'sum', 'H':'sum', '1B':'sum', '2B':'sum', '3B':'sum', 'HR':'sum', 'BB':'sum', 'HBP':'sum', 'AB':'sum', 'SB':'sum', 'CS':'sum', 'TB':'sum', 'SF':'sum', 'wRAAc':'sum', 'WAR':'sum'})
        df2 = functions.add_rate_stats(df2)
        df2 = df2.query('PA>=@qual').sort_values([stat, 'PA'], ascending=[False, True]).head(50).reset_index()
        df2['stat'] = df2[stat]
        df2.columns=['PID', 'First', 'Last', 'Team', 'PA', 'R', 'RBI', 'H', '1B', '2B', '3B', 'HR', 'BB', 'HBP', 'AB', 'SB', 'CS', 'TB', 'SF', 'BA', 'OBP', 'SLG', 'OPS', 'wRAAc', 'WAR', 'stat']
        #df2.columns=['PID', 'First', 'Last', 'Team', 'PA', 'H', 'BB', 'HBP', 'AB', 'TB', 'SF', 'BA', 'OBP', 'SLG', 'OPS', 'stat']
    else:
        df2 = df[(df['Org']==org) & (df['League']==lg)].groupby('PID').agg({'First':'last', 'Last':'last', 'Team':'last', 'PA':'sum', 'R':'sum', 'RBI':'sum', 'H':'sum', '1B':'sum', '2B':'sum', '3B':'sum', 'HR':'sum', 'BB':'sum', 'HBP':'sum', 'AB':'sum', 'SB':'sum', 'CS':'sum', 'TB':'sum', 'SF':'sum', 'wRAAc':'sum', 'WAR':'sum'}).sort_values([stat, 'PA'], ascending=[False, True]).head(50).reset_index()
        for i in ['wRAAc', 'WAR']:
            df2[i] = df2[i].apply(lambda x: round(x,1))
        df2['stat'] = df2[stat]
        df2 = functions.add_rate_stats(df2)
        #df2 = add_wRAA(df2)
        df2 = df2[df2['PA']>=qual]
    return templates.TemplateResponse("career_records.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'recent_year':df.Year.max(), 'stat':stat, 'type':'hitting', 'qual':qual})

@router.get("/pitching/career/{org}/{lg}")
async def career_records(request: Request, org: str, lg: str, stat: Optional[str] = 'WAR', qual: Optional[int] = 150):
    if stat in ['ERA', 'WHIP', 'Kper9', 'BBper9', 'Hper9', 'BAA']:
        df2 = pit[(pit['Org']==org) & (pit['League']==lg)].groupby('PID').agg({'First':'last', 'Last':'last', 'Team':'last', 'Outs':'sum', 'R':'sum', 'ER':'sum', 'H':'sum', 'BB':'sum', 'HBP':'sum', 'ABA':'sum', 'K':'sum', 'W':'sum', 'L':'sum', 'Sv':'sum', 'CG':'sum', 'WAR':'sum'})
        df2['IP'] = df2['Outs'].apply(lambda x: str(math.floor(x/3))+"."+str(x % 3))
        df2['ERA'] = round(df2['ER']/(df2['Outs']/3)*9,2)
        df2['WHIP'] = round((df2['BB']+df2['H'])/(df2['Outs']/3),2)
        df2['Kper9'] = round(df2['K']/(df2['Outs']/3)*9,1)
        df2['BBper9'] = round(df2['BB']/(df2['Outs']/3)*9,1)
        df2['Hper9'] = round(df2['H']/(df2['Outs']/3)*9,2)
        if stat in ['Kper9']:
            asc=False
        else:
            asc=True
        df2 = df2.query('Outs>=@qual').sort_values(stat, ascending=asc).head(50).reset_index()
        df2['stat'] = df2[stat]
        #df2.columns=['PID', 'First', 'Last', 'Team', 'PA', 'H', 'BB', 'HBP', 'AB', 'TB', 'SF', 'BA', 'OBP', 'SLG','OPS', 'stat']
    else:
        df2 = pit[(pit['Org']==org) & (pit['League']==lg)].groupby('PID').agg({'First':'last', 'Last':'last', 'Team':'last', 'Outs':'sum', 'R':'sum', 'ER':'sum', 'H':'sum', 'BB':'sum', 'HBP':'sum', 'ABA':'sum', 'K':'sum', 'W':'sum', 'L':'sum', 'Sv':'sum', 'CG':'sum', 'WAR':'sum'}).sort_values([stat, 'Outs'], ascending=[False, True]).head(50).reset_index()
        df2['WAR'] = df2['WAR'].apply(lambda x: round(x,1))
        df2['IP'] = df2['Outs'].apply(lambda x: str(math.floor(x/3))+"."+str(x % 3))
        df2['stat'] = df2[stat]
        df2 = df2[df2['Outs']>=qual]
    return templates.TemplateResponse("career_records.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'stat':stat, 'recent_year':pit.Year.max(), 'type':'pitching', 'qual':qual})
