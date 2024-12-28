from cache import cache
import json
import os
import pandas as pd
import plotly
import plotly.graph_objects as go
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
from logos import logos



router = APIRouter(prefix='/{org}', responses={404: {"description": "Not found"}})

@router.get("/")
async def org(request: Request, org: str):
    df2 = cache.get_hitting_data(org=org)
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
    standings = cache.get_standings_data(org=org, league=lg)
    post_winners = standings[(standings['Org']==org.upper()) & (standings['League']==lg) & (standings['Postseason']==1)][['Year', 'Team']].sort_values('Year', ascending=False)
    post_winners.columns=['Year', 'Playoffs']
    season_winners = standings[(standings['Org']==org.upper()) & (standings['League']==lg) & (standings['Season']==1)][['Year', 'Team']].sort_values('Year', ascending=False)
    season_winners.columns=['Year', 'Season']
    champs = post_winners.merge(season_winners, on='Year', how='outer')
    return templates.TemplateResponse("champions.html", {'request': request, 'org': org, 'lg': lg, "champs": champs, 'logos':logos})



@router.get("/{lg}")
async def league(request: Request, org: str, lg: str):
    standings_years = cache.get_standings_data(org=org, league=lg)['Year'].sort_values().unique().tolist()
    df2 = cache.get_hitting_data(org=org, league=lg)
    _list = df2.sort_values('Year').groupby('Team')['Year'].unique()#.reset_index()
    print(df2['Team'].unique())
    tms = df2['Team'].sort_values().unique()
    maxYear = df2.Year.max()
    minYear = df2.Year.min()
    yrs = df2['Year'].sort_values().unique().tolist()
    return templates.TemplateResponse("league.html", {"request": request, 'org':org, 'lg':lg, 'tms':tms, 'maxYear':maxYear, 'minYear':minYear, 
                                        'yrs':yrs, 'yr_list': _list.to_dict(), 'standings_years':standings_years, 'standings_max_year':standings_years[-1], 'logos':logos})



@router.get("/{lg}/{tm}/gallery")
async def orglgtm(request: Request, org: str, lg: str, tm: str):
    path = os.path.join('static', 'images', org, lg, tm)
    img_list = os.listdir(path)
    return templates.TemplateResponse('gallery.html', {'request':request, 'org':org, 'lg':lg, 'tm':tm, 'len':len(img_list), 'img_list':img_list})




def career_line_chart(data_dict):
    fig = go.Figure()
    for i in data_dict:
        fig.add_trace(
            go.Scatter(
                name=data_dict[i]['first']+' '+data_dict[i]['last'],
                x=[n+1 for n in list(range(len(data_dict[i]['data'])))],
                y=data_dict[i]['data'],
                marker_color = 'gray',
                opacity = .2,
                showlegend=False,
            )
        )

    # Update the specific trace to make it stand out
    index_to_highlight = list(data_dict.keys()).index(876)
    fig.data[index_to_highlight].update(
        marker_color='red',  # Change the color to red
        opacity=1,  # Make it fully opaque
        showlegend=True  # Show this line in the legend
    )

    fig.update_layout(
        height=650,
        template="seaborn",
        xaxis_dtick = 1,
        xaxis_title = 'Years'
    )
    return fig




@router.get("/{lg}/charts", response_class=HTMLResponse)
async def main_charts_page(request: Request, org: str, lg:str):
    #stats = cache.get_hitting_data(org=org, league=lg).columns.tolist()
    #stats = [stat for stat in stats if stat not in ['PID', 'First', 'Last', 'Team', 'Org', 'League', 'Year']]
    stats = ['wRAAc', 'WAR', 'H', 'R', 'RBI', 'single', 'double', 'triple', 'HR', 'TB', 'BB', 'HBP', 'K', 'SB', 'CS', 'SF', 'SH', 'GP', 'GS', 'PA', 'AB', 'ROE', 'FC', 'LOB', 'All_Star']
    return templates.TemplateResponse('league_charts.html', {'request':request, 'org':org, 'lg':lg, "statList":stats})


