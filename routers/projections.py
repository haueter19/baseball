import numpy as np
import pandas as pd

stats = ['AB', 'R', 'H', 'single', 'double', 'triple', 'HR', 'RBI', 'BB', 'K', 'HBP', 'SB', 'CS', 'SF', 'SH', 'TB']

def make_projections(df, yr, pa):    
    for i in stats:
        df.loc[df['Year']==yr,i] = df.loc[df['Year']==yr][i] / df.loc[df['Year']==yr]['PA'] * 4
        df.loc[df['Year']==yr-1,i] = df.loc[df['Year']==yr-1][i] / df.loc[df['Year']==yr-1]['PA'] * 3
        df.loc[df['Year']==yr-2,i] = df.loc[df['Year']==yr-2][i] / df.loc[df['Year']==yr-2]['PA'] * 2
        df.loc[df['Year']==yr-3,i] = df.loc[df['Year']==yr-3][i] / df.loc[df['Year']==yr-3]['PA']
    
    df = df.groupby('PID').agg({'PID':'first', 'First':'first', 'Last':'first', 'AB':'sum', 'R':'sum', 'H':'sum', 'single':'sum', 'double':'sum', 'triple':'sum', 'HR':'sum', 
                                'RBI':'sum', 'BB':'sum', 'K':'sum', 'HBP':'sum', 'SB':'sum', 'CS':'sum', 'SF':'sum', 'SH':'sum', 'TB':'sum', 'den':'sum'})

    for i in stats:
        df[i] = round(df[i]/df['den']*pa,2)

    df['PA'] = pa
    return df

def project_player_stats(player_data, stats, recent_years=4):
    """
    Project player statistics using weighted recent performance.
    
    Parameters:
    -----------
    player_data : pandas.DataFrame
        DataFrame containing player statistics across years
        Expected columns: 'Year' and all stats in the stats list
    stats : list
        List of statistical categories to project
    recent_years : int, optional (default=4)
        Number of recent years to use for projection
    
    Returns:
    --------
    pandas.Series
        Projected statistics for the player
    """
    # Ensure the data is sorted by year in ascending order
    player_data = player_data.sort_values('Year')
    
    # Get the available years, focusing on the most recent
    years = player_data['Year'].unique()
    
    # If fewer than recent_years are available, adjust the recent years
    available_years = min(len(years), recent_years)
    recent_year_indices = years[-available_years:]
    
    # Create weight vector with exponential decay
    weights = np.linspace(0.5, 1.0, available_years)
    weights /= weights.sum()
    
    # Initialize projection dictionary
    projections = {}
    
    # Project each stat
    for stat in stats:
        # Get stat values for recent years
        recent_data = player_data[player_data['Year'].isin(recent_year_indices)]
        recent_stat_values = recent_data[stat].values
        
        # Handle case with all zero values
        if np.sum(recent_stat_values) == 0:
            projections[stat] = 0
            continue
        
        # Filter out zero values while maintaining corresponding weights
        non_zero_mask = recent_stat_values > 0
        non_zero_values = recent_stat_values[non_zero_mask]
        non_zero_weights = weights[non_zero_mask]
        
        # Normalize weights
        non_zero_weights /= non_zero_weights.sum()
        
        # Calculate weighted average
        projected_stat = np.average(non_zero_values, weights=non_zero_weights)
        
        # Round to appropriate decimal places based on the stat
        if stat in stats:
            projections[stat] = round(max(0, projected_stat))
        else:
            projections[stat] = round(max(0, projected_stat), 3)
    
    return pd.Series(projections)


def calculate_league_averages(league_data, stats, recent_years=4):
    """
    Calculate league average statistics for recent years.
    
    Parameters:
    -----------
    league_data : pandas.DataFrame
        DataFrame containing all players' statistics
    stats : list
        List of statistical categories to analyze
    recent_years : int, optional (default=4)
        Number of recent years to use for league averages
    
    Returns:
    --------
    dict
        Dictionary of league average statistics
    """
    # Sort data by year
    league_data = league_data.sort_values('Year')
    
    # Get recent years
    years = league_data['Year'].unique()
    recent_year_indices = years[-recent_years:]
    
    # Calculate league averages for recent years
    league_averages = {}
    for stat in stats:
        # Filter data for recent years and calculate mean
        recent_stat_values = league_data[league_data['Year'].isin(recent_year_indices)][stat]
        
        # Calculate mean, handling potential zero values
        league_mean = recent_stat_values[recent_stat_values >= 0].mean()
        league_averages[stat] = league_mean
    
    return league_averages


def calculate_dynamic_regression_factor(player_pa, league_stats, min_pa=10, max_pa=200):
    """
    Calculate a dynamic regression factor based on plate appearances.
    
    Parameters:
    -----------
    player_pa : int or float
        Player's plate appearances
    league_stats : dict
        Dictionary containing league statistics about plate appearances
    min_pa : int, optional (default=25)
        Minimum plate appearances considered for low regression
    max_pa : int, optional (default=600)
        Maximum plate appearances considered for high regression
    
    Returns:
    --------
    float
        Dynamic regression factor between 0 and 1
    """
    # Extract league PA statistics
    league_avg_pa = league_stats.get('avg_pa', 20)
    league_max_pa = league_stats.get('max_pa', max_pa)
    
    # Ensure max_pa is at least as large as default
    max_pa = max(max_pa, league_max_pa)
    
    # Clamp player's PA to the defined range
    clamped_pa = max(min(player_pa, max_pa), min_pa)
    
    # Calculate regression factor using a sigmoid-like curve
    # This ensures smooth transition from high regression to low regression
    # Formula creates an S-curve that:
    # - Approaches 1 for very low PA
    # - Approaches 0 for high PA
    regression_factor = 1 - (clamped_pa - min_pa) / (max_pa - min_pa)
    
    # Additional adjustment to make the curve more pronounced
    regression_factor = regression_factor ** 2
    
    return max(0.05, min(0.5, regression_factor))



