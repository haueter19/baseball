import numpy as np
import pandas as pd

def at_bat_result(single_rate, double_rate, triple_rate, hr_rate, bb_rate, hbp_rate, k_rate, p_k, p_bb, p_hbp, p_h):
    #chance_to_reach = (hitter_obp+pitcher_obp)/2.
    k_rate = (k_rate+p_k)/2
    bb_rate = (bb_rate+p_bb)/2
    hbp_rate = (hbp_rate+p_hbp)/2
    hit_rate = single_rate+double_rate+triple_rate+hr_rate+.0001
    single_ratio = single_rate/hit_rate
    double_ratio = double_rate/hit_rate
    triple_ratio = triple_rate/hit_rate
    hr_ratio = hr_rate/hit_rate
    hit_rate = (hit_rate+p_h)/2.
    single_rate = single_ratio*hit_rate
    double_rate = double_ratio*hit_rate
    triple_rate = triple_ratio*hit_rate
    hr_rate = hr_ratio*hit_rate
    out_rate = 1-(single_rate+double_rate+triple_rate+hr_rate+bb_rate+hbp_rate+k_rate)
    
    #p=[single_rate, double_rate, triple_rate, hr_rate, bb_rate, hbp_rate, k_rate, out_rate]
    single_rate, double_rate, triple_rate, hr_rate, bb_rate, hbp_rate, k_rate, out_rate = .2, .1, .05, .05, .1, .05, .2, .25
    return np.random.choice(['1B', '2B', '3B', 'HR', 'BB', 'HBP', 'K', 'Out'], p=[single_rate, double_rate, triple_rate, hr_rate, bb_rate, hbp_rate, k_rate, out_rate])

def update_base_state(result, bases, r):
    if result in ['BB', 'HBP']:
        if bases[2] == 1: #runner on 3rd
            r += 1
            bases[2] = 0
        if bases[1] == 1: #runner on 2nd
            bases[2] = 1
        if bases[0] == 1: #runner on 1st
            bases[1] = 1
        bases[0] = 1
    elif result=='1B':
        if bases[2] == 1:
            r += 1
            bases[2] == 0
        if bases[1] == 1:
            if np.random.choice(['no extra base', 'extra base'], p=[.45, .55])=='no extra base':
                bases[2] = 1
                bases[1] = 0
            else:
                bases[2] = 0
                r += 1
                bases[1] = 0
        if bases[0] == 1:
            if np.random.choice(['no extra base', 'extra base'], p=[.75, .25])=='no extra base':
                bases[1] = 1
            else:
                bases[2] = 1
                bases[1] = 0
        bases[0] = 1
    elif result=='2B':
        if bases[2] == 1:
            r += 1
            bases[2] = 0
        if bases[1] == 1:
            r += 1
            bases[1] = 1
        if bases[0] == 1:
            if np.random.choice(['no extra base', 'extra base'], p=[.67, .33])=='no extra base':
                bases[2] = 1
                bases[0] = 0
            else:
                r += 1
                bases[2] = 0
                bases[0] = 0
        bases[1] = 1
    elif result=='3B':
        if bases[2] == 1:
            r += 1
        if bases[1] == 1:
            r += 1
            bases[1] = 0
        if bases[0] == 1:
            r += 1
            bases[0] = 0
        bases[2] = 1
    elif result=='HR':
        if bases[2] == 1:
            r += 1
        if bases[1] == 1:
            r += 1
        if bases[0] == 1:
            r += 1
        r += 1
        bases = [0, 0, 0]
    return bases, r

def sim_game(prj, tp, innings):
    log = {}
    ab_results = [[],[],[],[],[],[],[],[],[],[]]
    ab_results_dict = {}
    outs=0
    inn=1
    half='top'
    r = 0
    bases = [0, 0, 0]
    p = 0
    tto = 1
    game_log = "<b>Inning 1</b><br>"
    while inn<innings+1:
        result = at_bat_result(prj['1B_per_PA'].iloc[p], prj['2B_per_PA'].loc[p], prj['3B_per_PA'].iloc[p], prj['HR_per_PA'].iloc[p], prj['BB_per_PA'].iloc[p], prj['HBP_per_PA'].iloc[p], prj['K_per_PA'].iloc[p], tp['K_rate'].iloc[0], tp['BB_rate'].iloc[0], tp['HBP_rate'].iloc[0], tp['H_rate'].iloc[0])
        game_log += prj['Last'].iloc[p]+': '+result+'<br>'
        ab_results[p-1].append(result)
        if result in ['Out', 'K']:
            outs += 1
            if outs==3:
                outs = 0
                inn += 1
                bases = [0, 0, 0]
                #print('\nInning',inn)
                game_log += '<br><b>Inning '+str(inn)+'</b><br>'
        else:
            updates = update_base_state(result, bases, r)
            bases = updates[0]
            r = updates[1]
        p += 1
        if p==10:
            p = 0
            tto += 1
    #print(r,'runs')
    for i in range(10):
        ab_results_dict[prj.Last.iloc[i]] = ab_results[i]
    ab_results = ab_results_dict
    return r, game_log, ab_results

def run_sim(prj, tp, innings, g):
    tot_runs = 0
    for x in range(g):
        new_runs, game_log, ab_results = sim_game(prj, tp, innings)
        tot_runs += new_runs
        if x==g-1:
            rpg = tot_runs / g
    return rpg, game_log, ab_results