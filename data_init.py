import pandas as pd
import numpy as np
import functions

df = pd.read_csv('Master_Hitting.csv', engine='python', encoding='cp1252')#encoding='utf-8
maxYear = df['Year'].max()
df.loc[df['Year']==maxYear-1, 'den'] = 4
df.loc[df['Year']==maxYear-3, 'den'] = 3
df.loc[df['Year']==maxYear-4, 'den'] = 2
df.loc[df['Year']==maxYear-5, 'den'] = 1
common_stat_list = ['GP', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 
                    'SF', 'SH', 'TB', 'wRAA']

df.Team.fillna('None',inplace=True) # leave as is, must be a str

for i in common_stat_list+['den', 'League']:
    df[i].fillna(0, inplace=True)

for i in ['PID', 'H', '1B', '2B', 'K', 'SF', 'SH']:
    df[i] = df[i].astype(int)

pit = pd.read_csv('Master_Pitching.csv', engine='python')
pit.fillna(0,inplace=True)
for i in ['R', 'H', 'ER', 'BB', 'K', 'HBP', 'Outs', 'HLD', 'W', 'L', 'Sv']:
    pit[i] = pit[i].astype(int)

pit['ABA'] = pit.apply(lambda x: x['Outs']+x['H'] if x['AB'] in [np.nan, 0] else x['AB'], axis=1)
pit['BAA'] = pit['H']/pit['ABA']
pit['PAA'] = pit['Outs']+pit['H']+pit['BB']+pit['HBP']
pit['BB_rate'] = pit['BB']/pit['PAA']
pit['HBP_rate'] = pit['HBP']/pit['PAA']
pit['K_rate'] = pit['K']/pit['PAA']
pit['H_rate'] = pit['H']/pit['PAA']

df = functions.add_rate_stats(df)
df['OBP'].fillna(0, inplace=True)
df['SLG'].fillna(0, inplace=True)
df['OPS'].fillna(0, inplace=True)
df = functions.add_woba(df)
h_lg_avg = functions.make_lg_avg(df)
df = functions.add_ops_plus(df, h_lg_avg)
df = functions.add_wRAA(df, h_lg_avg)
df = functions.add_wRC(df, h_lg_avg)
df = functions.add_wRC_plus(df, h_lg_avg)
df['wRC+'].fillna(0, inplace=True)
df['wRC+'] = df['wRC+'].astype(int)

st = pd.read_csv('standings.csv')

oly = df[['Org', 'League', 'Year']].sort_values('Year').drop_duplicates().reset_index()
for i, row in oly.iterrows():
    functions.calc_hitting_war(df, row['Org'], row['League'], row['Year'])