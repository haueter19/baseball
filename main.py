from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import pandas as pd
import numpy as np
#mabl = pd.read_csv('C:\\Users\\Daniel\\Documents\\Python Scripts\\MABL_Hitting.csv')
#rrl = pd.read_csv('C:\\Users\\Daniel\\Documents\\Python Scripts\\RRL_Hitting.csv')
#mscr = pd.read_csv('C:\\Users\\Daniel\\Documents\\Python Scripts\\hitting.csv')
df = pd.read_csv('Master_Hitting.csv')
df['League'].fillna('None', inplace=True)
df['Team'].fillna('None', inplace=True)
maxYear = df['Year'].max()
df.loc[df['Year']==2019, 'den'] = 4
df.loc[df['Year']==2018, 'den'] = 3
df.loc[df['Year']==2017, 'den'] = 2
df.loc[df['Year']==2016, 'den'] = 1
common_stat_list = ['GP', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB', 'wRAA', 'RC']
for i in ['GP', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB', 'wRAA', 'den']:
    df[i].fillna(0, inplace=True)

for i in ['PID', 'H', '1B', '2B', 'K', 'SF', 'SH']:
    df[i] = df[i].astype(int)

pit = pd.read_csv('Master_Pitching.csv')
pit['League'].fillna('None', inplace=True)
pit['Team'].fillna('None', inplace=True)
pit['ABA'] = pit['Outs']+pit['H']
pit['BAA'] = pit['H']/pit['ABA']
pit['PAA'] = pit['Outs']+pit['H']+pit['BB']+pit['HBP']
pit['BB_rate'] = pit['BB']/pit['PAA']
pit['HBP_rate'] = pit['HBP']/pit['PAA']
pit['K_rate'] = pit['K']/pit['PAA']
pit['H_rate'] = pit['H']/pit['PAA']

def add_rate_stats(z):
    z['BA'] = round(z['H']/z['AB'],3)
    z['OBP'] = round((z['H']+z['BB']+z['HBP'])/(z['AB']+z['BB']+z['HBP']+z['SF']),3)
    z['SLG'] = round(z['TB']/z['AB'],3)
    z['OPS'] = round(z['SLG'] + z['OBP'],3)
    return z

def add_runs_created(z):
    z['RC'] = round(((((2.4*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF']))+(z['H']+z['BB']-z['CS']+z['HBP']))*((3*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF']))+((1.25*(z['H']-z['2B']-z['3B']-z['HR']))+(1.69*z['2B'])+(3.02*z['3B'])+(3.73*z['HR'])+(.29*(z['BB']+z['HBP']))+(.492*(z['SH']+z['SF']+z['SB']))-(.4*z['K']))))/(9*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF'])))-(.9*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF'])),2)
    return z

def add_lg_woba(z):
    z['wOBA'] = round(((0.691*z['BB']) + (0.722*z['HBP']) + (0.884*z['1B']) + (1.257*z['2B']) + (1.593*z['3B']) + (2.058*z['HR'])) / (z['AB'] + z['BB'] + z['HBP'] + z['SF']),3)
    return z

