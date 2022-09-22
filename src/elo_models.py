import json
import pyodbc
import warnings
import pandas as pd
import numpy as np

class ELOModel:
    """
    Base class for the ELO Models defined in this module
    """
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

class FiveThirtyEightElo(ELOModel):
    """
    fivethirtyeight.com's version of NFL Elo Rankings
    """
    def __init__(self,
                 home_field_add=55,
                 home_field_dist_add=4,
                 rest_add=25,
                 playoff_mult=1.2,
                 k=20) -> None:
        """
        README: https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work/
        """
        # Get the superclass
        ELOModel.__init__(self)
        self.home_field_add = home_field_add
        self.home_field_dist_add = home_field_dist_add
        self.rest_add = rest_add
        self.playoff_mult = playoff_mult
        self.k = k
        # Note: this model does not change the autocorrelation correction for margin of victory


    def elo_adjustment(self,
                       elo_base,
                       is_home_team,
                       travel_dist=0,
                       coming_off_bye=False,
                       is_playoffs=False) -> float:
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

    
    def get_vegas_line(self, home_team_elo_adj, away_team_elo_adj, denom=25) -> float:
        """
        Note: It's assumed that all ELO adjustments have already been made
        """

        # Calculate ELO Difference
        elo_diff = home_team_elo_adj - away_team_elo_adj

        # Probability Calc (Doesn't matter for vegas line I guess?)
        coeff=10
        exp_denom=400
        home_team_win_prob = 1 / ( coeff**(-elo_diff/exp_denom) + 1 )

        # Vegas Line Calc
        vegas_line = -elo_diff/denom
        return home_team_win_prob, vegas_line


    def get_post_game_elos(self, elo_h_pregame, elo_a_pregame, h_score, a_score, h_win_prob):
        """
        Takes a certain amount of ELO points from loser and gives to winner
        """
        elo_diff = np.abs(elo_h_pregame-elo_a_pregame)
        point_diff = np.abs(h_score-a_score)
        mov_mult = np.log(point_diff+1) * ( 2.2/(elo_diff*0.001 + 2.2) )  # Margin of Victory Multiplier - remove autocorr.
        if h_score > a_score:
            h_result = 1
        elif h_score < a_score:
            h_result = 0
        else:
            h_result = 0.5  # tie
        elo_change = self.k * (h_result - h_win_prob) * mov_mult
        elo_h_postgame = elo_h_pregame + elo_change
        elo_a_postgame = elo_a_pregame - elo_change
        return elo_h_postgame, elo_a_postgame


    def evaluate_season(self, season):
        """
        Evaluate an entire season with data from DB.. TODO!
        """


class JohnElo(ELOModel):
    """
    John W's version of NFL Elo Rankings
    """
    def __init__(self, coeff=0.075, exp_ratio=(699/999), home_field_add=1.5,margin_pct=0.02, h_a_pct=0.95, elo_adj_exp_ratio=0.25) -> None:
        ELOModel.__init__(self)
        self.coeff = coeff
        self.exp_ratio = exp_ratio
        self.home_field_add = home_field_add
        self.margin_pct = margin_pct  # (Multiplier) How much wins affects elo change
        self.h_a_pct = h_a_pct  # (Multiplier) How much being at home/away affects elo change
        self.elo_adj_exp_ratio = elo_adj_exp_ratio


    def get_vegas_line(self, home_team_elo, away_team_elo) -> float:
        """
        Gets the vegas line (home team) for the ELO Model
        """
        elo_diff = home_team_elo - away_team_elo
        vegas_line = -(self.coeff*(elo_diff)**(self.exp_ratio) + self.home_field_add)
        return vegas_line


    def get_post_game_elos(self, elo_h_pregame, elo_a_pregame, h_score, a_score):
        """
        Takes a certain amount of ELO points from loser and gives to winner
        """
        # Coeff A
        if h_score > a_score:
            coeff_a = self.margin_pct*self.h_a_pct*elo_a_pregame
        else:
            coeff_a = -self.margin_pct*self.h_a_pct*elo_h_pregame

        # Coeff B
        if h_score > a_score:
            if elo_h_pregame > elo_a_pregame:
                coeff_b = 1-(elo_h_pregame-elo_a_pregame)/elo_h_pregame
            elif elo_a_pregame > elo_h_pregame:
                coeff_b = 1+(elo_a_pregame-elo_h_pregame)/elo_a_pregame
            else:
                coeff_b = 1
        else:
            if elo_h_pregame > elo_a_pregame:
                coeff_b = 1+(elo_h_pregame-elo_a_pregame)/elo_h_pregame
            elif elo_a_pregame > elo_h_pregame:
                coeff_b = 1-(elo_a_pregame-elo_h_pregame)/elo_a_pregame
            else:
                coeff_b = 1

        # Run Calculation
        home_team_elo_change = coeff_a*coeff_b**self.elo_adj_exp_ratio
        elo_h_post_game = elo_h_pregame + home_team_elo_change
        elo_a_post_game = elo_a_pregame - home_team_elo_change
        return elo_h_post_game, elo_a_post_game


    def evaluate_season(self, season):
        """
        Evaluate an entire season with data from DB.. TODO!
        """
