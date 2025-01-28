from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import pandas as pd
import re

def parse_condition(condition_str):
    operators = {
        '>=': lambda x, y: x >= y,
        '<=': lambda x, y: x <= y,
        '>': lambda x, y: x > y,
        '<': lambda x, y: x < y,
        '=': lambda x, y: x == y,
        '+': lambda x, y: x >= y
    }
    
    # Handle natural language operators
    condition_str = condition_str.replace('less than', '<').replace('fewer than', '<').replace('at least', '+')
    
    # Updated regex to capture all operators
    match = re.search(
        r'([<>]=?|=|\+)?\s*(\d+)\s*(\+)?\s*((?:three pointers|points|rebounds|assists|steals|blocks))',
        condition_str,
        re.IGNORECASE
    )
    if not match:
        return None, None, None
    
    operator = (match.group(1) or match.group(3) or '+').strip()
    value = int(match.group(2))
    stat = match.group(4).lower()

    # Normalize operator symbols
    operator = {'+': '+', '>': '>', '<': '<', '=': '='}.get(operator, operator)
    
    stat_map = {
        'points': 'PTS',
        'rebounds': 'REB',
        'assists': 'AST',
        'steals': 'STL',
        'blocks': 'BLK',
        'three pointers': 'FG3M'
    }
    
    return operators.get(operator), value, stat_map.get(stat)

def get_player_games(player_id, season='2024-25'):
    game_log = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season,
        season_type_all_star='Regular Season'
    )
    df = game_log.get_data_frames()[0]
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'], format='%b %d, %Y')
    df = df.sort_values('GAME_DATE', ascending=False)
    return df

def find_player_complex(name):
    all_players = players.get_players()
    name = name.lower().strip()
    
    # Nickname handling
    nickname_map = {
        'kd': 'kevin durant',
        'steph': 'stephen curry',
        'lebron': 'leborn james',
        'jokic': 'nikola jokić',
        'luka': 'luka doncic'
    }
    name = nickname_map.get(name, name)
    
    for p in all_players:
        full_name = p['full_name'].lower()
        if (name == full_name or
            name in full_name or
            name == re.sub(r'[\W_]+', '', full_name)):
            return p
    return None

def process_complex_query(query):
    try:
        # Enhanced regex pattern with better operator support
        pattern = r'(?i)\bhow many (home|away)?\s*games\s*(?:in\s+last\s+(\d+)\s*|this\s+season)?.*?has\s+([A-Za-zÀ-ÿ\s-]+?)\s+(?:scored|made|had)\s+(.+)'
        match = re.search(pattern, query)
        
        if not match:
            return "Try: 'How many away games in last 20 has Giannis Antetokounmpo scored 30+ points?'"

        location = match.group(1).lower() if match.group(1) else None
        num_games = int(match.group(2)) if match.group(2) else None
        player_name = match.group(3).strip()
        condition_str = match.group(4).strip()

        # Parse the condition
        operator_func, threshold, stat_column = parse_condition(condition_str)
        if not all([operator_func, threshold, stat_column]):
            return f"Couldn't understand: {condition_str}"

        # Find player
        player = find_player_complex(player_name)
        if not player:
            return f"Player '{player_name}' not found"

        # Get and prepare data
        df = get_player_games(player['id'])
        df['LOCATION'] = df['MATCHUP'].apply(lambda x: 'home' if 'vs.' in x else 'away')

        # Apply filters
        if location:
            df = df[df['LOCATION'] == location]
        if num_games:
            df = df.head(num_games)

        # Apply stat condition
        valid_games = df[operator_func(df[stat_column], threshold)]
        
        return (f"{player['full_name']} has {len(valid_games)} {location + ' ' if location else ''}games "
                f"meeting {condition_str}" + 
                (f" in last {num_games} games" if num_games else " this season"))

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print("🏀 Enhanced NBA Stats Query Tool")
    print("Try these formats:")
    print("- How many away games in last 20 has Giannis Antetokounmpo scored 30+ points")
    print("- How many home games this season has Stephen Curry made <5 three pointers")
    print("- How many games has Luka made >=9 assists")
    
    while True:
        try:
            query = input("\nAsk a question or 'quit': ").strip()
            if query.lower() in ['quit', 'exit']:
                break
                
            response = process_complex_query(query)
            print(f"\n{'-'*40}\n{response}\n{'-'*40}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break