def make_lg_avg(z):
    stats = ['GP', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']
    #lgR = z.groupby(['Org', 'League', 'Year'])['R'].sum().reset_index(name='lgR')['lgR']
    #lgPA = z.groupby(['Org', 'League', 'Year'])['PA'].sum().reset_index(name='lgPA')['lgPA']
    z = z.groupby(['Org', 'League', 'Year']).agg({'GP':'mean', 'PA':'mean', 'AB':'mean', 'R':'mean', 'H':'mean', '1B':'mean', '2B':'mean', '3B':'mean', 'HR':'mean', 'RBI':'mean', 'BB':'mean', 'K':'mean', 'HBP':'mean', 'SB':'mean', 'CS':'mean', 'SF':'mean', 'SH':'mean', 'TB':'mean'}).reset_index()
    z['lgR'] = z.groupby(['Org', 'League', 'Year'])['R'].sum().reset_index(name='lgR')['lgR']
    z['lgPA'] = z.groupby(['Org', 'League', 'Year'])['PA'].sum().reset_index(name='lgPA')['lgPA']
    #z = z.merge(lgR, on=[['Org', 'League', 'Year']], how='inner')
    for i in stats:
        z[i] = round(z[i],1)
    add_rate_stats(z)
    add_lg_woba(z)
    z['wOBAscale'] = z['OBP']/z['wOBA']
    return z

def add_ops_plus(z, avg):
    #(OBP / lgOBP + SLG / lgSLG - 1) * 100
    z = z.merge(avg[['Org', 'League', 'Year', 'lgR', 'lgPA', 'BA', 'OBP', 'SLG', 'OPS', 'wOBA', 'wOBAscale']], on=['Org', 'League', 'Year'], suffixes=['', '_lg'], how='inner')
    z['OPS+'] = round((z['OBP']/z['OBP_lg'] + z['SLG']/z['SLG_lg'] -1)*100,0)
    return z

def add_woba(z):
    #(0.691×uBB + 0.722×HBP + 0.884×1B + 1.257×2B + 1.593×3B + 2.058×HR) / (AB + BB – IBB + SF + HBP)
    z['wOBA'] = round(((0.691*z['BB']) + (0.722*z['HBP']) + (0.884*z['1B']) + (1.257*z['2B']) + (1.593*z['3B']) + (2.058*z['HR'])) / (z['AB'] + z['BB'] + z['HBP'] + z['SF']),3)
    return z

def add_wRAA(z, avg):
    #wRAA formula = ((wOBA-lgwOBA)/wOBAScale)*PA;
    #z = z.merge(avg[['Org', 'League', 'Year', 'wOBA', 'wOBAscale']], on=['Org', 'League', 'Year'], suffixes=['', '_lg'], how='outer')
    z['wRAAc'] = round(((z['wOBA'] - z['wOBA_lg']) / z['wOBAscale'])*z['PA'],2)
    return z

def add_wRC(z, avg):
    #wRC = (((wOBA-League wOBA)/wOBA Scale)+(League R/PA))*PA
    #z = z.merge(avg[['Org', 'League', 'Year', 'wOBA']], on=['Org', 'League', 'Year'], suffixes=['', '_lg'], how='outer')
    z['wRC'] = round((((z['wOBA'] - z['wOBA_lg']) / z['wOBAscale']) + (z['lgR'] / z['lgPA'])) * z['PA'],1)
    return z

def add_wRC_plus(z, avg):
    #wRC+ = (((wRAA/PA + League R/PA) + (League R/PA – Park Factor* League R/PA))/ (AL or NL wRC/PA excluding pitchers))*100
    z['wRC+'] = round(((z['wRAAc']/z['PA'] + z['lgR']/z['lgPA'])  / (z['lgR']/z['lgPA'])) * 100, 0)
    return z

df = add_rate_stats(df)
df['OBP'].fillna(0, inplace=True)
df['SLG'].fillna(0, inplace=True)
df['OPS'].fillna(0, inplace=True)
df = add_woba(df)
h_lg_avg = make_lg_avg(df)
df = add_ops_plus(df, h_lg_avg)
df = add_wRAA(df, h_lg_avg)
df = add_wRC(df, h_lg_avg)
df = add_wRC_plus(df, h_lg_avg)
df['wRC+'].fillna(0, inplace=True)
df['wRC+'] = df['wRC+'].astype(int)

#add_rate_stats(h_lg_avg)

def add_team_totals(z):
    dict = {'PID':0, 'First':'Team', 'Last': 'Totals'}
    for i in common_stat_list:
        dict.update({i: round(z[i].sum(),1)})
    dict.update({'BA':round(z['H'].sum()/z['AB'].sum(),3)})
    dict.update({'OBP':round((z['H'].sum()+z['BB'].sum()+z['HBP'].sum())/(z['AB'].sum()+z['BB'].sum()+z['HBP'].sum()+z['SF'].sum()),3)})
    dict.update({'SLG':round(z['TB'].sum()/z['AB'].sum(),3)})
    dict.update({'OPS':round((z['H'].sum()+z['BB'].sum()+z['HBP'].sum())/(z['AB'].sum()+z['BB'].sum()+z['HBP'].sum()+z['SF'].sum())+(z['TB'].sum()/z['AB'].sum()), 3)})
    dict.update({'wRAAc':round(z['wRAAc'].sum(), 1)})
    z = z.append(dict, ignore_index = True)
    return z

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/{org}/stats", response_class=HTMLResponse)
async def stats_page(request: Request, org: str, team: Optional[str] = None, sort: Optional[str] = None, year: Optional[str] = None, league: Optional[str] = None, asc: Optional[bool] = False):
    df2 = df[df["Org"]==org]
    if team==None:
        pass
    else:
        df2 = df2[df2['Team']==team]
    if year==None:
        pass
    else:
        df2 = df2[df2['Year']==year]
    if league==None:
        pass
    else:
        df2 = df2[df2['League']==league]
    if sort==None:
        sort = 'PA'
    
    team_list = df2['Team'].unique().tolist()
    df2 = df2.sort_values([sort, "Year"], ascending=asc)
    return templates.TemplateResponse("index.html", {"request": request, "org":org, "df":df2.to_html(index=False), "league":league, "tm":team, "year":year, "sort":sort, "asc":asc, "teams":team_list})

@app.get("/player/")
async def player(request: Request):
    #df2 = df['PID'].unique().tolist()
    df2 = df.copy()
    df2 = df2.groupby('PID').agg({'First':'first', 'Last':'first'}).reset_index()
    return templates.TemplateResponse("players.html", {"request": request, 'df':df2, 'fname':'', 'lname':''})

@app.get("/player/{pid}")
async def player_page(request: Request, pid: int):
    df2 = df[df['PID']==pid]
    df2 = df2.sort_values(['Year', 'Org'], ascending=True)
    gp = df2.groupby('Year').agg({'GP':'sum', 'PA':'sum', 'AB':'sum', 'R':'sum', 'H':'sum', '1B':'sum', '2B':'sum', '3B':'sum', 'HR':'sum', 'RBI':'sum', 'BB':'sum', 'K':'sum', 'HBP':'sum', 'SB':'sum', 'CS':'sum', 'SF':'sum', 'SH':'sum', 'TB':'sum', 'wRAA':'sum', 'wRAAc':'sum'}).reset_index()
    add_runs_created(gp)
    add_rate_stats(gp)
    ba = gp.H.sum()/gp.AB.sum()
    obp = (gp.H.sum()+gp.BB.sum()+gp.HBP.sum())/(gp.AB.sum()+gp.BB.sum()+gp.HBP.sum()+gp.SF.sum())
    slg = gp.TB.sum()/gp.AB.sum()
    ops = obp + slg
    gp.at[-1] = ['Career', gp.GP.sum(), gp.PA.sum(), gp.AB.sum(), gp.R.sum(), gp.H.sum(), gp['1B'].sum(), gp['2B'].sum(), gp['3B'].sum(), gp.HR.sum(), gp.RBI.sum(), gp.BB.sum(),gp.K.sum(),gp.HBP.sum(),gp.SB.sum(),gp.CS.sum(),gp.SF.sum(),gp.SH.sum(),gp.TB.sum(),gp.wRAA.sum(),gp.wRAAc.sum(),gp.RC.sum(), ba,obp,slg,ops]
    return templates.TemplateResponse("players.html", {"request": request, "df":df.groupby('PID').agg({'First':'first', 'Last':'first'}).reset_index(), "df2":gp.to_html(index=False), 'fname':df2.First.max(), 'lname':df2.Last.max()})

@app.get("/sim", response_class=HTMLResponse)
async def run_sims(request: Request, org: Optional[str] = 'MABL', lg: Optional[str] = '35+', innings: Optional[int] = 7, sims: Optional[int] = 100, go: Optional[int] = 0, away_lineup: Optional[str] = '2432+1781+304+876+2019+1125+750+2043+484+376', away_pitcher: Optional[int] = 484, home_lineup: Optional[str] = '579+492+391+825+1632+495+1605+1978+509', home_pitcher: Optional[int] = 825):
    import urllib.parse
    away_lineup = urllib.parse.unquote(away_lineup)
    home_lineup = urllib.parse.unquote(home_lineup)
    if "+" in lg:
        pass
    else:
        lg = lg+"+"
    away_lineup = away_lineup.split('+')
    for i in range(len(away_lineup)):
        away_lineup[i] = int(away_lineup[i])
    home_lineup = home_lineup.split('+')
    for i in range(len(home_lineup)):
        home_lineup[i] = int(home_lineup[i])
    from projections import make_projections
    plyrs = make_projections(df[(df['Org']==org) & (df['League']==lg) & (df['Year']>2015)], 50)
    plyrs.drop(columns='PID',inplace=True)
    plyrs = plyrs.reset_index()
    prj_away = plyrs[plyrs['PID'].isin(away_lineup)].set_index('PID').reindex(away_lineup).reset_index()
    for i in ['1B', '2B', '3B', 'HR', 'BB', 'HBP', 'K']:
        prj_away[i+'_per_PA'] = round(prj_away[i]/prj_away['PA'],3)
    prj_home = plyrs[plyrs['PID'].isin(home_lineup)].set_index('PID').reindex(home_lineup).reset_index()
    for i in ['1B', '2B', '3B', 'HR', 'BB', 'HBP', 'K']:
        prj_home[i+'_per_PA'] = round(prj_home[i]/prj_home['PA'],3)    
    lg_pitchers = pit[(pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]
    home_pitcher_df = pit[(pit['PID']==home_pitcher) & (pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]
    away_pitcher_df = pit[(pit['PID']==away_pitcher) & (pit['Org']==org) & (pit['League']==lg) & (pit['Year']==2019)]
    from sim_game import run_sim
    if go!=0:
        rpg_away = run_sim(prj_away, home_pitcher_df, innings, sims)
        rpg_home = run_sim(prj_home, away_pitcher_df, innings, sims)
        score = str(rpg_away)+' - '+str(rpg_home)
    else:
        score = 'No sims run'
    return templates.TemplateResponse("sim.html", {'request': request, 'org':org, 'lg':lg, 'score':score, 'plyrs':plyrs, 'lg_pitchers':lg_pitchers, 'away_team':away_lineup, "away_pitcher":away_pitcher, "home_team":home_lineup, "home_pitcher":home_pitcher})

@app.get("{org}/teams")
async def teams_page(request: Request, org: Optional[str] = None, league: Optional[str] = None, year: Optional[int] = None, tm: Optional[str] = None, sort: Optional[str] = None):
    df2 = df[(df['Org']==org) & (df['League']==league) & (df['Team']==tm) & (df['Year']==year)][['PID', 'Team', 'First', 'Last', 'GP', 'PA', 'AB', 'R', 'H','1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']]
    if sort==None:
        sort="PA"
    add_rate_stats(df2)
    df2 = df2.sort_values(sort, ascending=False)
    df3 = df[(df['Org']==org) & (df['League']==league) & (df['Year']==year)]
    tms = df3.Team.unique().tolist()
    yrs = df[(df['Org']==org) & (df['League']==league)].Year.unique().tolist()
    return templates.TemplateResponse("teams.html", {"request": request, 'df':df2.to_html(index=False), 'tms':tms, 'yrs':yrs})

@app.get('/')
async def slash():
    return RedirectResponse("/home")

@app.get("/home")
async def home(request: Request):
    orgs = df['Org'].sort_values().unique()
    return templates.TemplateResponse("home.html", {"request": request, 'orgs':orgs})

@app.get("/standings/{org}/{lg}/{yr}")
async def standings(request: Request, org: str, lg: str, yr: int):
    st = pd.read_csv('standings.csv')
    st = st[(st['Org']==org) & (st['League']==lg) & (st['Year']==yr)].sort_values('Pct', ascending=False)
    st['GP'] = st['W']+st['L']+st['T']
    st['Pyth'] = round(((st['RF']*st['RF']) / ((st['RF']*st['RF']) + (st['RA']*st['RA']))),3)
    st['xW'] = round(st['Pyth']*st['GP'],1)
    return templates.TemplateResponse("standings.html", {'request': request, 'st':st, 'org':org, 'lg':lg, 'yr':yr})

@app.get("/stats/team/{org}/{lg}/{yr}")
async def team_stats_year(request: Request, org: str, lg: str, yr: int):
    df2 = df[(df['Org']==org) & (df['League']==lg) & (df['Year']==yr)]
    df2 = df2.groupby('Team').agg({'Org':'first', 'League':'first', 'Year':'first', 'GP':'sum', 'PA':'sum', 'K':'sum', 'SB':'sum', 'CS':'sum', '1B':'sum', '2B':'sum', '3B':'sum', 'HR':'sum', 'R':'sum', 'RBI':'sum', 'H':'sum', 'BB':'sum', 'HBP':'sum', 'SF':'sum', 'TB':'sum', 'AB':'sum', 'SH':'sum', 'wRAAc':'sum'}).reset_index()
    add_rate_stats(df2)
    add_woba(df2)
    df2 = add_ops_plus(df2, h_lg_avg)
    add_wRC(df2, h_lg_avg)
    add_wRC_plus(df2, h_lg_avg)
    df2['wRAAc'] = round(df2['wRAAc'],1)
    df2 = df2.sort_values('wRAAc', ascending=False)
    df2.drop(columns=['Org', 'League', 'Year'],inplace=True)
    st = pd.read_csv('standings.csv')
    st = st[(st['Org']==org) & (st['League']==lg) & (st['Year']==yr)]
    df2 = df2.merge(st, on='Team', how='left')
    maxYear = 2019#df2.Year.max()
    return templates.TemplateResponse("stats_team_view.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'yr':yr, 'maxYear':maxYear})

@app.get("/records/season/{org}/{lg}")
async def season_records(request: Request, org: str, lg: str, stat: Optional[str] = 'H'):
    df2 = df[(df['Org']==org) & (df['League']==lg) & (df['PA']>25)].sort_values(stat, ascending=False).head(20)
    #df2.columns=['PID', 'First', 'Last', 'Team', 'Year', 'PA', 'stat']
    df2['stat'] = df2[stat]
    return templates.TemplateResponse("season_records.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'stat':stat})

@app.get("/records/career/{org}/{lg}")
async def career_records(request: Request, org: str, lg: str, stat: Optional[str] = 'H'):
    if stat in ['BA', 'OBP', 'SLG', 'OPS']:
        df2 = df[(df['Org']==org) & (df['League']==lg)].groupby('PID').agg({'First':'last', 'Last':'last', 'Team':'last', 'PA':'sum', 'H':'sum', 'BB':'sum', 'HBP':'sum', 'AB':'sum', 'TB':'sum', 'SF':'sum'})
        df2 = add_rate_stats(df2)
        df2 = df2.query('PA>=100').sort_values(stat, ascending=False).head(20).reset_index()
        df2['stat'] = df2[stat]
        df2.columns=['PID', 'First', 'Last', 'Team', 'PA', 'H', 'BB', 'HBP', 'AB', 'TB', 'SF', 'BA', 'OBP', 'SLG','OPS', 'stat']
    else:
        df2 = df[(df['Org']==org) & (df['League']==lg)].groupby('PID').agg({'First':'last', 'Last':'last', 'Team':'last', 'PA':'sum', 'H':'sum', 'BB':'sum', 'HBP':'sum', 'AB':'sum', 'TB':'sum', 'SF':'sum'}).sort_values(stat, ascending=False).head(20).reset_index()
        df2['stat'] = df2[stat]
        df2 = add_rate_stats(df2)
        df2 = df2[df2['PA']>=100]
    return templates.TemplateResponse("career_records.html", {'request': request, 'df2':df2, 'org':org, 'lg':lg, 'stat':stat})

@app.get("/{org}/{lg}/{tm}/projections")
async def league(request: Request, org: str, lg: str, tm: str):
    df2 = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Team']==tm) & (df['Year'].isin([2019, 2018, 2017, 2016]))]
    from projections import make_projections
    pa = 50
    df2 = make_projections(df2, pa)
    add_woba(df2)
    return templates.TemplateResponse("projections.html", {"request": request, 'org':org, 'lg':lg, 'df':df2.to_html(index=False), 'df2':df2, 'pid':df2['PID']})

@app.get("/{org}")
async def org(request: Request, org: str):
    df2 = df[df['Org']==org.upper()]
    lgs = df2['League'].sort_values().unique()
    return templates.TemplateResponse("org.html", {"request": request, 'org':org, 'lgs':lgs})

@app.get("/{org}/{lg}/champions")
async def standings(request: Request, org: str, lg: str):
    standings = pd.read_csv('standings.csv')
    post_winners = standings[(standings['Org']==org.upper()) & (standings['League']==lg) & (standings['Postseason']==1)][['Year', 'Team']].sort_values('Year', ascending=False)
    post_winners.columns=['Year', 'Playoffs']
    season_winners = standings[(standings['Org']==org.upper()) & (standings['League']==lg) & (standings['Season']==1)][['Year', 'Team']].sort_values('Year', ascending=False)
    season_winners.columns=['Year', 'Season']
    champs = post_winners.merge(season_winners, on='Year', how='outer')
    return templates.TemplateResponse("champions.html", {'request': request, 'org': org, 'lg': lg, "champs": champs})

@app.get("/{org}/{lg}")
async def league(request: Request, org: str, lg: str):
    df2 = df[(df['Org']==org.upper()) & (df['League']==lg)]
    _list = df[(df['Org']==org.upper()) & (df['League']==lg)].sort_values('Year').groupby('Team')['Year'].unique()#.reset_index()
    #names_list = _list.Team
    #year_list = _list.Year
    tms = df2['Team'].sort_values().unique()
    maxYear = df2.Year.max()
    return templates.TemplateResponse("league.html", {"request": request, 'org':org, 'lg':lg, 'tms':tms, 'maxYear':maxYear, 'yr_list': _list.to_dict()})

@app.get("/{org}/{lg}/{tm}")
async def orglgtm(request: Request, org: str, lg: str, tm: str):
    df2 = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Team']==tm)]
    yrs = df2['Year'].sort_values().unique()
    return templates.TemplateResponse("team.html", {"request": request, 'org':org, 'lg':lg, 'tm':tm, 'yrs':yrs})

@app.get("/{org}/{lg}/league/{yr}")
async def stats_by_league(request: Request, org: str, lg: str, yr: int, sort: Optional[str] = None, asc: Optional[bool] = False):
    df2 = df[(df['Org']==org) & (df['League']==lg) & (df['Year']==yr)]
    add_rate_stats(df2)
    add_runs_created(df2)
    lgtot = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Year']==yr)]
    lgSLG = lgtot['TB'].sum()/lgtot['AB'].sum()
    lgOBP = (lgtot['H'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum())/(lgtot['AB'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum()+lgtot['SF'].sum())
    lgwOBA = round(((0.691*lgtot['BB'].sum()) + (0.722*lgtot['HBP'].sum()) + (0.884*lgtot['1B'].sum()) + (1.257*lgtot['2B'].sum()) + (1.593*lgtot['3B'].sum()) + (2.058*lgtot['HR'].sum())) / (lgtot['AB'].sum() + lgtot['BB'].sum() + lgtot['HBP'].sum() + lgtot['SF'].sum()),3)
    lgR = lgtot['R'].sum()
    lgPA = lgtot['PA'].sum()
    wOBAscale = lgOBP/lgwOBA
    #add_ops_plus(df2, lgOBP, lgSLG)
    add_woba(df2)
    #add_wRAA(df2, lgwOBA, wOBAscale)
    #add_wRC(df2, lgwOBA, wOBAscale, lgR, lgPA)
    #add_wRC_plus(df2, lgR, lgPA)
    df2['wRC+'].fillna(0,inplace=True)
    df2['wRC+'] = df2['wRC+'].astype(int)
    if asc==None:
        asc=False
    if sort==None:
        df2 = df2.sort_values('wRAAc', ascending=asc)
    else:
        df2 = df2.sort_values(sort, ascending=asc)
    return templates.TemplateResponse('league_stats.html', {"request": request, 'org':org, 'lg':lg, 'yr':yr, 'df':df2.to_html(index=False, justify='right'), 'df2':df2, 'pid':df2['PID'], 'sort': sort, 'asc': asc})

@app.get("/{org}/{lg}/{tm}/{yr}")
async def team_stats(request: Request, org: str, lg: str, tm: str, yr: int, sort: Optional[str] = None, asc: Optional[bool] = False):
    df2 = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Team']==tm) & (df['Year']==yr)][['PID', 'First', 'Last', 'GP', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB', 'wRAA', 'BA', 'OBP', 'SLG', 'OPS', 'OPS+', 'wRAAc', 'wOBA', 'wRC', 'wRC+']]
    df2['PID'] = df2['PID'].astype(int)
    add_rate_stats(df2)
    add_runs_created(df2)
    lgtot = df[(df['Org']==org.upper()) & (df['League']==lg) & (df['Year']==yr)]
    lgSLG = lgtot['TB'].sum()/lgtot['AB'].sum()
    lgOBP = (lgtot['H'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum())/(lgtot['AB'].sum()+lgtot['BB'].sum()+lgtot['HBP'].sum()+lgtot['SF'].sum())
    lgwOBA = round(((0.691*lgtot['BB'].sum()) + (0.722*lgtot['HBP'].sum()) + (0.884*lgtot['1B'].sum()) + (1.257*lgtot['2B'].sum()) + (1.593*lgtot['3B'].sum()) + (2.058*lgtot['HR'].sum())) / (lgtot['AB'].sum() + lgtot['BB'].sum() + lgtot['HBP'].sum() + lgtot['SF'].sum()),3)
    lgR = lgtot['R'].sum()
    lgPA = lgtot['PA'].sum()
    wOBAscale = lgOBP/lgwOBA
    #add_ops_plus(df2, lgOBP, lgSLG)
    add_woba(df2)
    #add_wRAA(df2, lgwOBA, wOBAscale)
    #add_wRC(df2, lgwOBA, wOBAscale, lgR, lgPA)
    #add_wRC_plus(df2, lgR, lgPA)
    #df2['wRC+'].fillna(0,inplace=True)
    #df2['wRC+'] = df2['wRC+'].astype(int)
    #df2.append({'Team Totals', df2['GP'].sum(), df2['PA'].sum(), df2['AB'].sum(), df2['R'].sum(), df2['H'].sum(), df2['1B'].sum(), df2['2B'].sum(), df2['3B'].sum(), df2['HR'].sum(), df2['RBI'].sum(), df2['BB'].sum(), df2['K'].sum(), df2['HBP'].sum(), df2['SB'].sum(), df2['CS'].sum(), df2['SF'].sum(), df2['SH'].sum(), df2['TB'].sum(), df2['wRAA'].sum(), df2['RC'].sum(), round(df2['H'].sum()/df2['AB'].sum(),3), '-', '-', '-', '-', '-', '-', '-', '-']
    if asc==None:
        asc=False
    if sort==None:
        df2 = df2.sort_values('wRAAc', ascending=False)
    else:
        df2 = df2.sort_values(sort, ascending=asc)
    df2 = add_team_totals(df2)
    lg_stats = h_lg_avg[(h_lg_avg['Org']==org) & (h_lg_avg['League']==lg) & (h_lg_avg['Year']==yr)]
    return templates.TemplateResponse("team_stats.html", {"request": request, 'org':org, 'lg':lg, 'tm':tm, 'yr':yr, 'df2':df2, 'lg_stats':lg_stats, 'pid':df2['PID'], 'sort': sort, 'asc': asc})
