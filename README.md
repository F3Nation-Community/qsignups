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

## Project Status

I consider the app to be functional, but I also have a lot more planned! I welcome all beta testers and co-developers! Hit me up if you'd like to help out [@Moneyball (F3 St. Charles)] on the Nation space, or feel free to submit pull requests.

If you find bugs, you can reach out on Slack or (even better) add the issue to my github Issues log.

### What's Working
* AOs can be added and edited via the admin UI
* Weekly beatdown schedules can be added to the calendar via the admin UI
  * Single (non-recurring) events can also be added via the admin UI
* Single events can be deleted
* Users can take Q slots
* Users can take themselves off Q slots and edit their events (time, special qualifiers like VQ)
* Slack admins can also clearn slots and edit event for others
* Automated creation of a weekly "Weinke" / schedule shown in the app home screen
* Reminder messages to users about upcoming Qs
* Conditional formatting of Weinke to highlight open slots, VQs, etc.
* Support for other event types (QSource, Ruck Beatdowns, etc)
* Optional AO lineups sent to each AO slack channel

### Feature Requests / Roadmap (link: [Issues](https://github.com/evanpetzoldt/qsignups-lambda/issues))
* Google Calendar Integration - In Progress (Thanks @Rudy!)
* More calendar management UI functionality:
  * Delete recurring events
  * Edit recurring events
  * Delete AOs and associated future events
* Switching to weinke images being posted to specific channel (created by QSignups), just a text-based schedule in QSignups - In Progress
* Creation of monthly AO-specific weinkes, to be posted to AO channels at specified intervals and / or accessed via secondary menu
* "Other" option for special event qualifiers with a free text input
  * Addition of programmable region-specific list for commonly used selections?
* Support for events at the same time on the same date at the same AO
* Integration of slackblast
* Integration of welcomebot
* Q resources menu (links to Q101, exicon, helpful tips)
  * Also beatdown wheel of fun 
* Upcoming Qs on home screen - add an Edit button to each
* Site Q - have a way to store these in the table (even support for multiple Site Qs per AO?)

Any other ideas you have are welcomed! Feel free to add an Issue with the tag 'enhancement'.
