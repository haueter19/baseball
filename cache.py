# cache.py
from typing import Dict, Any, Optional, List, Union
from database import SessionLocal
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

class DataCache:
    def __init__(self):
        self.df: pd.DataFrame = pd.DataFrame()
        self.pit: pd.DataFrame = pd.DataFrame()
        self.st: pd.DataFrame = pd.DataFrame()
        self.players: pd.DataFrame = pd.DataFrame()
        self._initialized = False

    async def update_cache(self, db: Session) -> None:
        try:
            result = db.execute(text("SELECT p.id, p.DOB, h.*, COALESCE(julianday(h.Year)-julianday(substr(p.DOB,length(p.DOB)-4)),0) Age FROM hitting h INNER JOIN players p On (h.PID=p.PID)"))
            self.df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            result1 = db.execute(text("SELECT p.id, p.DOB, h.*, COALESCE(julianday(h.Year)-julianday(substr(p.DOB,length(p.DOB)-4)),0) Age FROM pitching h INNER JOIN players p On (h.PID=p.PID)"))
            self.pit = pd.DataFrame(result1.fetchall(), columns=result1.keys())
            
            result2 = db.execute(text("SELECT * FROM standings"))
            self.st = pd.DataFrame(result2.fetchall(), columns=result2.keys())

            self._initialized = True
            
            print("Cache updated successfully")
        except Exception as e:
            print(f"Error updating cache: {str(e)}")

    def filter_data(self, 
                   data: pd.DataFrame,
                   org: Optional[Union[str, List[str]]] = None,
                   league: Optional[Union[str, List[str]]] = None,
                   team: Optional[Union[str, List[str]]] = None,
                   year: Optional[Union[int, List[int]]] = None,
                   pid: Optional[Union[int, List[int]]] = None) -> pd.DataFrame:
        """Filter any dataset by common parameters."""
        filtered_data = data.copy()

        if org:
            if isinstance(org, str):
                filtered_data = filtered_data[filtered_data['Org'] == org]
                
            else:
                filtered_data = filtered_data[filtered_data['Org'].isin(org)]
                
        if league:
            if isinstance(league, str):
                filtered_data = filtered_data[filtered_data['League'] == league]
            else:
                filtered_data = filtered_data[filtered_data['League'].isin(league)]
                
        if team:
            if isinstance(team, str):
                filtered_data = filtered_data[filtered_data['Team'] == team]
            else:
                filtered_data = filtered_data[filtered_data['Team'].isin(team)]
                
        if year:
            if isinstance(year, int):
                filtered_data = filtered_data[filtered_data['Year'] == year]
            else:
                filtered_data = filtered_data[filtered_data['Year'].isin(year)]
        
        if pid:
            if isinstance(pid, int):
                filtered_data = filtered_data[filtered_data['PID'] == pid]
            else:
                filtered_data = filtered_data[filtered_data['PID'].isin(pid)]

        return filtered_data

    def get_hitting_data(self,
                        org: Optional[Union[str, List[str]]] = None,
                        league: Optional[Union[str, List[str]]] = None,
                        team: Optional[Union[str, List[str]]] = None,
                        year: Optional[Union[int, List[int]]] = None,
                        pid: Optional[Union[int, List[int]]] = None) -> pd.DataFrame:
        """Get hitting data with optional filters."""
        return self.filter_data(self.df, org, league, team, year, pid)

    def get_pitching_data(self,
                         org: Optional[Union[str, List[str]]] = None,
                         league: Optional[Union[str, List[str]]] = None,
                         team: Optional[Union[str, List[str]]] = None,
                         year: Optional[Union[int, List[int]]] = None,
                         pid: Optional[Union[int, List[int]]] = None) -> pd.DataFrame:
        """Get pitching data with optional filters."""
        return self.filter_data(self.pit, org, league, team, year, pid)

    def get_standings_data(self,
                         org: Optional[Union[str, List[str]]] = None,
                         league: Optional[Union[str, List[str]]] = None,
                         team: Optional[Union[str, List[str]]] = None,
                         year: Optional[Union[int, List[int]]] = None,
                         pid: Optional[Union[int, List[int]]] = None) -> pd.DataFrame:
        """Get standings data with optional filters."""
        return self.filter_data(self.st, org, league, team, year, pid)
    
    def get_player_data(self,
                        org: Optional[Union[str, List[str]]] = None,
                        league: Optional[Union[str, List[str]]] = None,
                        team: Optional[Union[str, List[str]]] = None,
                        year: Optional[Union[int, List[int]]] = None,
                        pid: Optional[Union[int, List[int]]] = None) -> pd.DataFrame:
        """Get players data with optional filters."""
        return self.filter_data(self.players, org, league, team, year, pid)

    def get_unique_values(self, column: str) -> List:
        """Get unique values for a given column across all datasets."""
        unique_values = set()
        
        if column in self.df.columns:
            unique_values.update(self.df[column].unique())
        if column in self.pit.columns:
            unique_values.update(self.pit[column].unique())
        if column in self.st.columns:
            unique_values.update(self.st[column].unique())
            
        return sorted(list(unique_values))

    def get_orgs(self) -> List[str]:
        """Get list of all unique organizations."""
        return self.get_unique_values('Org')

    def get_leagues(self, org: Optional[str] = None) -> List[str]:
        """Get list of all leagues, optionally filtered by org."""
        if org:
            leagues = set()
            for df in [self.df, self.pit, self.st]:
                if 'League' in df.columns:
                    leagues.update(df[df['Org'] == org]['League'].unique())
            return sorted(list(leagues))
        return self.get_unique_values('League')

    def get_teams(self, org: Optional[str] = None, league: Optional[str] = None) -> List[str]:
        """Get list of all teams, optionally filtered by org and/or league."""
        teams = set()
        for df in [self.df, self.pit, self.st]:
            filtered = df.copy()
            if org:
                filtered = filtered[filtered['Org'] == org]
            if league:
                filtered = filtered[filtered['League'] == league]
            if 'Team' in filtered.columns:
                teams.update(filtered['Team'].unique())
        return sorted(list(teams))

    def get_years(self) -> List[int]:
        """Get list of all available years."""
        return sorted(self.get_unique_values('Year'))



# Create a single instance
cache = DataCache()



async def periodic_cache_update(db: Session):
    await cache.update_cache(db)