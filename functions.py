### List of helper functions
import pandas as pd
import numpy as np

def add_rate_stats(z):
    z.loc[z['AB']==0, ['BA', 'SLG']] = [0, 0]
    z.loc[z['AB']>0, 'BA'] = round(z.loc[z['AB']>0,'H']/z.loc[z['AB']>0,'AB'],3)
    z.loc[z['AB']>0, 'SLG'] = round(z.loc[z['AB']>0,'TB']/z.loc[z['AB']>0,'AB'],3)
    z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])==0, 'OBP'] = 0
    z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0, 'OBP'] = round((z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0,'H']+z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0,'BB']+z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0,'HBP'])/(z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0,'AB']+z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0,'BB']+z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0,'HBP']+z.loc[(z['AB']+z['BB']+z['HBP']+z['SF'])>0,'SF']),3)
    z['OPS'] = round(z['SLG'] + z['OBP'],3)
    return z

def add_runs_created(z):
    z['RC'] = round(((((2.4*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF']))+(z['H']+z['BB']-z['CS']+z['HBP']))*((3*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF']))+((1.25*(z['H']-z['double']-z['triple']-z['HR']))+(1.69*z['double'])+(3.02*z['triple'])+(3.73*z['HR'])+(.29*(z['BB']+z['HBP']))+(.492*(z['SH']+z['SF']+z['SB']))-(.4*z['K']))))/(9*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF'])))-(.9*(z['AB']+z['BB']+z['HBP']+z['SH']+z['SF'])),2)
    return z

def add_lg_woba(z):
    z['wOBA'] = round(((0.691*z['BB']) + (0.722*z['HBP']) + (0.884*z['single']) + (1.257*z['double']) + (1.593*z['triple']) + (2.058*z['HR'])) / (z['AB'] + z['BB'] + z['HBP'] + z['SF']),3)
    return z

def make_lg_avg(z):
    stats = ['GP', 'PA', 'AB', 'R', 'H', 'single', 'double', 'triple', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']
    #lgR = z.groupby(['Org', 'League', 'Year'])['R'].sum().reset_index(name='lgR')['lgR']
    #lgPA = z.groupby(['Org', 'League', 'Year'])['PA'].sum().reset_index(name='lgPA')['lgPA']
    z = z.groupby(['Org', 'League', 'Year'])[stats].mean().reset_index()
    #z = z.groupby(['Org', 'League', 'Year']).agg({'GP':'mean', 'PA':'mean', 'AB':'mean', 'R':'mean', 'H':'mean', 'single':'mean', 'double':'mean', 'triple':'mean', 'HR':'mean', 'RBI':'mean', 'BB':'mean', 'K':'mean', 'HBP':'mean', 'SB':'mean', 'CS':'mean', 'SF':'mean', 'SH':'mean', 'TB':'mean'}).reset_index()
    z['lgR'] = z.groupby(['Org', 'League', 'Year'])['R'].sum().reset_index(name='lgR')['lgR']
    z['lgPA'] = z.groupby(['Org', 'League', 'Year'])['PA'].sum().reset_index(name='lgPA')['lgPA']
    #z = z.merge(lgR, on=[['Org', 'League', 'Year']], how='inner')
    for i in stats:
        z[i] = round(z[i],1)
    add_rate_stats(z)
    add_woba(z)
    z['wOBAscale'] = z['OBP']/z['wOBA']
    return z

def add_ops_plus(z, avg):
    #(OBP / lgOBP + SLG / lgSLG - 1) * 100
    z = z.merge(avg[['Org', 'League', 'Year', 'lgR', 'lgPA', 'BA', 'OBP', 'SLG', 'OPS', 'wOBA', 'wOBAscale']], on=['Org', 'League', 'Year'], suffixes=['', '_lg'], how='inner')
    z['OPS+'] = round((z['OBP']/z['OBP_lg'] + z['SLG']/z['SLG_lg'] -1)*100,0)
    return z

def add_woba(z):
    #(0.691×uBB + 0.722×HBP + 0.884×1B + 1.257×2B + 1.593×3B + 2.058×HR) / (AB + BB – IBB + SF + HBP)
    z['wOBA'] = round(((0.691*z['BB']) + (0.722*z['HBP']) + (0.884*z['single']) + (1.257*z['double']) + (1.593*z['triple']) + (2.058*z['HR'])) / (z['AB'] + z['BB'] + z['HBP'] + z['SF']),3)
    return z

def add_wRAA(z):
    #wRAA formula = ((wOBA-lgwOBA)/wOBAScale)*PA;
    #z = z.merge(avg[['Org', 'League', 'Year', 'wOBA', 'wOBAscale']], on=['Org', 'League', 'Year'], suffixes=['', '_lg'], how='outer')
    z['wRAAc'] = round(((z['wOBA'] - z['wOBA_lg']) / z['wOBAscale'])*z['PA'],2)
    z.fillna({'wRAAc':0},inplace=True)
    return z

def add_wRC(z):
    #wRC = (((wOBA-League wOBA)/wOBA Scale)+(League R/PA))*PA
    #z = z.merge(avg[['Org', 'League', 'Year', 'wOBA']], on=['Org', 'League', 'Year'], suffixes=['', '_lg'], how='outer')
    z['wRC'] = round((((z['wOBA'] - z['wOBA_lg']) / z['wOBAscale']) + (z['lgR'] / z['lgPA'])) * z['PA'],1)
    return z

def add_wRC_plus(z):
    #wRC+ = (((wRAA/PA + League R/PA) + (League R/PA – Park Factor* League R/PA))/ (AL or NL wRC/PA excluding pitchers))*100
    z['wRC+'] = round(((z['wRAAc']/z['PA'] + z['lgR']/z['lgPA'])  / (z['lgR']/z['lgPA'])) * 100, 0)
    return z

def add_team_totals(z):
    dict = {'PID':0, 'First':'Team', 'Last': 'Totals'}
    from data_init import common_stat_list
    for i in common_stat_list:
        dict.update({i: round(z[i].sum(),1)})
    dict.update({'BA':round(z['H'].sum()/z['AB'].sum(),3)})
    dict.update({'OBP':round((z['H'].sum()+z['BB'].sum()+z['HBP'].sum())/(z['AB'].sum()+z['BB'].sum()+z['HBP'].sum()+z['SF'].sum()),3)})
    dict.update({'SLG':round(z['TB'].sum()/z['AB'].sum(),3)})
    dict.update({'OPS':round((z['H'].sum()+z['BB'].sum()+z['HBP'].sum())/(z['AB'].sum()+z['BB'].sum()+z['HBP'].sum()+z['SF'].sum())+(z['TB'].sum()/z['AB'].sum()), 3)})
    dict.update({'wRAAc':round(z['wRAAc'].sum(), 1)})
    dict.update({'wRC':round(z['wRC'].sum(), 1)})
    dict.update({'WAR':round(z['WAR'].sum(), 2)})
    d = pd.DataFrame(dict, index=[0])
    z = pd.concat([z, d])
    return z

def calc_hitting_war(df, st, org, lg, yr):
    mask = (df['Org']==org) & (df['League']==lg) & (df['Year']==yr)
    st_mask = (st['Org']==org) & (st['League']==lg) & (st['Year']==yr)
    #num_teams = st[st_mask].Team.nunique()
    num_games = st[st_mask][['W', 'L', 'T']].sum().sum()
    if num_games == 0:
        num_games = df[mask]['GP'].max()

    wins_avail = num_games/2
    repl_wins = .297*wins_avail
    pos_wins_avail = (wins_avail - repl_wins) * (4/7)
    df.loc[mask, 'replacement_runs'] = pos_wins_avail * df[mask].R.sum() / wins_avail * df[mask]['PA'] / df[mask]['PA'].sum()
    df.loc[mask, 'WAR'] = round((df[mask]['wRAAc']+df[mask]['replacement_runs']) / (df[mask].R.sum() / wins_avail),2)
    return 



