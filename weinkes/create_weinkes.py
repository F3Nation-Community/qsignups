
import string
from xml.dom.domreg import well_known_implementations
from xml.etree.ElementInclude import include
from decouple import config, UndefinedValueError
import json
from numpy import block
import pandas as pd
import mysql.connector
from datetime import datetime, date, timedelta
import dataframe_image as dfi
# import matplotlib
# import lxml
import ssl
from slack_bolt import App
from slack_sdk import WebClient
import slack_bolt.app
import numpy as np
import pickle
import requests
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
import os
import cv2
import random

# DB config
db_config = {
    "host":"f3stlouis.cac36jsyb5ss.us-east-2.rds.amazonaws.com",
    "user":config('DATABASE_USER'), 
    "password":config('DATABASE_WRITE_PASSWORD'),
    "database":config('DATABASE_SCHEMA') 
}

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

def add_image_noise(img_path):
  img = cv2.imread(img_path)
  row, col, depth = img.shape

  for i in range(3):
    x = random.randint(0, col-1)
    y = random.randint(0, row-1)
    img[y, x] = [127, 127, 127]

  cv2.imwrite(img_path, img)

# Google Photos service connection
def Create_Service(client_secret_file, api_name, api_version, *scopes):
    print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    cred = None

    pickle_file = f'secrets/token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred, static_discovery=False)
        print(API_SERVICE_NAME, 'service created successfully')
        return service
    except Exception as e:
        print(e)
    return None

