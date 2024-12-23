from cache import cache
import math
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
#from data_init import df, pit
import functions

router = APIRouter(prefix='/player', responses={404: {"description": "Not found"}})

@router.get("/")
async def player(request: Request, org: Optional[str] = 'MABL', lg: Optional[str] = '18+'):
    df2 = cache.get_hitting_data(org=org, league=lg)
    df2 = df2.groupby('PID').agg({'First':'first', 'Last':'first'}).reset_index()
    return RedirectResponse('/player/876')

@router.get("/{pid}")
async def player_page(request: Request, pid: int = 876, org: Optional[str] = 'MABL', lg: Optional[str] = '18+'):
    #hitting section
    players = cache.get_player_data()
    df2 = cache.get_hitting_data(pid=pid)
    df2 = df2.sort_values(['Year', 'Org'], ascending=True)
    gp = df2.groupby('Year').agg({'GP':'sum', 'PA':'sum', 'AB':'sum', 'R':'sum', 'H':'sum', 'single':'sum', 'double':'sum', 'triple':'sum', 'HR':'sum', 'RBI':'sum', 'BB':'sum', 'K':'sum', 'HBP':'sum', 'SB':'sum', 'CS':'sum', 'SF':'sum', 'SH':'sum', 'TB':'sum', 'wRAAc':'sum', 'WAR':'sum'}).reset_index()
    functions.add_runs_created(gp)
    functions.add_rate_stats(gp)
    ba = round(gp.H.sum()/gp.AB.sum(),3)
    obp = round((gp.H.sum()+gp.BB.sum()+gp.HBP.sum())/(gp.AB.sum()+gp.BB.sum()+gp.HBP.sum()+gp.SF.sum()),3)
    slg = round(gp.TB.sum()/gp.AB.sum(),3)
    ops = round(obp + slg,3)
    gp.loc[-1] = ['Career', gp.GP.sum(), gp.PA.sum(), gp.AB.sum(), gp.R.sum(), gp.H.sum(), gp['single'].sum(), gp['double'].sum(), gp['triple'].sum(), gp.HR.sum(), gp.RBI.sum(), gp.BB.sum(),gp.K.sum(),gp.HBP.sum(),gp.SB.sum(),gp.CS.sum(),gp.SF.sum(),gp.SH.sum(),gp.TB.sum(),round(gp.wRAAc.sum(),2), round(gp.WAR.sum(),2), round(gp.RC.sum(),2), ba,obp,slg,ops]
    for col in ['GP', 'PA', 'AB', 'R', 'H','single', 'double', 'triple', 'HR', 'RBI', 'BB', 'K','HBP', 'SB', 'CS', 'SF', 'SH', 'TB']:
        gp[col] = gp[col].astype(int)
    for col in ['wRAAc', 'WAR']:
        gp[col] = round(gp[col],3)
    gp['Year'] = gp['Year'].apply(lambda x: int(x) if x != 'Career' else x)
    gp2 = df2.groupby(['Year', 'Org', 'League']).agg({'Team':'first', 'GP':'sum', 'PA':'sum', 'AB':'sum', 'R':'sum', 'H':'sum', 'single':'sum', 'double':'sum', 'triple':'sum', 'HR':'sum', 'RBI':'sum', 'BB':'sum', 'K':'sum', 'HBP':'sum', 'SB':'sum', 'CS':'sum', 'SF':'sum', 'SH':'sum', 'TB':'sum', 'wRAAc':'sum', 'WAR':'sum'})
    functions.add_runs_created(gp2)
    functions.add_rate_stats(gp2)
    #pitching section
    pit2 = cache.get_pitching_data(pid=pid).sort_values(['Year', 'Org'], ascending=True)
    pit2 = pit2.groupby('Year').agg({'Outs':'sum', 'GP':'sum', 'GS':'sum', 'K':'sum', 'H':'sum', 'R':'sum', 'ER':'sum', 'BB':'sum', 'HBP':'sum', 'HR':'sum', 'CG':'sum', 'W':'sum', 'L':'sum', 'Sv':'sum', 'HLD':'sum', 'ABA':'sum', 'WAR':'sum'}).reset_index()
    pit_career = pit2.sum()
    pit2['WAR'] = pit2['WAR'].apply(lambda x: round(x,1))
    pit_career['WAR'] = round(pit_career['WAR'],1)
    pit2['IP'] = pit2['Outs'].apply(lambda x: str(math.floor(x/3))+"."+str(x % 3))
    pit_career['IP'] = str(math.floor(pit_career['Outs']/3))+"."+str(pit_career['Outs'] % 3)
    pit2['BAA'] = round(pit2['H']/pit2['ABA'],3)
    pit2['ERA'] = round(pit2['ER']/(pit2['Outs']/3)*9,2)
    pit2['WHIP'] = round((pit2['H']+pit2['BB'])/(pit2['Outs']/3),2)
    pit2['Kper9'] = round(pit2['K']/(pit2['Outs']/3)*9,1)
    pit2['BBper9'] = round(pit2['BB']/(pit2['Outs']/3)*9,1)
    pit2['Hper9'] = round(pit2['H']/(pit2['Outs']/3)*9,1)
    try:
        pit_career['BAA'] = round(pit_career['H']/pit_career['ABA'],3)
        pit_career['ERA'] = round(pit_career['ER']/(pit_career['Outs']/3)*9,2)
        pit_career['WHIP'] = round((pit_career['H']+pit_career['BB'])/(pit_career['Outs']/3),2)
        pit_career['Kper9'] = round(pit_career['K']/(pit_career['Outs']/3)*9,1)
        pit_career['BBper9'] = round(pit_career['BB']/(pit_career['Outs']/3)*9,1)
        pit_career['Hper9'] = round(pit_career['H']/(pit_career['Outs']/3)*9,1)
    except:
        pit_career['BAA'] = 0
    pit_career['Year'] = 'Career'
    # standings section
    st = cache.get_standings_data()
    cols = list(st.columns)
    st = df2.merge(st, on=['Org', 'League', 'Team', 'Year'], how='left')#[['PID', 'First', 'Last']+st.columns]
    win_df = st.groupby(['Org', 'League']).agg({'Team':'last', 'First':'first', 'Last':'first', 'W':'sum', 'L':'sum', 'T':'sum', 'RF':'sum', 'RA':'sum', 'Season':'sum', 'Postseason':'sum', 'PA':'count'}).reset_index()
    win_df['G'] = win_df['W'] + win_df['L'] + win_df['T']
    win_df['Pct'] = round(win_df['W'] / win_df['G'],3)
    win_df['ch_pct'] = round(win_df['Postseason'] / win_df['PA'],3)
    win_df['Pyth'] = round(win_df['RF']**2 / (win_df['RF']**2 + win_df['RA']**2),3)
    win_df['xWin'] = round(win_df['Pyth']*win_df['G'],1)
    win_df['W_added'] = round(win_df['W'] - win_df['xWin'],1)
    for col in ['G', 'W', 'L', 'T', 'RF', 'RA', 'Season', 'Postseason']:
        win_df[col] = win_df[col].astype(int)
    return templates.TemplateResponse("players.html", {"request": request, "df":players, "df2":gp, 'fname':df2.First.max(), 'lname':df2.Last.max(), 
                                                       'org':org, 'lg':lg, "team_list":df2.Team.unique(), 'gp2':gp2, 'pit':pit2, 'pit_career':pit_career, 
                                                       'standings':win_df})