@router.get("/{lg}/charts/player_comparison/{stat}")
async def cumsum_chart(request: Request, org: str, lg: str, stat: Optional[str] = 'wRAAc'):
    z = cache.get_hitting_data(org=org, league=lg)
    num_of_teams_check = z.groupby('Year')['Team'].nunique().reset_index()
    years_with_league_data = num_of_teams_check[num_of_teams_check ['Team']>2]['Year'].tolist()
    players = z[['PID', 'First', 'Last']].drop_duplicates()
    zz = pd.pivot_table(z[z['Year'].isin(years_with_league_data)], index='PID', columns='Year', values=stat, aggfunc='sum')
    zz = zz.cumsum(axis=1)

    data_dict = {}
    num_of_years = len(years_with_league_data)#z.Year.max() - z.Year.min()
    for i, row in zz.iterrows():
        d = zz.loc[i]
        s = zz.loc[i].notna()
        years_to_pad = num_of_years - len(d[d.index.isin(s[s].index)].tolist())
        data_dict[i] = {'data':d[d.index.isin(s[s].index)].tolist() + [None] * years_to_pad,
                        'first': '' if players[players['PID']==i]['First'].iloc[0] == None else players[players['PID']==i]['First'].iloc[0],
                        'last': '' if players[players['PID']==i]['Last'].iloc[0] == None else players[players['PID']==i]['Last'].iloc[0],
                    }
    chart_data = career_line_chart(data_dict)

    chart_data = json.dumps(chart_data, cls=plotly.utils.PlotlyJSONEncoder)
    return chart_data



def group_by_age(age, lg):
    if lg=='18+':
        age_range = (18,44)
    elif lg=='35+':
        age_range = (35,51)
    else:
        age_range = (17, 80)
    age_gp = age[(age['League']==lg) & (age['Age'].between(age_range[0], age_range[1]))].groupby('Age').agg({'id':'count', 'H':'sum', 'AB':'sum', 'TB':'sum', 'BB':'sum', 'HBP':'sum', 'SF':'sum', 'wRAAc':'mean'}).reset_index()
    age_gp['BA'] = round(age_gp['H']/age_gp['AB'],3)
    age_gp['SLG'] = round(age_gp['TB']/age_gp['AB'],3)
    age_gp['OBP'] = (age_gp['H']+age_gp['BB']+age_gp['HBP']) / (age_gp['AB']+age_gp['HBP']+age_gp['BB']+age_gp['SF'])
    age_gp['OPS'] = age_gp['OBP']+age_gp['SLG']
    age_gp['BA'] = age_gp['BA'].rolling(3, min_periods=1).mean()
    age_gp['OBP'] = age_gp['OBP'].rolling(3, min_periods=1).mean()
    age_gp['SLG'] = age_gp['SLG'].rolling(3, min_periods=1).mean()
    age_gp['OPS'] = age_gp['OPS'].rolling(3, min_periods=1).mean()
    age_gp['wRAAc'] = age_gp['wRAAc'].rolling(3, min_periods=1).mean()
    age_gp.rename(columns={'id':'n'},inplace=True)
    return age_gp


@router.get("/{lg}/charts/aging_curve/{stat}")
async def aging_curve(request: Request, org: str, lg: str, stat: Optional[str] = None):
    df = cache.get_hitting_data(org=org, league=lg)
    if lg == '35+':
        df = df[df['Age']>=35]
    elif lg == '45+':
        df = df[df['Age']>=45]
    elif lg == '55+':
        df = df[df['Age']>=52]
    else:
        df = df[df['Age']>=17]

    age_gp = group_by_age(df, lg)
    print(age_gp)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            name='18+',
            x=age_gp['Age'],
            y=age_gp[stat],
            mode='lines+markers',
        )
    )
    fig.update_layout(
        template="seaborn",
        height=650,
        xaxis_title = 'Age',
        xaxis_dtick = 1,
        #yaxis = dict('title'='stat'), 
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)