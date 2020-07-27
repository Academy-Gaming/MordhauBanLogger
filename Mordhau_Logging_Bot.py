import os
import discord
import asyncio

import re
import json
import hashlib
from time import sleep
import dateutil.parser
import config
import requests
import utilMonthly as util
import time
import datetime
import traceback
import io

playerhistoryData = {}

configServersRaw = []
for x in config.config['SERVERS']:
    configServersRaw.append(str(x) + "=" + str(config.config['SERVERS'][x]))
servers = {x[0].strip(): x[1].strip() for x in [y.split("=") for y in configServersRaw]}


def readLogfilesLoop():
    lastDateRead = {}

    while True:
        for server in servers:
            logfile = io.open(servers[server], mode="r", encoding="utf-8")
            for logfile_line in logfile.readlines():
                # print(logfile_line)
                if not server in lastDateRead:
                    lastDateRead[server] = datetime.datetime.now()
                if not 'unbanned player' in logfile_line:
                    if 'banned player' in logfile_line:
                        lineDate = logfile_line.strip().split("]")[0].replace("[", "").split(":")[0]
                        # print("Date found:"+str(lineDate))
                        date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
                        if date_object > lastDateRead[server]:
                            lastDateRead[server] = date_object
                            print("Going to handle ban message " + str(logfile_line))
                            event = {}
                            event['Message'] = logfile_line
                            event['Server'] = server
                            banhandler(event)
                if 'muted player' in logfile_line:
                    lineDate = logfile_line.strip().split("]")[0].replace("[", "").split(":")[0]
                    # print("Date found:"+str(lineDate))
                    date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
                    if date_object > lastDateRead[server]:
                        lastDateRead[server] = date_object
                        print("Going to handle mute message " + str(logfile_line))
                        event = {}
                        event['Message'] = logfile_line
                        event['Server'] = server
                        mutehandler(event)
                if 'unbanned player' in logfile_line:
                    lineDate = logfile_line.strip().split("]")[0].replace("[", "").split(":")[0]
                    # print("Date found:"+str(lineDate))
                    date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
                    if date_object > lastDateRead[server]:
                        lastDateRead[server] = date_object
                        print("Going to handle unban message " + str(logfile_line))
                        event = {}
                        event['Message'] = logfile_line
                        event['Server'] = server
                        unbanhandler(event)

            # lastDateRead[server] = datetime.datetime.now()
            logfile.close()
    time.sleep(5)


def banhandler(event):
    ban_message = event['Message']
    print("Parsing potential ban message {}".format(ban_message))
    admin, steamid, ban_duration, reason = parse_messageBan(ban_message)

    if admin == "ERROR" and steamid == "ERROR" and ban_duration == "ERROR" and reason == "ERROR":
        return None

    if ban_duration == 0:
        ban_duration = 'PERMANENT'
    else:
        ban_duration = int(ban_duration)
    if reason == 'Idle':
        print('Player kicked for being idle. No action required.')
        return False
    # Looking up Player name by SteamID
    print('Looking up playername by steam ID')
    steam_key = str(config.config['SETTINGS']['steam_key'].strip())
    try:
        resp = requests.get(
            'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={}&steamids={}'.format(steam_key,
                                                                                                         steamid))
    except:
        print("Error looking up user on steam")
    try:
        print(resp.text)
        playername = resp.json()['response']['players'][0]['personaname']
        playeravatarlink = resp.json()['response']['players'][0]['avatarfull']
    except:
        playername = ""
        playeravatarlink = ""

    server = event['Server']

    playerhistory = get_playerhistory(server, steamid)
    if not playerhistory:
        playerhistory = []

    if len(playerhistory) > 10:
        playerhistory = playerhistory[-10:]

    if not 'Vote kick' in reason:
        payload = {
            'SteamId': steamid,
            'Server': server,
            'Playername': playername,
            'BanDuration': ban_duration,
            'Reason': reason,
            'BanAdmin': admin,
            'PlayerAvatar': playeravatarlink,
            'Type': "BAN",
            'BanHistory': playerhistory
        }
        handlerDiscord(payload)

    else:
        print('Player was kicked by vote - not sending discord notification.')

    playerhistory.append({
        'BanDate': datetime.datetime.isoformat(datetime.datetime.now()),
        'BanDuration': ban_duration,
        'BanAdmin': admin,
        'BanReason': reason,
        'Type': "BAN"
    })

    update_playerhistory(server, steamid, playername, playerhistory)
    return True


