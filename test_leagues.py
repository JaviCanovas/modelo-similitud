import soccerdata as sd
import json

def test():
    try:
        fbref = sd.FBref(leagues=["AUS-A-League", "BRA-Serie A", "CHI-Primera Division"], seasons='2526')
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test()
