import math
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

templates = Jinja2Templates(directory="templates")

engine = create_engine('sqlite:///fantasy_data.db', echo=False)

num_teams = 12
num_dollars = 260
player_split = .65
pitcher_split = 1 - player_split
tot_dollars = num_teams * num_dollars

drafted_by_pos = {
    'C':12,
    '1B':12,
    '2B':12,
    '3B':12,
    'SS':12,
    'OF':5*12,
    'MI':12,
    'CI':12,
    'DH':12*2, 
    'P':9
}


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

def process_top_hitters(h):
    # Define two empty dicts
    pos_avg = {}
    pos_std = {}
    # Create Used field and set to False, for tracking which players are considered drafted
    h['Used'] = False
    # For each of these positions, define a mask to isolate the unused players who are eligible at that position
    for position in ['C', '2B', '1B', 'OF', '3B', 'SS']:
        mask = (h['Pos'].str.contains(position)) & (h['Used']==False)
        pos_avg[position], pos_std[position] = {}, {}
        
        # Rate stats first
        # Calculate the BA Z score. Because it is a rate, it takes a different formula: H - (AB * (lgH/lgAB))
        pos_index_list = h[mask].index[:drafted_by_pos[position]]
        h.loc[pos_index_list, 'BA'] = (h[mask]['H'] - (h[mask]['AB'] * (h[mask]['H'].sum()/h[mask]['AB'].sum())))
        
        # For each stat category, fill in the dictionaries with an average and standard deviation using the top N players
        # where N is established by the number of drafted players at that position by the league (eg 1B = 12, OF=60)
        for stat in ['PA', 'AB', 'BA', 'HR', 'RBI', 'R', 'SB']:
            pos_avg[position][stat] = round(h.loc[h[mask].index[:drafted_by_pos[position]], stat].mean(),1)
            pos_std[position][stat] = round(h.loc[h[mask].index[:drafted_by_pos[position]], stat].std(),1)
            # Using the player's stat projection, calculate their Z score among the top players
            for j in h[mask].index[:drafted_by_pos[position]]:
                h.loc[j, 'z'+stat] = (h.loc[j][stat] - pos_avg[position][stat]) / pos_std[position][stat]
        
        # Sum the 5 stat category Z scores
        h.loc[h[mask].index[:drafted_by_pos[position]], 'z'] = h['zR'] + h['zRBI'] + h['zHR'] + h['zBA'] + h['zSB']
        # Make the last player's Z score equal 0, then adjust the rest by that same amount
        if h.loc[h[mask].index[:drafted_by_pos[position]]].sort_values('z')['z'].iloc[0] < 0:
            h.loc[h[mask].index[:drafted_by_pos[position]], 'z'] += abs(h.loc[h[mask].index[:drafted_by_pos[position]]].sort_values('z')['z'].iloc[0])
        else:
            h.loc[h[mask].index[:drafted_by_pos[position]], 'z'] -= h.loc[h[mask].index[:drafted_by_pos[position]]].sort_values('z')['z'].iloc[0]
        # Assign the current position as the player's Primary_Pos
        h.loc[h[mask].index[:drafted_by_pos[position]], 'Primary_Pos'] = position
        #print(position+':\n',h.loc[h[mask].index[:drafted_by_pos[position]]]['Name'].unique())
        # Mark these players as Used so they do not get used in another position
        h.loc[h[mask].index[:drafted_by_pos[position]], 'Used'] = True

    # This is the same process as above except it does it for the MI and CI categories which means you have to find the 
    # top 12 middle/corner infielders available
    for position in ['MI', 'CI']:
        if position == 'MI':
            pos_avg[position], pos_std[position] = {}, {}
            mask = ((h['Pos'].str.contains('SS')) & (h['Used']==False)) | ((h['Pos'].str.contains('2B')) & (h['Used']==False))
            
            pos_index_list = h[mask].index[:drafted_by_pos[position]]
            h.loc[pos_index_list, 'BA'] = (h[mask]['H'] - (h[mask]['AB'] * (h[mask]['H'].sum()/h[mask]['AB'].sum())))
        
            for stat in ['PA', 'AB', 'BA', 'HR', 'RBI', 'R', 'SB']:
                pos_avg[position][stat] = round(h.loc[h[mask].index[:drafted_by_pos[position]], stat].mean(),1)
                pos_std[position][stat] = round(h.loc[h[mask].index[:drafted_by_pos[position]], stat].std(),1)
                for j in h[mask].index[:drafted_by_pos[position]]:
                    h.loc[j, 'z'+stat] = (h.loc[j][stat] - pos_avg[position][stat]) / pos_std[position][stat]

            h.loc[h[mask].index[:drafted_by_pos[position]], 'z'] = h['zR'] + h['zRBI'] + h['zHR'] + h['zBA'] + h['zSB']
            h.loc[h[mask].index[:drafted_by_pos[position]], 'z'] += abs(h.loc[h[mask].index[:drafted_by_pos[position]]].sort_values('z')['z'].iloc[0])
            h.loc[h[mask].index[:drafted_by_pos[position]], 'Primary_Pos'] = position
            #print(position+':\n',h.loc[h[mask].index[:12]]['Name'].unique())
            h.loc[h[mask].index[:drafted_by_pos[position]], 'Used'] = True

        elif position == 'CI':
            pos_avg[position], pos_std[position] = {}, {}
            mask = ((h['Pos'].str.contains('1B')) & (h['Used']==False)) | ((h['Pos'].str.contains('3B')) & (h['Used']==False))
            
            pos_index_list = h[mask].index[:drafted_by_pos[position]]
            h.loc[pos_index_list, 'BA'] = (h[mask]['H'] - (h[mask]['AB'] * (h[mask]['H'].sum()/h[mask]['AB'].sum())))
            
            for stat in ['PA', 'AB', 'BA', 'HR', 'RBI', 'R', 'SB']:
                pos_avg[position][stat] = round(h.loc[h[mask].index[:drafted_by_pos[position]], stat].mean(),1)
                pos_std[position][stat] = round(h.loc[h[mask].index[:drafted_by_pos[position]], stat].std(),1)
                for j in h[mask].index[:drafted_by_pos[position]]:
                    h.loc[j, 'z'+stat] = (h.loc[j][stat] - pos_avg[position][stat]) / pos_std[position][stat]

            h.loc[h[mask].index[:drafted_by_pos[position]], 'z'] = h['zR'] + h['zRBI'] + h['zHR'] + h['zBA'] + h['zSB']
            h.loc[h[mask].index[:drafted_by_pos[position]], 'z'] += abs(h.loc[h[mask].index[:drafted_by_pos[position]]].sort_values('z')['z'].iloc[0])
            h.loc[h[mask].index[:drafted_by_pos[position]], 'Primary_Pos'] = position
            #print(position+':\n',h.loc[h[mask].index[:12]]['Name'].unique())
            h.loc[h[mask].index[:drafted_by_pos[position]], 'Used'] = True

    # Same process again but uses all remaining hitters and takes the top 12. Expect to see the true DHs at the top
    pos_avg['DH'], pos_std['DH'] = {}, {}
    mask = (h['Used']==False)
    
    pos_index_list = h[mask].index[:drafted_by_pos[position]]
    h.loc[pos_index_list, 'BA'] = (h[mask]['H'] - (h[mask]['AB'] * (h[mask]['H'].sum()/h[mask]['AB'].sum())))
        
    for stat in ['PA', 'AB', 'BA', 'HR', 'RBI', 'R', 'SB']:
        pos_avg['DH'][stat] = round(h.loc[h[mask].index[:24], stat].mean(),1)
        pos_std['DH'][stat] = round(h.loc[h[mask].index[:24], stat].std(),1)
        for j in h[mask].index[:24]:
                h.loc[j, 'z'+stat] = (h.loc[j][stat] - pos_avg['DH'][stat]) / pos_std['DH'][stat]

    h.loc[h[mask].index[:24], 'z'] = h['zR'] + h['zRBI'] + h['zHR'] + h['zBA'] + h['zSB']
    h.loc[h[mask].index[:24], 'z'] += abs(h.loc[h[mask].index[:24]].sort_values('z')['z'].iloc[0])
    h.loc[h[mask].index[:24], 'Primary_Pos'] = 'DH'
    #print('DH:\n',h.loc[h[mask].index[:24]]['Name'].unique())
    #print('DH:\n',h.loc[h[mask].index[:24]].index)
    sub_mask = h.loc[h[mask].index[:24]].index
    h.loc[h[mask].index[:24], 'Used'] = True
    
    if len(h[h['Used']==True])!=14*num_teams:
        print('drafted list not right')
    return h, pos_avg, pos_std