def mutehandler(event):
    mute_message = event['Message']
    print("Parsing potential mute message {}".format(mute_message))
    admin, steamid, ban_duration = parse_messageMute(mute_message)

    if admin == "ERROR" and steamid == "ERROR" and ban_duration == "ERROR":
        return None

    if ban_duration == 0:
        ban_duration = 'PERMANENT'
    else:
        ban_duration = int(ban_duration)
    # Looking up Player name by SteamID
    print('Looking up playername by steam ID')
    steam_key = str(config.config['SETTINGS']['steam_key'].strip())
    try:
        resp = requests.get(
            'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={}&steamids={}'.format(steam_key,
                                                                                                         steamid))
    except:
        print("Error looking up user on steam")
    try:
        print(resp.text)
        playername = resp.json()['response']['players'][0]['personaname']
        playeravatarlink = resp.json()['response']['players'][0]['avatarfull']
    except:
        playername = ""
        playeravatarlink = ""

    server = event['Server']

    playerhistory = get_playerhistory(server, steamid)
    if not playerhistory:
        playerhistory = []

    reason = 'None given'

    if len(playerhistory) > 10:
        playerhistory = playerhistory[-10:]

    payload = {
        'SteamId': steamid,
        'Server': server,
        'Playername': playername,
        'BanDuration': ban_duration,
        'MuteAdmin': admin,
        'PlayerAvatar': playeravatarlink,
        'Type': "MUTE",
        'BanHistory': playerhistory
    }
    handlerDiscord(payload)

    playerhistory.append({
        'BanDate': datetime.datetime.isoformat(datetime.datetime.now()),
        'BanDuration': ban_duration,
        'MuteAdmin': admin,
        'BanReason': reason,
        'Type': "MUTE"
    })

    update_playerhistory(server, steamid, playername, playerhistory)
    return True


def unbanhandler(event):
    unban_message = event['Message']
    print("Parsing potential unban message {}".format(unban_message))
    admin, steamid = parse_messageUnban(unban_message)

    if admin == "ERROR" and steamid == "ERROR":
        return None

    # Looking up Player name by SteamID
    print('Looking up playername by steam ID')
    steam_key = str(config.config['SETTINGS']['steam_key'].strip())
    try:
        resp = requests.get(
            'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={}&steamids={}'.format(steam_key,
                                                                                                         steamid))
    except:
        print("Error looking up user on steam")
    try:
        print(resp.text)
        playername = resp.json()['response']['players'][0]['personaname']
        playeravatarlink = resp.json()['response']['players'][0]['avatarfull']
    except:
        playername = ""
        playeravatarlink = ""

    server = event['Server']

    playerhistory = get_playerhistory(server, steamid)
    if not playerhistory:
        playerhistory = []

    if len(playerhistory) > 10:
        playerhistory = playerhistory[-10:]

    payload = {
        'SteamId': steamid,
        'Server': server,
        'Playername': playername,
        'UnbanAdmin': admin,
        'PlayerAvatar': playeravatarlink,
        'Type': "UNBAN",
        'BanHistory': playerhistory
    }
    handlerDiscord(payload)
    return True


def parse_messageBan(message):
    if 'reason: Idle' in message:
        # Not a ban
        return None, 0, 'Idle'
    # LogMordhauPlayerController: Display: Admin BIG | dan (76561198292933506) banned player 76561199053620235 (Duration: 0, Reason: RDM)
    # regex_capture = re.compile("Banned Steam ID (\d+), duration: (\d+), reason:(.*)?")
    regex_capture = re.compile(
        "LogMordhauPlayerController: Display: Admin (.+) banned player (\d+) \(Duration: (\d+), Reason: (.*)\)")
    regex_parse = re.search(regex_capture, message)
    if not regex_parse:
        print('Failed to parse the regex for message!!!')
        return "ERROR", "ERROR", "ERROR"
    admin = regex_parse[1]
    steamid = regex_parse[2]
    duration = regex_parse[3]
    try:
        reason = regex_parse[4]
    except IndexError:
        reason = 'None given'
    return admin, steamid, duration, reason


def parse_messageMute(message):
    # LogMordhauPlayerController: Display: Admin AssaultLine (76561198005305380) muted player 76561198966484285 (Duration: 10000)
    # regex_capture = re.compile("LogMordhauPlayerController: Display: (\d+), duration: (\d+), reason:(.*)?")
    regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) muted player (\d+) \(Duration: (\d+)\)")
    regex_parse = re.search(regex_capture, message)
    if not regex_parse:
        print('Failed to parse the regex for message!!!')
        return "ERROR", "ERROR", "ERROR"
    admin = regex_parse[1]
    steamid = regex_parse[2]
    duration = regex_parse[3]
    return admin, steamid, duration


def parse_messageUnban(message):
    # LogMordhauPlayerController: Display: Admin AssaultLine (76561198005305380) muted player 76561198966484285 (Duration: 10000)
    # regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) muted player (\d+) \(Duration: (\d+)\)")
    regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) unbanned player (\d+)")
    regex_parse = re.search(regex_capture, message)
    if not regex_parse:
        print('Failed to parse the regex for message!!!')
        return "ERROR", "ERROR"
    admin = regex_parse[1]
    steamid = regex_parse[2]
    return admin, steamid


