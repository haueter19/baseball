def make_projections(df, pa):
    stats = ['AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']
    df = df.reset_index()

    for i in stats:
        df.loc[df['Year']==2019,i] = df.loc[df['Year']==2019][i] / df.loc[df['Year']==2019]['PA'] * 4
        df.loc[df['Year']==2018,i] = df.loc[df['Year']==2018][i] / df.loc[df['Year']==2018]['PA'] * 3
        df.loc[df['Year']==2017,i] = df.loc[df['Year']==2017][i] / df.loc[df['Year']==2017]['PA'] * 2
        df.loc[df['Year']==2016,i] = df.loc[df['Year']==2016][i] / df.loc[df['Year']==2016]['PA']
    
    df = df.groupby('PID').agg({'PID':'first', 'First':'first', 'Last':'first', 'AB':'sum', 'R':'sum', 'H':'sum', '1B':'sum', '2B':'sum', '3B':'sum', 'HR':'sum', 'RBI':'sum', 'BB':'sum', 'K':'sum', 'HBP':'sum', 'SB':'sum', 'CS':'sum', 'SF':'sum', 'SH':'sum', 'TB':'sum', 'den':'sum'})

    for i in stats:
        df[i] = round(df[i]/df['den']*pa,2)

    df['BA'] = round(df['H']/df['AB'],3)
    df['OBP'] = round((df['H'] + df['BB'] + df['HBP'])/(df['AB'] + df['BB'] + df['HBP'] + df['SF']),3)
    df['SLG'] = round(df['TB']/df['AB'],3)
    df['OPS'] = round(df['OBP'] + df['SLG'],3)
    df['PA'] = pa
    return df