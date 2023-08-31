# QSignups

Welcome to QSignups! This is a Slack App hosted in AWS Lambda to manage the Q signups and calendar for F3 regions.

![Alt text](/screens/qsignups-logo.png?raw=true "QSignups Logo")

## Installation Instructions

1. Use [this link](https://slack.com/oauth/v2/authorize?client_id=3135457248691.3137775183364&scope=app_mentions:read,channels:history,channels:read,chat:write,chat:write.customize,chat:write.public,commands,files:write,im:history,im:write,team:read,users:read,users:read.email,channels:join,files:read,im:read,reactions:read,reactions:write&user_scope=) to install (preferably from desktop)
2. You will probably get an error message - just hit the "try again from here" link

## Usage Instructions

@HelpDesk from F3 Alliance has put together [a great guide to share with your PAX](https://docs.google.com/document/d/1TE63l7dOKy635kbbyRi9TbbeCSx2SISkmBwZIXoqLzk/edit) on how to find and use QSignups.

Further instructions coming for administrators.

## AWS Architecture

![Alt text](/screens/QSignups_Design_2022_06.PNG?raw=true "QSignups Design")

## Feature Requests / Roadmap

Any feedback and ideas you have for the app are welcomed! Please leave feature requests as an Issue with the tag 'enhancement'
- [Issues / Feature Requests](https://github.com/evanpetzoldt/qsignups-lambda/issues)
- [Development Board](https://github.com/users/evanpetzoldt/projects/1/views/1)

# Contributing

QSignups is in active development, and I welcome any and all help or contributions! Feel free to leave an Issue with bugs or feature requests, or even better leave us a Pull Request.

## CI/CD

I've got Github actions that trigger on pushes to the `master` branch... the Github action will build a deployment package and deploy first to a `test` environment, then eventually to our `prod` environment (it will first prompt me for a manual approval).

## Local Development

If you'd like to contribute to QSignups, I highly recommend setting up a local development environment for testing. Below are the steps to get it running (I did this in unix, YMMV on OSX or Windows):

1. Clone the repo:
```sh
git clone https://github.com/evanpetzoldt/qsignups-lambda.git
```
2. Install the [AWS Serverless Application Model (SAM) CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. Set up a local database (code & instructions coming)
4. Create the Slack bot: 
    1. Navigate to [api.slack.com]()
    2. Click "Create an app"
    3. Click "From a manifest", select your workspace
    4. Paste in the manifest below
    5. After creating the app, you will need a couple of items: first, copy and save the Signing Secret from Basic Information. Second, copy and save the Bot User OAuth Token from OAuth & Permissions

```yaml
display_information:
  name: QSignups-dev
  description: Manage your F3 Region Schedule.
  background_color: "#2200AA"
features:
  app_home:
    home_tab_enabled: true
    messages_tab_enabled: true
    messages_tab_read_only_enabled: false
  bot_user:
    display_name: QSignups-dev
    always_online: true
  slash_commands:
    - command: /hello
      url: https://YourNgrokURL/slack/events
      description: Test saying hello
      usage_hint: /hello open mailbox
      should_escape: false
    - command: /schedule
      url: https://YourNgrokURL/slack/events
      description: Query for upcoming schedule
      usage_hint: /schedule tomorrow
      should_escape: false
oauth_config:
  redirect_urls:
    - https://YourNgrokURL/slack/auth
  scopes:
    bot:
      - app_mentions:read
      - channels:history
      - channels:join
      - channels:read
      - chat:write
      - chat:write.customize
      - chat:write.public
      - commands
      - files:read
      - files:write
      - im:history
      - im:read
      - im:write
      - reactions:read
      - reactions:write
      - team:read
      - users:read
      - users:read.email
settings:
  event_subscriptions:
    request_url: https://YourNgrokURL/slack/events
    bot_events:
      - app_home_opened
      - app_mention
  interactivity:
    is_enabled: true
    request_url: https://YourNgrokURL/slack/events
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```


5. Back to your project, create a `env.json` file at the root of the directory. The file should take the format (you will need to replace most of the values):
```json
{
  "Parameters": {
    "SLACK_SIGNING_SECRET": "SIGNING_SECRET_FROM_ABOVE",
    "SLACK_BOT_TOKEN": "BOT_TOKEN_FROM_ABOVE",
    "DATABASE_HOST": "localhost",
    "ADMIN_DATABASE_USER": "local_user",
    "ADMIN_DATABASE_PASSWORD": "local_password",
    "ADMIN_DATABASE_SCHEMA": "f3stcharles"
  }
}
```
  - Small note: I had to use my local ip address for `DATABASE_HOST`, not "localhost"
6. Install ngrok and run the following command from your terminal:
```sh
ngrok http 3000
```
7. Copy the Forwarding URL (has ngrok.app at the end)
8. Back in your browser for the Slack app, replace all of the YourNgrokURLs with the ngrok Forwarding URL
9. You are now ready to roll! This would be a good time to make sure you're on your own branch :)
10. To run the app after you've made some changes, use the following command:
```sh
sam build --use-container --container-env-var-file env.json && sam local start-api --env-vars env.json --warm-containers EAGER
```
11. The `sam build` command will build a Docker container mimicking the functionality of the deployed Lambda. The `local start-api` command starts a listener on that container. The Slack API will send requests to your ngrok URL, which will route to your local Docker. If you want to make changes to the code, stop the deployment by using [Ctrl-C] in the terminal where you ran the `sam build` command, and re-run the command.
    - If you want to avoid rebuilding your Docker every time you make a change, you can simply edit the code created by the build command in the `.aws-sam` directory. However, this folder will not be version controlled, so I choose not to use it