def create_drive_service():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('secrets/token_drive.json'):
        creds = Credentials.from_authorized_user_file('secrets/token_drive.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)

        # Call the Drive v3 API
        # results = service.files().list(
        #     pageSize=10, fields="nextPageToken, files(id, name)").execute()
        # items = results.get('files', [])

        # if not items:
        #     print('No files found.')
        #     return
        # print('Files:')
        # for item in items:
        #     print(u'{0} ({1})'.format(item['name'], item['id']))
        return service
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        print(f'An error occurred: {error}')
        return None

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt

# Google Photos API config
# API_NAME = 'photoslibrary'
# API_VERSION = 'v1'
# CLIENT_SECRET_FILE = 'secrets/client_secret_google_photos.json'
# SCOPES = ['https://www.googleapis.com/auth/photoslibrary',
#           'https://www.googleapis.com/auth/photoslibrary.sharing']

service = create_drive_service()

# Function to upload to Google Drive
def upload_weinke_google_drive(weinke_name):
  file_metadata = {'name': weinke_name}
  media = MediaFileUpload(f'weinkes/{weinke_name}.png',
                          mimetype='image/png')
  file = service.files().create(body=file_metadata,
                                      media_body=media,
                                      fields='id').execute()
  file_id = file['id']
  request_body = {
      'role': 'reader',
      'type': 'anyone'
  }

  response_permission = service.permissions().create(fileId=file_id, body=request_body).execute()

  return(f'https://drive.google.com/uc?id={file_id}&export=download')

# Function to upload to Google Photos
def upload_weinke_google_photos(weinke_name):
  # setup
  image_file = f'weinkes/{weinke_name}.png'
  upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
  token = pickle.load(open('secrets/token_photoslibrary_v1.pickle', 'rb'))

  # headers for bytes upload
  headers = {
      'Authorization': 'Bearer ' + token.token,
      'Content-type': 'application/octet-stream',
      'X-Goog-Upload-Protocol': 'raw',
      'X-Goog-Upload-File-Name': weinke_name + '.png'
  }

  # open image bytes and upload
  img = open(image_file, 'rb').read()
  response = requests.post(upload_url, data=img, headers=headers)

  # headers for mediaItem upload
  request_body = {
      'newMediaItems': [
          {
              'description':'current week weinke',
              'simpleMediaItem': {
                  'uploadToken': response.content.decode('utf-8')
              }
          }
      ]
  }

  # upload mediaItem and gether id, width, height from response
  upload_response = service.mediaItems().batchCreate(body=request_body).execute()
  upload_response_content = upload_response['newMediaItemResults'][0]
  img_mediaItem_id = upload_response_content['mediaItem']['id']
  img_width = upload_response_content['mediaItem']['mediaMetadata']['width']
  img_height = upload_response_content['mediaItem']['mediaMetadata']['height']

  # gather public url from GET request
  get_url = f'https://photoslibrary.googleapis.com/v1/mediaItems/{img_mediaItem_id}'
  get_header = {'Authorization': 'Bearer ' + token.token}
  get_response = requests.get(get_url, headers=get_header)
  get_response_json = get_response.json()
  img_url = f"{get_response_json['baseUrl']}=w{img_width}-h{img_height}"

  return(img_url)

# Figure out current and next weeks based on current start of day
# I have the week start on Monday and end on Sunday - if this is run on Sunday, "current" week will start tomorrow
tomorrow_day_of_week = (date.today() + timedelta(days=1)).weekday()
current_week_start = date.today() + timedelta(days=-tomorrow_day_of_week+1)
current_week_end = date.today() + timedelta(days=7-tomorrow_day_of_week)
next_week_start = current_week_start + timedelta(weeks=1)
next_week_end = current_week_end + timedelta(weeks=1)

# Function for conditional formatting
def highlight_cells(s):
  # if s.str.contains('The Forge')
  #   forge_flag = s.str.contains('The Forge')
  #   vq_flag = s.str.contains('VQ')
  #   open_flag = (s.str.slice(0, 4)=='OPEN')
  #   return ['background-color: #194D33' if i == 'OPEN' else 'background-color: #000000' for i in is_open]
  highlight_cells_list = list()
  for cell in s:
      if cell is None:
          highlight_cells_list.append('background-color: #000000')
      elif 'The Forge' in cell:
          highlight_cells_list.append('background-color: #c43b01')
      elif ('VQ' in cell) or ('AO Launch' in cell) or ('24 Hr Beatdown' in cell):
          highlight_cells_list.append('background-color: #004dcf')
      elif cell[0:4] == 'OPEN':
          highlight_cells_list.append('background-color: #194D33')
      else:
          highlight_cells_list.append('background-color: #000000')
  return pd.Series(highlight_cells_list)

# loop through regions
with mysql.connector.connect(**db_config) as mydb:
  sql_region = "SELECT * FROM qsignups_regions;"
  df_regions = pd.read_sql(sql_region, mydb)

for index, row in df_regions.iterrows():
  team_id = row['team_id']
  print(f'working on team {team_id}...')

  # Generate SQL pulls
  sql_current = f"""
  SELECT m.*, a.ao_display_name, a.ao_location_subtitle
  FROM qsignups_master m
  LEFT JOIN qsignups_aos a
  ON m.team_id = a.team_id 
    AND m.ao_channel_id = a.ao_channel_id
  WHERE m.team_id = '{team_id}'
    AND m.event_date >= DATE('{current_week_start}')
    AND m.event_date <= DATE('{current_week_end}')
  ORDER BY m.ao_channel_id, m.event_date, m.event_time;
  """

  sql_next = f"""
  SELECT m.*, a.ao_display_name, a.ao_location_subtitle
  FROM qsignups_master m
  LEFT JOIN qsignups_aos a
  ON m.team_id = a.team_id
    AND m.ao_channel_id = a.ao_channel_id
  WHERE m.team_id = '{team_id}'
    AND m.event_date >= DATE('{next_week_start}')
    AND m.event_date <= DATE('{next_week_end}')
  ORDER BY m.ao_channel_id, m.event_date, m.event_time;
  """

  # Pull data
  try:
    with mysql.connector.connect(**db_config) as mydb:
      df_current = pd.read_sql_query(sql_current, mydb, parse_dates=['event_date'])
      df_next = pd.read_sql_query(sql_next, mydb, parse_dates=['event_date'])
  except Exception as e:
    print(f'There was a problem pull from the db: {e}')

  df_list = [
    [df_current, 'current_week_weinke'],
    [df_next, 'next_week_weinke']
  ]

  for week in df_list:
    df = week[0].copy()
    output_name = week[1]

    # Pull up prior processed data for comparison
    try:
      df_prior = pd.read_csv(f'weinkes/{team_id}_{output_name}.csv')
      df_prior['event_time'] = df_prior['event_time'].astype(str).str.zfill(4)
      df_compare = df.compare(df_prior)
    except:
      df_compare = [1, 2, 3]

    if len(df_compare)>=1:
      df.to_csv(f'weinkes/{team_id}_{output_name}.csv', index=False)
      
      # date operations
      df['event_date_fmt'] = df['event_date'].dt.strftime("%m/%d")

      # Reset index
      df.reset_index(inplace=True)

      # Build cell labels
      df.loc[df['q_pax_name'].isna(), 'q_pax_name'] = 'OPEN!'
      df['q_pax_name'].replace('\s\(([\s\S]*?\))','',regex=True, inplace=True) # Take out pax name parentheses
      df['label'] = df['q_pax_name'] + '\n' + df['event_time']
      df.loc[(df['event_special'].values != None), ('label')] = df['q_pax_name'] + '\n' + df['event_special'] + '\n' + df['event_time']
      df['AO\nLocation'] = df['ao_display_name'] + '\n' + df['ao_location_subtitle']
      df['AO\nLocation2'] = df['AO\nLocation'].str.replace('The ','')

      # # Combine cells for days / AOs with more than one event
      # df.sort_values(['event_date', 'event_time'], ignore_index=True, inplace=True)
      # prior_date = ''
      # prior_label = ''
      # include_list = []
      # for i in range(len(df)):
      #   row = df.loc[i]
      #   if row['event_date_fmt'] == prior_date:
      #     df.loc[i, 'label'] = prior_label + '\n' + df.loc[i, 'label']
      #     include_list.append(False)
      #   else:
      #     if prior_label != '':
      #       include_list.append(True)
      #     prior_date = row['event_date_fmt']
      #     prior_label = row['label']
      # include_list.append(True)

      # # filter out duplicate dates
      # df = df[include_list]

      # Reshape to wide format by date
      df2 = df.pivot(index='AO\nLocation', columns=['event_day_of_week', 'event_date_fmt'], values='label').fillna("")

      # Sort and enforce word wrap on labels
      df2.sort_index(axis=1, level=['event_date_fmt'], inplace=True)
      df2.columns = df2.columns.map('\n'.join).str.strip('\n')
      df2.reset_index(inplace=True)

      # Take out "The " for sorting
      df2['AO\nLocation2'] = df2['AO\nLocation'].str.replace('The ','')
      df2.sort_values(by=['AO\nLocation2'], axis=0, inplace=True)
      df2.drop(['AO\nLocation2'], axis=1, inplace=True)
      df2.reset_index(inplace=True, drop=True)

      # Set CSS properties for th elements in dataframe
      th_props = [
        ('font-size', '15px'),
        ('text-align', 'center'),
        ('font-weight', 'bold'),
        ('color', '#F0FFFF'),
        ('background-color', '#000000'),
        ('white-space', 'pre-wrap'),
        ('border', '1px solid #F0FFFF')
        ]

      # Set CSS properties for td elements in dataframe
      td_props = [
        ('font-size', '15px'),
        ('text-align', 'center'),
        ('white-space', 'pre-wrap'),
        #('background-color', '#000000'),
        ('color', '#F0FFFF'),
        ('border', '1px solid #F0FFFF')
        ]

      # Set table styles
      styles = [
        dict(selector="th", props=th_props),
        dict(selector="td", props=td_props)
        ]

      # set style and export png
      df_styled = df2.style.set_table_styles(styles).apply(highlight_cells).hide_index()
      # df_styled = df2.style.set_table_styles(styles).hide_index()
      # df2.style.apply(highlight_cells)
      dfi.export(df_styled,f"weinkes/{team_id}_{output_name}.png")
      # add_image_noise(f"weinkes/{team_id}_{output_name}.png")

      # primary upload for public viewing
      # instantiate Slack client (user token this time!)
      ssl_context = ssl.create_default_context()
      ssl_context.check_hostname = False
      ssl_context.verify_mode = ssl.CERT_NONE
      # slack_client = WebClient(
      #   config('SLACK_USER_TOKEN'), ssl=ssl_context
      # )
    
      # # post to channel (bot playground for now)
      # response = slack_client.files_upload(
      #   file=f'weinkes/{team_id}_{output_name}.png',
      #   initial_comment=output_name,
      #   channels=['C03EKNLPPCZ']
      # )
      # response2 = slack_client.files_sharedPublicURL(file=response['file']['id'])

      # # gather url info
      # loc = response['file']['permalink_public']
      # secrets = str.split(str.lstrip(loc,'https://slack-files.com/'), '-')
      # url = f'https://files.slack.com/files-pri/{secrets[0]}-{secrets[1]}/{team_id.lower()}_{output_name}.png?pub_secret={secrets[2]}'

      # upload to Google Photos
      img_url = upload_weinke_google_drive(f'{team_id}_{output_name}')

      # optionally upload to the region's weinke channel
      try:
        region_weinke_created = False
        if (row['weekly_weinke_channel'] is not None) and (output_name == 'current_week_weinke'):
          # establish slack client and upload
          slack_client = WebClient(row['bot_token'], ssl=ssl_context)
          try:
            if row['weekly_weinke_updated'] is not None:
              slack_client.chat_delete(channel=row['weekly_weinke_channel'], ts=row['weekly_weinke_updated'])
          except:
            print('weinke post not found, skipping deletion...')
          response = slack_client.files_upload(
            file=f'weinkes/{team_id}_{output_name}.png',
            initial_comment="This week's schedule",
            channels=row['weekly_weinke_channel']
          )
          region_upload_ts = response['file']['shares']['public'][row['weekly_weinke_channel']][0]['ts']
          region_weinke_created = True
      except Exception as e:
        print(f'There was a problem updating the weinke channel: {e}')

      # update schedule_weinke table
      if region_weinke_created:
        sql_update = f"UPDATE qsignups_regions SET {output_name} = '{img_url}', weekly_weinke_updated = '{region_upload_ts}' WHERE team_id = '{team_id}';"
      else:
        sql_update = f"UPDATE qsignups_regions SET {output_name} = '{img_url}' WHERE team_id = '{team_id}';"
      
      try:
        with mysql.connector.connect(**db_config) as mydb:
          mycursor = mydb.cursor()
          mycursor.execute(sql_update)
          mycursor.execute("COMMIT;")
      except Exception as e:
        print(f'There was a problem updating the database: {e}')

