# MordhauBanLogger
Discord bot that waits for bans or mutes to show in the Mordhau.log and then logs to a json and sends an alert to a Discord channel with all punishment information.

The bot has a very simple setup as long as you are running it on the same dedicated server or VPS that your Mordhau servers are ran on.

You will need the following info to set up the bot:

- Discord Bot token that is made at https://discord.com/developers/applications, also invite the bot to your discord.
- Steam API Key in order to resolve the profile picture and steam info of punished players https://steamcommunity.com/dev/apikey
- Channel in Discord set up for your Ban Reports to be sent to by the bot.


To get it to run from the source without the exe you would need to install:

- Python (newest version is recommended, but anything over 3.6.1 should work)
- aiohttp == 3.5.4
- python_dateutil == 2.8.0
- requests == 2.22.0
- websockets == 7.0

Setup:
The files must be on your machine hosting the servers, it is possible to monitor remote servers also. (I will make a guide for that at a later date unless someone beats me to it.)
Open the Config.ini and input all the info that is required for the bot to run.
In the Servers section you can put the name of the server being monitored and the directory that leads exactly to your Mordhau.log file. (it must point to the Mordhau.log, not just the folder its in)

For Example:
Academy_Duels=C:\Users\Administrator\Desktop\WindowsGSM Servers\servers\9\serverfiles\Mordhau\Saved\Logs\Mordhau.log

You can add as many servers as you want monitored.
Another thing to keep in mind is that this bot only shows online while sending an alert and then instantly goes back to offline. Even if its running 24/7 you won't see the bot online unless its sending an alert.

Logging to File:

YOU MUST CREATE THE "save" FOLDER IN THE FOLDER THAT THE BOT IS RUNNING IN.

The bot logs all the same info that is sent to discord into a json file that is stored within save/{year}/{month}/{Server}.json
Each of your servers will have their own json. It will only create a new json each month for each server to cut down on the amount of files you may have to search through.
(will probably implement database support in the future)


Important Note, specially if the bot does not react: 
Check if the Log timestamps are fitting the servers system time. If not, you need to add the -LOCALLOGTIMES server start parameter and restart the server. If you have no access to it, you would currently have to edit the code. Maybe making a Offset config-variable in the future?!