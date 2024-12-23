import pandas as pd
import numpy as np
import functions
import sqlite3

conn = sqlite3.connect('local_baseball.db')

# Load hitting data from csv
#df = pd.read_csv('Master_Hitting.csv', engine='python', encoding='cp1252')#encoding='utf-8
df = pd.read_sql('SELECT * FROM hitting', conn)
# Give each season-row a denominator (used for making projections)
maxYear = df['Year'].max()
for i, yr in enumerate(range(maxYear-3, maxYear+1)):
    df.loc[df['Year']==yr, 'den'] = i+1

common_stat_list = ['GP', 'PA', 'AB', 'R', 'H', 'single', 'double', 'triple', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 
                    'SF', 'SH', 'TB', 'wRAA']
# Fill in missing data with 0. Precursor to changing to int
df.fillna({i:0 for i in common_stat_list+['den', 'League']}, inplace=True)
df.fillna({'Team':'None'},inplace=True) # leave as is, must be a str
# Change to int
for i in ['PID', 'H', 'single', 'double', 'triple', 'K', 'SF', 'SH']:
    df[i] = df[i].astype(int)

# Load pitching data from csv
pit = pd.read_csv('Master_Pitching.csv', engine='python')
pit.fillna(0,inplace=True)
# Change to int
for i in ['R', 'H', 'ER', 'BB', 'K', 'HBP', 'Outs', 'HLD', 'W', 'L', 'Sv']:
    pit[i] = pit[i].astype(int)
# Compute at bats against. This is just an estimate based on IP, H unless pitching AB exists (mostly Rockers from Pacific League)
pit['ABA'] = pit.apply(lambda x: x['Outs']+x['H'] if x['AB'] in [np.nan, 0] else x['AB'], axis=1)
# Compute metrics
pit['BAA'] = pit['H']/pit['ABA']
pit['PAA'] = pit['Outs']+pit['H']+pit['BB']+pit['HBP']
pit['BB_rate'] = pit['BB']/pit['PAA']
pit['HBP_rate'] = pit['HBP']/pit['PAA']
pit['K_rate'] = pit['K']/pit['PAA']
pit['H_rate'] = pit['H']/pit['PAA']

# Compute rate stats for triple slash plus OPS
df = functions.add_rate_stats(df)
df.fillna({'BA':0, 'OBP':0, 'SLG':0, 'OPS':0}, inplace=True)

# Compute advanced hitting stats
df = functions.add_woba(df)
h_lg_avg = functions.make_lg_avg(df)
df = functions.add_ops_plus(df, h_lg_avg)
df = functions.add_wRAA(df)
df = functions.add_wRC(df)
df = functions.add_wRC_plus(df)
df.fillna({'wRC+':0}, inplace=True)
df['wRC+'] = df['wRC+'].astype(int)
# Load in standings data
st = pd.read_csv('standings.csv')


oly = df[['Org', 'League', 'Year']].sort_values('Year').drop_duplicates().reset_index()
for i, row in oly.iterrows():
    functions.calc_hitting_war(df, st, row['Org'], row['League'], row['Year'])
