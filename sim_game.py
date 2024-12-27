import random
from dataclasses import dataclass
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
    def __init__(self, innings, home_lineup: List[PlayerStats], away_lineup: List[PlayerStats],
                 home_pitcher: PitcherStats, away_pitcher: PitcherStats):
        self.innings = innings
        self.home_lineup = home_lineup
        self.away_lineup = away_lineup
        self.home_pitcher = home_pitcher
        self.away_pitcher = away_pitcher
        self.reset_game()
    
    def reset_game(self):
        self.inning = 1
        self.top_of_inning = True
        self.outs = 0
        self.bases = [False, False, False]
        self.home_score = 0
        self.away_score = 0
        self.home_batter_idx = 0
        self.away_batter_idx = 0
        self.play_by_play = []
    
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
    
    def simulate_half_inning(self) -> List[str]:
        plays = []
        self.outs = 0
        self.bases = [False, False, False]
        self.runs_in_inning = 0
        
        current_pitcher = self.away_pitcher if not self.top_of_inning else self.home_pitcher
        
        while self.outs < 3:
            current_lineup = self.home_lineup if not self.top_of_inning else self.away_lineup
            current_idx = self.home_batter_idx if not self.top_of_inning else self.away_batter_idx
            
            result = self.simulate_at_bat(current_lineup[current_idx], current_pitcher)
            plays.append(result)
            
            if not self.top_of_inning:
                self.home_batter_idx = (self.home_batter_idx + 1) % len(self.home_lineup)
            else:
                self.away_batter_idx = (self.away_batter_idx + 1) % len(self.away_lineup)
        
        return plays, self.runs_in_inning
    
    def simulate_at_bat(self, batter: PlayerStats, pitcher: PitcherStats) -> str:
        probs = self.combine_probabilities(batter, pitcher)
        outcome = random.choices(
            list(probs.keys()),
            weights=list(probs.values())
        )[0]
        
        runs = 0
        if outcome == 'hit':
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
        
        return f"{batter.name} vs {pitcher.name}: {outcome}" + (f" ({runs} runs score)" if runs > 0 else "")

    def simulate_game(self) -> List[str]:
        game_log = []
        
        while (self.inning <= 9 or self.home_score == self.away_score) and not self.game_over():
            game_log.append(f"\nTop {self.inning}")
            plays = self.simulate_half_inning()[0]
            game_log.extend(plays)
            
            # Only play bottom half if necessary
            if self.inning >= 9 and not self.top_of_inning and self.home_score > self.away_score:
                break
                
            self.top_of_inning = False
            game_log.append(f"\nBottom {self.inning}")
            plays = self.simulate_half_inning()[0]
            game_log.extend(plays)
            
            self.inning += 1
            self.top_of_inning = True
        
        game_log.append(f"\nFinal Score: Away {self.away_score} - Home {self.home_score}")
        return game_log
    
    def game_over(self) -> bool:
        if self.inning < self.innings:
            return False
        if self.inning > self.innings:
            return self.home_score != self.away_score
        # 9th inning checks
        if self.top_of_inning:
            return False
        return self.home_score > self.away_score