def process_rem_hitters(h, pos_avg, pos_std):
    for position in ['C', '2B', '1B', 'OF', '3B', 'SS']:
        mask = (h['Used']==False) & (h['Primary_Pos']==position)
        h.loc[mask, 'BA'] = (h[mask]['H'] - (h[mask]['AB'] * (h[(h['Used']==True) & (h['Primary_Pos']==position)]['H'].sum()/h[(h['Used']==True) & (h['Primary_Pos']==position)]['AB'].sum())))
        for stat in ['PA', 'AB', 'BA', 'HR', 'RBI', 'R', 'SB']:
            h.loc[mask, 'z'+stat] = (h[stat] - pos_avg[position][stat]) / pos_std[position][stat]

    h.loc[h['Used']==False, 'z'] = h['zBA'] + h['zHR'] + h['zRBI'] + h['zR'] + h['zSB']
    return h

router = APIRouter(prefix='/fantasy', responses={404: {"description": "Not found"}})

@router.get("/draft")
async def draft_view(request: Request):
    h = pd.read_sql('hitting', engine)
    owners_df = h.groupby('Owner').agg({'Name':'count', 'Paid':'sum', 'z':'sum', 'H':'sum', 'AB':'sum', 'HR':'sum', 'R':'sum', 'RBI':'sum', 'SB':'sum'}).reset_index()
    owners_df.rename(columns={'Name':'Drafted'},inplace=True)
    owners_df['$/unit'] = round(owners_df['Paid']/owners_df['z'],1)
    owners_df['z'] = round(owners_df['z'],1)
    owners_df['$ Left'] = 260 - owners_df['Paid']
    owners_df['BA'] = round(owners_df['H']/owners_df['AB'],3)
    owners_df['Pts'] = 0
    for i in ['BA', 'HR', 'R', 'RBI', 'SB']:
        owners_df['Pts'] += owners_df[i].rank()
    return templates.TemplateResponse('draft.html', {'request':request, 'hitters':h[h['Owner'].isna()], 'owned':h[h['Owner'].notna()], 'owners_df':owners_df})

@router.get("/draft/update_bid")
async def update_db(playerid: str, price: int, owner: str):
    conn = engine.connect()
    meta = MetaData()
    hitters = Table('hitting', meta,
                Column('playerid', String, primary_key=True),
                Column('Paid', Integer),
                Column('Owner', String(25)),
                Column('Timestamp', DATETIME)
    )
    meta.create_all(engine)
    #qry = "UPDATE hitting SET Paid="+price+", Owner='"+owner+"' WHERE playerid='"+playerid+"'"
    #print(qry)
    #t = text(qry)
    conn.execute(hitters.update().values(Paid=price, Owner=owner, Timestamp=datetime.now()).where(hitters.c.playerid==playerid))
    conn.close()
    return RedirectResponse('/fantasy/draft') #{'playerid':playerid, 'price':price, 'owner':owner}

@router.get('/draft/reset_all')
async def reset_all():
    t = text("UPDATE hitting SET Paid=NULL, Owner=NULL")
    conn = engine.connect()
    conn.execute(t)
    return RedirectResponse('/fantasy/draft')