def project_and_regress_player_stats(
    player_data, 
    league_data, 
    stats, 
    league_stats,
    recent_years=4
):
    """
    Complete workflow for projecting and dynamically regressing player statistics.
    
    Parameters:
    -----------
    player_data : pandas.DataFrame
        DataFrame containing individual player statistics
    league_data : pandas.DataFrame
        DataFrame containing all players' statistics
    stats : list
        List of statistical categories to project
    league_stats : dict
        Dictionary containing league-level statistics
    recent_years : int, optional (default=4)
        Number of recent years to use for projection
    
    Returns:
    --------
    dict
        Final projected and regressed player statistics
    """
    # Step 1: Project player stats
    initial_projections = project_player_stats(player_data, stats, recent_years)
    
    # Step 2: Calculate league averages
    league_averages = calculate_league_averages(league_data, stats, recent_years)
    
    # Calculate dynamic regression factor based on plate appearances
    player_pa = league_stats.get('player_pa', 0)
    regression_factor = calculate_dynamic_regression_factor(
        player_pa, 
        league_stats
    )
    
    # Step 3: Regress projections to league mean
    final_projections = {}
    for stat, proj_value in initial_projections.items():
        league_mean = league_averages.get(stat, proj_value)
        
        # Dynamic regression
        regressed_value = (proj_value * (1 - regression_factor) + 
                           league_mean * regression_factor)
        
        # Rounding logic        
        final_projections[stat] = round(max(0, regressed_value), 3)
    
    return {
        'projections': final_projections,
        'regression_factor': regression_factor
    }



def generate_player_projections(league_data, stats, teams, recent_years=4):
    """
    Generate projections for all players in the league.
    
    Parameters:
    -----------
    league_data : pandas.DataFrame
        DataFrame containing all players' statistics
        Expected columns: 'Player', 'Year', and all stats
    stats : list
        List of statistical categories to project
    recent_years : int, optional (default=4)
        Number of recent years to use for projection
    
    Returns:
    --------
    pandas.DataFrame
        Consolidated projections for all players
    """
    # Prepare to store projections
    all_projections = []
    
    # Calculate league-level statistics
    league_stats = calculate_league_level_stats(league_data)
    
    # Get unique players
    players = league_data[league_data['Team'].isin(teams)]['PID'].unique()
    
    # Iterate through each player
    for player in players:
        # Filter data for this player
        player_data = league_data[league_data['PID'] == player].drop('PID', axis=1)
        
        # Calculate player-specific league stats
        player_league_stats = league_stats.copy()
        player_league_stats['player_pa'] = calculate_player_plate_appearances(player_data)
        
        # Project and regress stats
        try:
            result = project_and_regress_player_stats(
                player_data, 
                league_data, 
                stats, 
                player_league_stats,
                recent_years
            )
            
            # Prepare projection entry
            projection_entry = {
                'PID': player,
                'First':player_data.First.max(),
                'Last':player_data.Last.max(),
                'Team':player_data.Team.max(),
                'Regression_Factor': result['regression_factor']
            }
            projection_entry.update(result['projections'])
            
            all_projections.append(projection_entry)
        
        except Exception as e:
            print(f"Error projecting stats for {player}: {e}")
    
    # Convert to DataFrame
    projections_df = pd.DataFrame(all_projections)
    
    return projections_df



def calculate_league_level_stats(league_data):
    """
    Calculate overall league-level statistics.
    
    Parameters:
    -----------
    league_data : pandas.DataFrame
        DataFrame containing all players' statistics
    
    Returns:
    --------
    dict
        League-level statistical summary
    """
    # Calculate plate appearances
    pa_column = 'PA'  # Assuming At-Bats as proxy for Plate Appearances
    
    league_stats = {
        'avg_pa': league_data.groupby('PID')[pa_column].sum().mean(), #league_data[pa_column][league_data[pa_column] >= 0].mean(),
        'max_pa': league_data.groupby('PID')[pa_column].sum().max(), #league_data[pa_column].max(),
        'min_pa': league_data.groupby('PID')[pa_column].sum().min(), #league_data[pa_column][league_data[pa_column] >= 0].min()
    }
    
    return league_stats



def calculate_player_plate_appearances(player_data, pa_column='PA'):
    """
    Calculate total plate appearances for a player.
    
    Parameters:
    -----------
    player_data : pandas.DataFrame
        DataFrame containing player's statistics
    pa_column : str, optional (default='AB')
        Column to use for plate appearance calculation
    
    Returns:
    --------
    float
        Total plate appearances
    """
    # Sum plate appearances, handling potential zero years
    total_pa = player_data[pa_column][player_data[pa_column] > 0].sum()
    
    return total_pa