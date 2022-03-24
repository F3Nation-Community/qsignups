from email import message
import logging
import json
import os
import mysql.connector
from contextlib import ContextDecorator
from datetime import datetime, timezone, timedelta, date
import pandas as pd

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.aws_lambda.lambda_s3_oauth_flow import LambdaS3OAuthFlow

class my_connect(ContextDecorator):
    def __init__(self, team_id):
        self.data_base_connection = ''
        self.team_id = team_id

    def __enter__(self):
        print(self.team_id)
        # self.data_base_connection = mysql.connector.connect(
        #     host=os.environ['DATABASE_HOST'],
        #     user=os.environ['ADMIN_DATABASE_USER'],
        #     passwd=os.environ['ADMIN_DATABASE_PASSWORD']
        # )

        # sql_select = f'SELECT schema_name, user, password FROM paxminer.regions WHERE team_id = {team_id};'

        # mycursor = self.data_base_connection.cursor()
        # mycursor.execute(sql_select)
        # schema, user, password = mycursor.fetchone()

        #cursor = self.data_base_connection.cursor()
        #return cursor
        # return self.data_base_connection, schema
        return self

    def __exit__(self, *exc):
        # self.data_base_connection.close()
        return False

with my_connect('T123') as team_object:
    print(f'your team is: {team_object.team_id}')

temp = my_connect('T1234')
temp.data_base_connection