def get_playerhistory(server, steamid):
    global playerhistoryData

    now = datetime.datetime.now()
    year = now.year
    month = now.month

    try:
        playerhistoryData = util.load_data(year, month, "playerhistory")
    except:
        # traceback.print_exc()
        print("Some kind of load error")
        playerhistoryData = {}

    print(playerhistoryData)

    if str(server) in playerhistoryData:
        print("Server has old data")
        if str(steamid) in playerhistoryData[str(server)]:
            print("Returning old history")
            return playerhistoryData[str(server)][str(steamid)]["history"]

    print("No old data found")
    return None


def update_playerhistory(server, steamid, playername, history):
    global playerhistoryData

    now = datetime.datetime.now()
    year = now.year
    month = now.month

    if not str(server) in playerhistoryData:
        playerhistoryData[str(server)] = {}
    if not str(steamid) in playerhistoryData[str(server)]:
        playerhistoryData[str(server)][str(steamid)] = {}
        playerhistoryData[str(server)][str(steamid)]["history"] = []
        playerhistoryData[str(server)][str(steamid)]["playername"] = ""

    playerhistoryData[str(server)][str(steamid)]["history"] = history
    playerhistoryData[str(server)][str(steamid)]["playername"] = playername

    print("Going to save: " + str(playerhistoryData))

    util.save_data(year, month, playerhistoryData, "playerhistory")


def handlerDiscord(data):
    token = str(config.discordtoken)
    channel_id = str(config.config['SETTINGS']['channel_id'].strip())
    print('Initializing discord client.')
    client = DiscordClient(data, channel_id)
    print('Client initialized - running client.')
    run_client(client, token)


def run_client(client, *args):
    loop = asyncio.get_event_loop()
    finished = False
    while not finished:
        loop.run_until_complete(client.start(*args))
        finished = True
        print("Clearing loop")
        client.clear()


class DiscordClient(discord.Client):
    def __init__(self, ban_message, channel_id):
        super(DiscordClient, self).__init__()
        self.ban_message = ban_message
        self.channel_id = int(channel_id)

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        print('Getting channel ID.')
        channel = self.get_channel(int(self.channel_id))
        if channel is None:
            print("ERROR: Unable to get discord channel")
            await self.close()

        if not self.ban_message['BanHistory']:
            past_offenses = 'NONE'
        else:
            past_offenses = '\n------------------\n' + '\n------------------\n'.join([
                (
                        'Type: ' + m['Type'] +
                        '\nDate: ' + m['BanDate'] +
                        '\nOffense: ' + m['BanReason'] +
                        '\nDuration: ' + str(m['BanDuration']) + ' (in minutes)'
                )
                for m in self.ban_message['BanHistory']
            ]) + '\n------------------'
        print('Sending message: ', self.ban_message, 'to channel:', self.channel_id)
        if self.ban_message['Type'] == "BAN":
            message = f'''
**BAN REPORT:**

**Server:** `{self.ban_message['Server']}`
**SteamId:** `{self.ban_message['SteamId']}`
**Playername:** `{self.ban_message['Playername']}`
**Offense:** `{self.ban_message['Reason']}`
**Admin:** `{self.ban_message['BanAdmin']}`
**Duration:** `{self.ban_message['BanDuration']} minutes`

**Previous and Current Offenses:** ```{past_offenses}```
'''
            embed = discord.Embed(description=message,color=0xff0000)

        elif self.ban_message['Type'] == "MUTE":
            message = f'''
**MUTE REPORT:**

**Server:** `{self.ban_message['Server']}`
**SteamId:** `{self.ban_message['SteamId']}`
**Playername:** `{self.ban_message['Playername']}`
**Admin:** `{self.ban_message['MuteAdmin']}`
**Duration:** `{self.ban_message['BanDuration']} minutes`

**Previous and Current Offenses:** ```{past_offenses}```
'''
            embed = discord.Embed(description=message,color=0x0087c8)

        elif self.ban_message['Type'] == "UNBAN":
            message = f'''
**UNBAN REPORT:**

**Server:** `{self.ban_message['Server']}`
**SteamId:** `{self.ban_message['SteamId']}`
**Playername:** `{self.ban_message['Playername']}`
**Admin:** `{self.ban_message['UnbanAdmin']}`

**Previous and Current Offenses:** ```{past_offenses}```
'''
            embed = discord.Embed(description=message,color=0x00ff00)
        
        
        embed.set_image(url=self.ban_message['PlayerAvatar'])

        await channel.send(embed=embed)
        print('Message sent, closing client.')
        await self.close()


readLogfilesLoop()
