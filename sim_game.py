import random
from dataclasses import dataclass
import pandas as pd
import pickle
import plotly.graph_objects as go
from typing import List, Dict

@dataclass
class PlayerStats:
    name: str
    pa: int
    singles: int
    doubles: int
    triples: int
    hr: int
    bb: int
    hbp: int
    so: int
    
    @property
    def hits(self) -> int:
        return self.singles + self.doubles + self.triples + self.hr

    @property
    def extra_base_probs(self) -> Dict[str, float]:
        """Calculate probability of extra base hits relative to all hits"""
        return {
            'double_rate': self.doubles / self.hits if self.hits > 0 else 0,
            'triple_rate': self.triples / self.hits if self.hits > 0 else 0,
            'hr_rate': self.hr / self.hits if self.hits > 0 else 0
        }
    
    def get_outcome_probabilities(self) -> Dict[str, float]:
        return {
            'hit': self.hits / self.pa,
            'bb': self.bb / self.pa,
            'hbp': self.hbp / self.pa,
            'so': self.so / self.pa,
            'out': (self.pa - self.hits - self.bb - self.hbp - self.so) / self.pa
        }

@dataclass
class PitcherStats:
    name: str
    batters_faced: int
    hits_allowed: int
    bb_allowed: int
    hbp_allowed: int
    so_achieved: int
    
    def get_outcome_probabilities(self) -> Dict[str, float]:
        return {
            'hit': self.hits_allowed / self.batters_faced,
            'bb': self.bb_allowed / self.batters_faced,
            'hbp': self.hbp_allowed / self.batters_faced,
            'so': self.so_achieved / self.batters_faced,
            'out': (self.batters_faced - self.hits_allowed - self.bb_allowed - 
                   self.hbp_allowed - self.so_achieved) / self.batters_faced
        }
    

