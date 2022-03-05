import json
import math
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import MetaData, text, Column, Integer, String, ForeignKey, Table, create_engine
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import DATETIME, TIMESTAMP
from starlette.responses import RedirectResponse
from sklearn.preprocessing import MinMaxScaler

templates = Jinja2Templates(directory="templates")

n_teams = 13
tm_players = 23
tm_dollars = 263
player_split = .65
pitcher_split = 1 - player_split
tot_dollars = n_teams * tm_dollars
tot_players = n_teams * tm_players
tot_hitters = n_teams * 14
tot_pitchers = n_teams * 9
total_z_over_0 = 701.39442#591.1999720030974
orig_conv =  (tm_dollars/tm_players)*(tot_players/total_z_over_0)
owner_list = ['Avg Joes', 'Brewbirds', 'Charmer', 'Dirty Birds', 'Harvey', 'Lil Trump', 'Lima Time', 'Midnight', 'Moms Cookin', 'Roid Ragers', 'Trouble', 'Wu-Tang', 'Young Guns']

drafted_by_pos = {
    'C':13,
    '1B':13,
    '2B':13,
    '3B':13,
    'SS':13,
    'OF':5*13,
    'MI':13,
    'CI':13,
    'DH':13*2, 
    'P':13*9
}

meta = MetaData()
engine = create_engine('sqlite:///fantasy_data.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

players = Table('players', meta,
                Column('playerid', String, primary_key=True),
                Column('Paid', Integer),
                Column('Owner', String(25)),
                Column('Timestamp', DATETIME)
    )

def scale_data(df, cols):
    """
    INPUT: 
        df: original dataframe
        list: subset of columns to scale
    OUTPUT:
        df: scaled data
    """
    scaler = MinMaxScaler()
    scaler.fit(df[cols])
    scaled_df = scaler.transform(df[cols])
    scaled_df = pd.DataFrame(scaled_df, index=df.index)
    scaled_df.columns=[df[cols].columns.tolist()]
    return scaled_df

def add_distance_metrics(h, player_id, col_list):
    scaled_df = scale_data(h[h['Owner'].isna()].set_index('playerid'), col_list)
    df2 = h[h['Owner'].isna()].loc[:,['playerid', 'Name', 'Pos']+col_list].set_index('playerid')
    for j, row in scaled_df.iterrows():
        #df2.at[j,'corr'] = pearsonr(scaled_df.loc[player_id,col_list],row[col_list])[0]
        df2.at[j,'eucl_dist'] = np.linalg.norm(scaled_df.loc[player_id,col_list] - row[col_list])
        #df2.at[j,'manh_dist']= sum(abs(e - s) for s, e in zip(scaled_df.loc[player_id,col_list], row[col_list]))
    return df2.sort_values('eucl_dist').iloc[1:11]

def next_closest_in_tier(df, pos, playerid):
    try:
        i = df[(df['Primary_Pos']==pos) & (df['playerid']==playerid) & (df['Owner'].isna())].index[0]
        val = df[(df['Primary_Pos']==pos) & (df['Owner'].isna()) & (df['playerid']==playerid)]['Value'].iloc[0]
        return round(df[df['playerid']==playerid]['Value'].iloc[0] - df[(df['Primary_Pos']==pos) & (df['Owner'].isna()) & (df['Value']<=val)].iloc[1]['Value'],1)
    except:
        return 0


def load_data():
    h = pd.read_csv('data/2022-fangraphs-proj-h.csv')
    h['sorter'] = h['HR']+h['R']+h['RBI']+h['H']+h['SB']
    
    p = pd.read_csv('data/2022-fangraphs-proj-p.csv')
    val_h = pd.read_csv('data/2022-fangraphs-auction-calculator-h.csv')
    val_h.rename(columns={'PlayerId':'playerid', 'POS':'Pos'},inplace=True)
    val_p = pd.read_csv('data/2022-fangraphs-auction-calculator-p.csv')
    val_p.rename(columns={'PlayerId':'playerid', 'POS':'Pos'},inplace=True)
    
    h = h.merge(val_h[['playerid', 'Pos', 'Dollars']])
    h.drop(columns=['wOBA', 'CS', 'Fld', 'BsR', 'ADP'],inplace=True)
    h['Pos'] = h['Pos'].apply(lambda x: ', '.join(x.split('/')))
    h.sort_values('sorter', ascending=False, inplace=True)
    h.reset_index(drop=True)
    
    p = p.merge(val_p[['playerid', 'Pos', 'Dollars']])
    p.drop(columns=['ADP'],inplace=True)
    p['Sv+Hld'] = p['SV']+p['HLD']
    p['Pos'] = p['Pos'].apply(lambda x: ', '.join(x.split('/')))
    p['sorter'] = p['SO']+(p['Sv+Hld']*4)+p['W']
    p.sort_values('sorter', ascending=False, inplace=True)
    p.reset_index(drop=True)
    return h, p

def calc_z(x, stat):
    z = (x - drafted[stat].mean()) / drafted[stat].std()
    return z

def find_primary_pos(p):
    pos_list = p.split(', ')
    pos_hierarchy = ['C', '2B', '1B', 'OF', '3B', 'SS', 'DH', 'SP', 'RP', 'P']
    for i in pos_hierarchy:
        if i in pos_list:
            return i


def check_roster_pos(roster, name, team_name, pos, eligible):
    eligible_at = eligible.split('/')
    eligibility = []
    for p in eligible.split('/'):
        if p=='C':
            eligibility.extend(['C'])
        if p=='1B':
            eligibility.extend(['1B', 'CI'])
        if p=='2B':
            eligibility.extend(['2B', 'MI'])
        if p=='3B':
            eligibility.extend(['3B', 'CI'])
        if p=='SS':
            eligibility.extend(['SS', 'MI'])
        if p=='OF':
            eligibility.extend(['OF1', 'OF2', 'OF3', 'OF4', 'OF5'])
        if p in ['SP', 'RP']:
            eligibility.extend(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'])
        
    eligibility = list(dict.fromkeys(eligibility))
    if 'SP' in eligible_at or 'RP' in eligible_at: 
        pos_list = eligibility
    else:
        pos_list = eligibility+['DH1', 'DH2']
    for p in pos_list:
        if roster.loc[p, team_name]==0:
            roster.loc[p, team_name] = name
            return p
    
    return pos_list

router = APIRouter(prefix='/fantasy', responses={404: {"description": "Not found"}})

@router.get("/draft")
async def draft_view(request: Request):
    h = pd.read_sql('players', engine)
    h['Paid'].fillna(0,inplace=True)
    h['Paid'] = h['Paid'].apply(lambda x: int(x) if x>0 else x)
    for i in ['z', 'Dollars', 'Value', 'IP']:
        h[i] = round(h[i],1)
    h['BA'] = round(h['BA'],3)
    for i in ['ERA', 'WHIP']:
        h[i] = round(h[i],2)
    for i in ['SO', 'W', 'Sv+Hld', 'R', 'RBI', 'SB', 'HR']:
        h[i].fillna(0,inplace=True)
        h[i] = h[i].astype(int)
    owners_df = h.query('Paid>0').groupby('Owner').agg({'Name':'count', 'Paid':'sum', 'z':'sum', 'H':'sum', 'AB':'sum', 'HR':'sum', 'R':'sum', 'RBI':'sum', 'SB':'sum', 'Outs':'sum', 'W':'sum', 'SO':'sum', 'Sv+Hld':'sum', 'ER':'sum', 'IP':'sum', 'BB':'sum', 'HA':'sum'}).reset_index()
    owners_df.rename(columns={'Name':'Drafted'},inplace=True)
    owners_df['Paid'] = owners_df['Paid'].apply(lambda x: int(x) if x>0 else x)
    owners_df['$/unit'] = round(owners_df['Paid']/owners_df['z'],1)
    owners_df['z'] = round(owners_df['z'],1)
    owners_df['$ Left'] = tm_dollars - owners_df['Paid']
    owners_df['$ Left / Plyr'] = round(owners_df['$ Left'] / (tm_players -owners_df['Drafted']),1)
    owners_df['Cash'] = round(owners_df['$ Left / Plyr'] / (((tot_dollars - owners_df.Paid.sum()) + owners_df['Paid']) / ((tot_players - owners_df.Drafted.sum()) + owners_df['Drafted'])),2)
    owners_df['Value'] = round((owners_df['z']*orig_conv) - owners_df['Paid'],1)
    owners_df['BA'] = round(owners_df['H']/owners_df['AB'],3)
    owners_df['ERA'] = round(owners_df['ER']/(owners_df['Outs']/3)*9,2)
    owners_df['WHIP'] = round((owners_df['BB']+owners_df['HA'])/(owners_df['Outs']/3),2)
    owners_df['Pts'] = 0
    for i in ['BA', 'HR', 'R', 'RBI', 'SB', 'ERA', 'WHIP', 'W', 'SO', 'Sv+Hld']:
        owners_df['Pts'] += owners_df[i].rank()
    owners_df['Rank'] = owners_df['Pts'].rank()
    roster = pd.DataFrame(index=['C', '1B', '2B', '3B', 'SS', 'MI', 'CI', 'OF1', 'OF2', 'OF3', 'OF4', 'OF5', 'DH1', 'DH2', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'], data=np.zeros((23,n_teams)), columns=owner_list)
    for tm in owners_df.Owner.tolist():
        for i, row in h[h['Owner']==tm][['Name', 'Owner', 'Primary_Pos', 'Pos', 'Paid', 'Timestamp']].sort_values("Timestamp").iterrows():
            if row['Paid']==0:
                pass
            else:
                check_roster_pos(roster, h.loc[i]['Name'], h.loc[i]['Owner'], h.loc[i]['Primary_Pos'], h.loc[i]['Pos'])
    dollars_rem = (tot_dollars - owners_df['Paid'].sum())
    z_rem = (h[h['z']>0]['z'].sum() - owners_df['z'].sum())
    conv_factor = dollars_rem / z_rem
    h['curValue'] = round(h['z']*conv_factor,1)
    #h['next_in_tier'] = h.apply(lambda x: next_closest_in_tier(h, x['Primary_Pos'], x['playerid']),axis=1)
    return templates.TemplateResponse('draft.html', {'request':request, 'players':h.sort_values('z', ascending=False), 
                                    'owned':h[h['Owner'].notna()], 'owners_df':owners_df, 'roster':roster, 
                                    'owners_json':owners_df.to_json(orient='index'), 
                                    'json':h.sort_values('z', ascending=False).to_json(orient='records'),
                                    'players_left':(tot_players - owners_df.Drafted.sum()),
                                    'dollars_left':(tot_dollars - owners_df.Paid.sum()),
                                    'init_dollars_per_z':round((tot_dollars/h[h['z']>=0]['z'].sum()*player_split),2),
                                    'current_dollars_per_z':round(owners_df.Paid.sum() / owners_df.z.sum(),2)})

@router.get("/draft/update_bid")
async def update_db(playerid: str, price: int, owner: str):
    conn = engine.connect()
    meta.create_all(engine)
    conn.execute(players.update().values(Paid=price, Owner=owner, Timestamp=datetime.now()).where(players.c.playerid==playerid))
    conn.close()
    return RedirectResponse('/fantasy/draft') #{'playerid':playerid, 'price':price, 'owner':owner}

@router.get("/draft/sims/{playerid}")
async def sim_players(playerid: str):
    h = pd.read_sql('players', engine)
    if h[h['playerid']==playerid]['Owner'].any():
        return '<br>sims unavailable for owned players'
    else:
        if h[h['playerid']==playerid]['Primary_Pos'].iloc[0] in ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH']:
            sims = add_distance_metrics(h, playerid, ['BA', 'R', 'RBI', 'HR', 'SB']).sort_values('eucl_dist')
        else:
            sims = add_distance_metrics(h, playerid, ['ERA', 'WHIP', 'W', 'SO', 'Sv+Hld']).sort_values('eucl_dist')
        sims_data = h[h['playerid'].isin(sims['Name'].index)][['Name', 'Value']]
        #print('<br>'.join(sims_data))
        return sims_data.to_json(orient='records')#'<br>'.join(sims_data['Name'])

@router.get('/draft/reset_all')
async def reset_all():
    t = text("UPDATE players SET Paid=NULL, Owner=NULL")
    conn = engine.connect()
    conn.execute(t)
    return RedirectResponse('/fantasy/draft')