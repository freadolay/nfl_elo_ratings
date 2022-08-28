import pyodbc
import pandas as pd
import json
import warnings


def sql_query(sql_query_str):
    with open("src/db_access.json") as f:
        data = json.load(f)
        server = data['server']
        database = data['database']
        username = data['username']
        password = data['password']
        driver = data['driver']

        # Use PYODBC driver for connection
        # TODO: Replace this with a SQL Alchemy Connector to remove warnings
        # connection_string = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD=' + password
        # sql_alchemy_conn_str = urllib.parse.quote_plus(connection_string)
        engine = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';DATABASE='+database+';UID='+username+';PWD=' + password)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = pd.read_sql(sql_query_str, con=engine)
        return df