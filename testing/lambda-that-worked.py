import logging
import json
import os

#import mysql.connector

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.aws_lambda.lambda_s3_oauth_flow import LambdaS3OAuthFlow

# process_before_response must be True when running on FaaS
app = App(
    process_before_response=True,
    oauth_flow=LambdaS3OAuthFlow(),
)


@app.event("app_mention")
def handle_app_mentions(body, say, logger):
    logger.info(f'INFO: {body}')
    say("What's up, world?")


@app.command("/hello-bolt-python-lambda")
def respond_to_slack_within_3_seconds(ack):
    # This method is for synchronous communication with the Slack API server
    ack("Thanks!")
    
@app.event("app_home_opened")
def update_home_tab(client, event, logger, context):
    #logger.info(f'Received event: {event}')
    print(f'Received event: {event}')
    print(f'Received client: {client}')
    print(f'Received context: {context}')
    user_id = event['user']
    team_id = event['view']['team_id']
    #bot_token = get_token_for_team(team_id)

    blocks = [
        {
            "type": "section",
            "block_id": "section678",
            "text": {
                "type": "mrkdwn",
                "text": f"Hello, {user_id}!! You are on team {team_id}."
            }
        }
    ]
    client.views_publish(
        user_id=user_id,
        #token=bot_token,
        view={
            "type": "home",
            "blocks":blocks
        }
    )


SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


def handler(event, context):
    print(f'Original event: {event}')
    print(f'Original context: {context}')
    parsed_event = json.loads(event['body'])
    team_id = parsed_event['team_id']
    print(f'Team ID: {team_id}')
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)


# # -- OAuth flow -- #
# export SLACK_SIGNING_SECRET=***
# export SLACK_BOT_TOKEN=xoxb-***
# export SLACK_CLIENT_ID=111.111
# export SLACK_CLIENT_SECRET=***
# export SLACK_SCOPES=app_mentions:read,chat:write

# AWS IAM Role: bolt_python_s3_storage
#   - AmazonS3FullAccess
#   - AWSLambdaBasicExecutionRole

# rm -rf latest_slack_bolt && cp -pr ../../src latest_slack_bolt
# pip install python-lambda
# lambda deploy --config-file aws_lambda_oauth_config.yaml --requirements requirements_oauth.txt