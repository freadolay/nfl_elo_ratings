import json
import pyodbc
import warnings
import pandas as pd

class ELOModel:
    def __init__(self) -> None:
        # DB INFO
        with open("src/db_access.json") as f:
            data = json.load(f)
            self.server = data['server']
            self.database = data['database']
            self.username = data['username']
            self.password = data['password']
            self.driver = data['driver']
        
    def query_db(self, sql_query_str:str) -> pd.DataFrame:
        # TODO: Replace this with a SQL Alchemy Connector to remove warnings
        engine = pyodbc.connect('DRIVER='+self.driver+';SERVER='+self.server+';DATABASE='+self.database+';UID='+self.username+';PWD=' + self.password)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = pd.read_sql(sql_query_str, con=engine)
        return df

class FiveThirtyEightElo:
    def __init__(self, home_field_add=55, home_field_dist_add=4, rest_add=25, playoff_mult=1.2) -> None:
        # Get the superclass
        ELOModel.__init__(self)
        self.home_field_add = home_field_add
        self.home_field_dist_add = home_field_dist_add
        self.rest_add = rest_add
        self.playoff_mult = playoff_mult

        
    def elo_adjustment(self, elo_base, is_home_team, travel_dist=0, coming_off_bye=False, is_playoffs=False) -> float:
        """
        travel_dist = distance in miles
        home_field_dist_add = multiplier per 1000 miles
        """
        home_field_addition = is_home_team*self.home_field_add
        home_field_dist_addition = is_home_team*self.home_field_dist_add*travel_dist/1000
        rest_addition = coming_off_bye*self.rest_add
        elo = elo_base + home_field_addition + home_field_dist_addition + rest_addition
        if is_playoffs and is_home_team:
            elo *= self.playoff_mult
        return elo

    
    def get_vegas_line(self, home_team_elo, away_team_elo, denom=25) -> float:
        # Make ELO Adjustments for each team
        # Home Team
        home_team_elo_adj = self.elo_adjustment(
            elo_base=home_team_elo,
            is_home_team=True,
            travel_dist=0,
            coming_off_bye=False,
            is_playoffs=False
        )
        # Away Team
        away_team_elo_adj = self.elo_adjustment(
            elo_base=away_team_elo,
            is_home_team=False,
            travel_dist=0,
            coming_off_bye=False,
            is_playoffs=False
        )

        # Calculate ELO Difference
        elo_diff = home_team_elo_adj - away_team_elo_adj

        # Probability Calc (Doesn't matter for vegas line I guess?)
        coeff=10
        exp_denom=400
        home_team_win_prob = 1 / ( coeff**(-elo_diff/exp_denom) + 1 )

        # Vegas Line Calc
        vegas_line = -elo_diff/denom
        return vegas_line


class JohnElo:
    def __init__(self, coeff=0.075, exp_ratio=(699/999), home_field_add=1.5) -> None:
        ELOModel.__init__(self)
        self.coeff = coeff
        self.exp_ratio = exp_ratio
        self.home_field_add = home_field_add

    def get_vegas_line(self, home_team_elo, away_team_elo) -> float:
        elo_diff = home_team_elo - away_team_elo
        vegas_line = -(self.coeff*(elo_diff)**(self.exp_ratio) + self.home_field_add)
        return vegas_line




    