class BaseballGame:
    def __init__(self, home_lineup: List[PlayerStats], away_lineup: List[PlayerStats],
                 home_pitcher: PitcherStats, away_pitcher: PitcherStats, innings: int = 9):
        self.home_lineup = home_lineup
        self.away_lineup = away_lineup
        self.home_pitcher = home_pitcher
        self.away_pitcher = away_pitcher
        self.innings = innings
        self.current_pitcher = None
        self.reset_game()
        self.box_score = {"home_runs":[], "away_runs":[], "home_hits":0, "away_hits":0, "home_errors":0, "away_errors":0}
    
    def reset_game(self):
        self.inning = 1
        self.top_of_inning = True
        self.outs = 0
        self.runs_in_inning = 0
        self.bases = [False, False, False]
        self.home_score = 0
        self.away_score = 0
        self.home_batter_idx = 0
        self.away_batter_idx = 0
        self.play_by_play = []
        self.state_log = []
        self.current_pitcher = self.home_pitcher if not self.top_of_inning else self.away_pitcher
    
    def combine_probabilities(self, batter: PlayerStats, pitcher: PitcherStats) -> Dict[str, float]:
        batter_probs = batter.get_outcome_probabilities()
        pitcher_probs = pitcher.get_outcome_probabilities()
        
        # Combine probabilities using geometric mean
        combined_probs = {}
        for outcome in batter_probs:
            combined_probs[outcome] = (batter_probs[outcome] * pitcher_probs[outcome]) ** 0.5
        
        # Normalize probabilities
        total = sum(combined_probs.values())
        return {k: v/total for k, v in combined_probs.items()}
    
        
    def handle_hit(self, bases_advanced: int) -> int:
        runs = 0
        bases_copy = self.bases.copy()
        
        # Define advancement probabilities
        extra_base_prob = {
            1: 0.45,  # Probability of taking extra base on single
            2: 0.35   # Probability of taking extra base on double
        }
        
        # Handle each baserunner from third to first
        for i in range(2, -1, -1):
            if bases_copy[i]:
                min_advance = min(bases_advanced, 3-i)  # Minimum bases to advance
                max_advance = min(min_advance + 1, 3-i) # Maximum possible advance
                
                # If extra base is possible and hit isn't triple/HR
                if max_advance > min_advance and bases_advanced in extra_base_prob:
                    # Random chance for extra base
                    actual_advance = max_advance if random.random() < extra_base_prob[bases_advanced] else min_advance
                else:
                    actual_advance = min_advance
                
                # Score run or advance runner
                if i + actual_advance >= 3:
                    runs += 1
                    self.bases[i] = False
                else:
                    self.bases[i] = False
                    self.bases[i + actual_advance] = True
        
        # Place batter on appropriate base
        self.bases[bases_advanced - 1] = True
        return runs
    
    def handle_homerun(self) -> int:
        runs = 1
        for i in range(3):
            if self.bases[i]:
                runs += 1
                self.bases[i] = False
        return runs
    
    def handle_walk(self) -> int:
        runs = 0
        if all(self.bases):
            runs = 1
            return runs
        
        for i in range(2, -1, -1):
            if i == 0:
                self.bases[i] = True
            elif self.bases[i-1]:
                self.bases[i] = True
        return runs

    def get_current_pitcher(self) -> PitcherStats:
        """Returns the current pitcher based on inning half"""
        return self.home_pitcher if self.top_of_inning else self.away_pitcher
        
    def simulate_half_inning(self) -> List[str]:
        plays = []
        self.outs = 0
        self.bases = [False, False, False]
        self.hits_in_inning = 0
        self.runs_in_inning = 0
        # Update current pitcher at the start of the half inning
        self.current_pitcher = self.get_current_pitcher()
        #current_pitcher = self.away_pitcher if not self.top_of_inning else self.home_pitcher
        self.state_log.append({
                'inning':self.inning, 'half':self.top_of_inning, 'score':self.home_score-self.away_score, 'outs':0, 'base_state':[False, False, False].copy(), 'batter':None, 'pitcher':self.current_pitcher.name, 'outcome':None, 'win_exp':.5}
            )
        
        while self.outs < 3:
            if not self.top_of_inning and self.inning >= self.innings and self.home_score > self.away_score:
                break

            current_lineup = self.home_lineup if not self.top_of_inning else self.away_lineup
            current_idx = self.home_batter_idx if not self.top_of_inning else self.away_batter_idx
            
            # Simulate at bat to get result
            result = self.simulate_at_bat(current_lineup[current_idx], self.current_pitcher)
            
            plays.append(result)
            
            if not self.top_of_inning and self.inning >= self.innings and self.home_score > self.away_score:
                break
            
            if not self.top_of_inning:
                self.home_batter_idx = (self.home_batter_idx + 1) % len(self.home_lineup)
            else:
                self.away_batter_idx = (self.away_batter_idx + 1) % len(self.away_lineup)

        # Update box_score
        if self.top_of_inning:
            self.box_score['away_hits'] += self.hits_in_inning
            self.box_score['away_runs'].append(self.runs_in_inning)
        else:
            self.box_score['home_hits'] += self.hits_in_inning
            self.box_score['home_runs'].append(self.runs_in_inning)
            
        # Add inning summary to plays list
        plays.append(f"{self.runs_in_inning} {'run' if self.runs_in_inning == 1 else 'runs'}, {self.hits_in_inning} {'hit' if self.hits_in_inning == 1 else 'hits'}")
        return plays
        
    
    def simulate_at_bat(self, batter: PlayerStats, pitcher: PitcherStats) -> str:
        probs = self.combine_probabilities(batter, pitcher)
        outcome = random.choices(
            list(probs.keys()),
            weights=list(probs.values())
        )[0]
        
        runs = 0
        if outcome == 'hit':
            self.hits_in_inning += 1
            # Determine hit type based on batter's rates
            hit_probs = batter.extra_base_probs
            rand = random.random()
            if rand < hit_probs['hr_rate']:
                runs = self.handle_homerun()
                hit_type = 'HR'
            elif rand < hit_probs['hr_rate'] + hit_probs['triple_rate']:
                runs = self.handle_hit(3)
                hit_type = '3B'
            elif rand < hit_probs['hr_rate'] + hit_probs['triple_rate'] + hit_probs['double_rate']:
                runs = self.handle_hit(2)
                hit_type = '2B'
            else:
                runs = self.handle_hit(1)
                hit_type = '1B'
            outcome = hit_type
        elif outcome == 'bb' or outcome == 'hbp':
            runs = self.handle_walk()
        elif outcome == 'so' or outcome == 'out':
            self.outs += 1
            
        if self.top_of_inning:
            self.away_score += runs
        else:
            self.home_score += runs

        self.runs_in_inning += runs
        self.recent_outcome = outcome
        
        temp_state = {
            'inning': self.inning,
            'half': self.top_of_inning,
            'score': self.home_score - self.away_score,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'outs': self.outs,
            'base_state': self.bases.copy(),
            'batter': batter.name,
            'pitcher': pitcher.name,
            'outcome': outcome,
        }
        print(temp_state)
        if hasattr(self, 'lookup_win_exp'):
            temp_state['win_exp'] = self.lookup_win_exp(temp_state)
            temp_state['wpa'] = temp_state['win_exp'] - self.state_log[-1]['win_exp']
        self.state_log.append(temp_state)
        
        return f"{batter.name} vs {pitcher.name}: {outcome}" + (f" ({runs} runs score)" if runs > 0 else "")

    def simulate_game(self) -> List[str]:
        game_log = []
        
        while True:
            # Top of inning
            game_log.append(f"\nTop {self.inning}")
            plays = self.simulate_half_inning()
            game_log.extend(plays)
            
            # Check if we need to play bottom half
            if self.inning >= self.innings and self.home_score > self.away_score:
                game_log.append(f"\nHome team wins - Bottom {self.inning} not needed!")
                break
            
            # Bottom of inning
            self.top_of_inning = False
            game_log.append(f"\nBottom {self.inning}")
            plays = self.simulate_half_inning()
            game_log.extend(plays)
            
            # Check if game is complete
            if self.inning >= self.innings:
                if self.home_score != self.away_score:
                    break
                
            self.inning += 1
            self.top_of_inning = True
            
            # Don't start a new inning if we've completed regulation and someone is winning
            if self.inning > self.innings and self.home_score != self.away_score:
                break
        
        game_log.append(f"\nFinal Score: Away {self.away_score} - Home {self.home_score}")
        if self.home_score > self.away_score:
            game_log.append("Home team wins!")
        else:
            game_log.append("Away team wins!")
        return game_log

    
    def game_over(self) -> bool:
        # Game is finally over when True is returned
        if self.inning < self.innings: # Return False if current inning less than game length
            return False
        if self.inning > self.innings: # Return False if current inning greater than game length but score is tied
            return self.home_score != self.away_score
        # 9th inning checks
        if self.top_of_inning:
            return False
        return self.home_score > self.away_score

    def convert_base_state(self, x: list) -> int:
        if x == [False, False, False]:
            return 1
        if x == [True, False, False]:
            return 2
        if x == [False, True, False]:
            return 3
        if x == [True, True, False]:
            return 4
        if x == [False, False, True]:
            return 5
        if x == [False, True, True]:
            return 6
        if x == [True, True, True]:
            return 7
        else:
            return 8

    def lookup_win_exp(self, sit: dict) -> float:
        inn = sit['inning']
        half = sit['half']
        outs = sit['outs']
        base_sit = sit['base_state']
        score = sit['score']
        
        if outs == 3: # need to convert to next inning    
            outs = 0 # set outs to 0 no matter what
            base_sit = [False, False, False]
            if half == False: # if bottom half of inning, increment the inning and change half to top
                inn += 1
                half = True
            else:
                half = True
                
        # Convert base_state using your function
        base_sit = self.convert_base_state(base_sit)
        
        # Treat all extra innings as the 9th
        if inn > self.innings:
            inn = self.innings
        if score > 15:
            score = 15
        elif score < -15:
            score = -15
        
        # Look up the state tuple in the precomputed dictionary
        state_key = (inn + 2, half, outs, base_sit)
        #print(state_key)
        we_dict = self.load_we_dict()
        we_row = we_dict.get(state_key)
        
        # Retrieve the win expectancy value for the given score
        if we_row:
            if self.game_over():
                if score > 0:
                    win_expectancy = 1
                else:
                    win_expectancy = 0
            else:
                win_expectancy = we_row.get(score)
        else:
            print('lookup_win_exp failure')
            win_expectancy = -99  # Handle cases where the key doesn't exist
        return win_expectancy

    
    def load_we_dict(self):
        # Load the dictionary from the file
        with open("./static/win_expectancy_table.pkl", "rb") as f:
            we_dict = pickle.load(f)
        return we_dict


    def results(self):
        result = pd.DataFrame(self.state_log)
        result = result[result['outcome'].notna()]
        result['hit'] = result.outcome.apply(lambda x: 1 if x in ['1B', '2B', '3B', 'HR'] else 0)
        result['at_bat'] = result.outcome.apply(lambda x: 1 if x in ['BB', 'HBP'] else 0)
        self.result_df = result
        return result
    
    def _box_score_helper(self, x):
        # Initialize an empty dictionary
        value_count_dict = {}
        
        # Count occurrences of each value
        for value in x:
            if value_count_dict.get(value):
                value_count_dict[value] += 1
            else:
                value_count_dict[value] = 1
        
        # Print the dictionary
        #print(value_count_dict)
        return pd.Series(value_count_dict)

    def create_box_score(self):
        r = self.result_df.groupby('batter').agg({'outcome':list}).apply(lambda x: self._box_score_helper(x['outcome']), axis=1)
        pa = self.result_df.groupby('batter')['batter'].count()
        r['pa'] = pa
        for o in ['1B', '2B', '3B', 'HR', 'bb', 'hbp', 'out', 'so']:
            if o not in r.columns:
                r[o] = 0
        
        r = r.fillna(0).reset_index()
        
        r['H'] = r['1B']+r['2B']+r['3B']+r['HR']
        r['AB'] = r['H'] + r['out'] + r['so']
        r['wpa'] = self.result_df.groupby('batter')['wpa'].sum().reset_index()['wpa']
        self.box_score['stats'] = r[['batter', 'AB', 'H', '2B', '3B', 'HR', 'bb', 'hbp', 'so', 'wpa']].to_dict(orient='records')
        return 

    def plot_win_exp(self):
        result = self.result_df
        inning_indices = result.groupby('inning').apply(lambda x: x.index[0]).to_dict()
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=result.index,
                y=result.win_exp,
                mode='lines+markers',
                marker=dict(color='skyblue'),
                #text=result.index,
                text=result['inning'],
                customdata=result['inning'],
                hovertemplate=
                    "<b>Inning: </b>"+result['inning'].astype(str)+"<br>" + 
                    "<b>Outs: </b>"+result['outs'].astype(str)+"<br>" + 
                    "<b>Score: </b>"+result['home_score'].astype(int).astype(str)+" - " + result['away_score'].astype(int).astype(str) + "<br>" + 
                    "<b>Result</b> of " + result['batter'] + " vs "+result['pitcher'] + ": " + result['outcome'] + "<br>" +
                    "<b>Home team win expectancy: </b>"+round(result['win_exp']*100,1).astype(str)+"%<br>" + 
                    "<extra></extra>",
            )
        )
        
        fig.add_hline(y=0.5, line_dash='dash')

        shade_on = True
        x0 = 1
        for k,v in inning_indices.items():
            fig.add_vline(x=v)
            if shade_on:
                shade_on = False
                fig.add_vrect(x0=x0, x1=v, fillcolor="lightblue", opacity=0.45, line_width=0)
            else:
                shade_on = True
            x0 = v

        fig.update_layout(
            title="Win Expectancy Plot",
            template='plotly_dark',
            height=700,
            #width=1000,
            yaxis_range=[0,1]
        )
        return fig

    def generate_win_probability_data(self):
        win_probs = []
        for state in self.state_log:
            win_prob = self.lookup_win_exp(state)
            win_probs.append({
                'inning': state['inning'],
                'half': state['half'],
                'outs': state['outs'],
                'homeScore': self.home_score,
                'awayScore': self.away_score,
                'winProbability': win_prob,
                'base_state': state['base_state'],
                'batter': state['batter'],
                'pitcher': state['pitcher'],
                'outcome': state['outcome']
            })
        return win_probs