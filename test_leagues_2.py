import soccerdata as sd
import json

def test():
    try:
        fbref = sd.FBref(leagues=["AUS-A-League"], seasons='2526')
        df = fbref.read_player_season_stats(stat_type="standard")
        print("Columns for AUS-A-League standard:", df.columns)
        print("Row count:", len(df))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test()
