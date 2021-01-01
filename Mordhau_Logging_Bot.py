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
playerlink = ""

configServersRaw = []
for x in config.config['SERVERS']:
	configServersRaw.append(str(x)+"="+str(config.config['SERVERS'][x]))
servers = {x[0].strip(): x[1].strip() for x in [y.split("=") for y in configServersRaw]}

def readLogfilesLoop():

	lastDateRead = {}

	while True:
		for server in servers:
			logfile = io.open(servers[server], mode="r", encoding="utf-8")
			for logfile_line in logfile.readlines():
				#print(logfile_line)
				if not server in lastDateRead:
					lastDateRead[server] = datetime.datetime.now()
				# BAN
				if not 'unbanned player' in logfile_line:
				# This conditional prevents the bot from parsing messages that contain 'unbanned player' in it.
					if 'banned player' in logfile_line:
						lineDate = logfile_line.strip().split("]")[0].replace("[","").split(":")[0]
						#print("Date found:"+str(lineDate))
						date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
						if date_object > lastDateRead[server]:
							lastDateRead[server] = date_object
							print("Going to handle ban message "+str(logfile_line))
							event = {}
							event['Message'] = logfile_line
							event['Server'] = server
							banhandler(event)
				# UNBAN
				if 'unbanned player' in logfile_line:
					lineDate = logfile_line.strip().split("]")[0].replace("[","").split(":")[0]
					#print("Date found:"+str(lineDate))
					date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
					if date_object > lastDateRead[server]:
						lastDateRead[server] = date_object
						print("Going to handle unban message "+str(logfile_line))
						event = {}
						event['Message'] = logfile_line
						event['Server'] = server
						unbanhandler(event)
				# KICK
				if 'kicked player' in logfile_line:
					lineDate = logfile_line.strip().split("]")[0].replace("[","").split(":")[0]
					#print("Date found:"+str(lineDate))
					date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
					if date_object > lastDateRead[server]:
						lastDateRead[server] = date_object
						print("Going to handle kick message "+str(logfile_line))
						event = {}
						event['Message'] = logfile_line
						event['Server'] = server
						kickhandler(event)
				# MUTE
				if not 'unmuted player' in logfile_line:
				# This conditional prevents the bot from parsing messages that contain 'unmuted player' in it.
					if 'muted player' in logfile_line:
						lineDate = logfile_line.strip().split("]")[0].replace("[","").split(":")[0]
						#print("Date found:"+str(lineDate))
						date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
						if date_object > lastDateRead[server]:
							lastDateRead[server] = date_object
							print("Going to handle mute message "+str(logfile_line))
							event = {}
							event['Message'] = logfile_line
							event['Server'] = server
							mutehandler(event)
				# UNMUTE
				if 'unmuted player' in logfile_line:
					lineDate = logfile_line.strip().split("]")[0].replace("[","").split(":")[0]
					#print("Date found:"+str(lineDate))
					date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
					if date_object > lastDateRead[server]:
						lastDateRead[server] = date_object
						print("Going to handle unmute message "+str(logfile_line))
						event = {}
						event['Message'] = logfile_line
						event['Server'] = server
						unmutehandler(event)
				# ADDADMIN
				if 'Added PlayFab ID' in logfile_line:
					lineDate = logfile_line.strip().split("]")[0].replace("[","").split(":")[0]
					#print("Date found:"+str(lineDate))
					date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
					if date_object > lastDateRead[server]:
						lastDateRead[server] = date_object
						print("Going to handle addadmin message "+str(logfile_line))
						event = {}
						event['Message'] = logfile_line
						event['Server'] = server
						addadminhandler(event)
				# REMOVEADMIN
				if 'Removed PlayFab ID' in logfile_line:
					lineDate = logfile_line.strip().split("]")[0].replace("[","").split(":")[0]
					#print("Date found:"+str(lineDate))
					date_object = datetime.datetime.strptime(lineDate, '%Y.%m.%d-%H.%M.%S')
					if date_object > lastDateRead[server]:
						lastDateRead[server] = date_object
						print("Going to handle removeadmin message "+str(logfile_line))
						event = {}
						event['Message'] = logfile_line
						event['Server'] = server
						removeadminhandler(event)

				#lastDateRead[server] = datetime.datetime.now()
			logfile.close()
	time.sleep(1)

def banhandler(event):
	ban_message = event['Message']
	print("Parsing potential ban message {}".format(ban_message))
	admin,playfabid,ban_duration,reason = parse_messageBan(ban_message)

	if admin == "ERROR" and playfabid == "ERROR" and ban_duration == "ERROR" and reason == "ERROR":
		return None

	if ban_duration == 0:
		ban_duration = 'PERMANENT'
	else:
		ban_duration = int(ban_duration)
	if reason == 'Idle':
		print('Player kicked for being idle. No action required.')
		return False

	server = event['Server']

	playerhistory = get_playerhistory(server,playfabid)
	if not playerhistory:
		playerhistory = []

	if len(playerhistory) > 10:
		playerhistory = playerhistory[-10:]

	if not 'Vote kick' in reason:
		payload={
			'PlayFabID': playfabid,
			'Server': server,
			'BanDuration': ban_duration,
			'Reason': reason,
			'BanAdmin': admin,
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

	update_playerhistory(server,playfabid,playerhistory)
	return True

def unbanhandler(event):
	unban_message = event['Message']
	print("Parsing potential unban message {}".format(unban_message))
	admin,playfabid = parse_messageUnban(unban_message)

	if admin == "ERROR" and playfabid == "ERROR":
		return None

	server = event['Server']

	playerhistory = get_playerhistory(server,playfabid)
	if not playerhistory:
		playerhistory = []

	if len(playerhistory) > 10:
		playerhistory = playerhistory[-10:]

	payload={
		'PlayFabID': playfabid,
		'Server': server,
		'UnbanAdmin': admin,
		'Type': "UNBAN",
		'BanHistory': playerhistory
	}
	handlerDiscord(payload)
	return True

def kickhandler(event):
	kick_message = event['Message']
	print("Parsing potential kick message {}".format(kick_message))
	admin,playfabid, reason = parse_messageKick(kick_message)

	if admin == "ERROR" and playfabid == "ERROR" and reason == "ERROR":
		return None

	server = event['Server']

	playerhistory = get_playerhistory(server,playfabid)
	if not playerhistory:
		playerhistory = []

	if len(playerhistory) > 10:
		playerhistory = playerhistory[-10:]

	payload={
		'PlayFabID': playfabid,
		'Server': server,
		'Reason': reason,
		'KickAdmin': admin,
		'Type': "KICK",
		'BanHistory': playerhistory
	}
	handlerDiscord(payload)
	return True

def mutehandler(event):
	mute_message = event['Message']
	print("Parsing potential mute message {}".format(mute_message))
	admin,playfabid,ban_duration = parse_messageMute(mute_message)

	if admin == "ERROR" and playfabid == "ERROR" and ban_duration == "ERROR":
		return None

	if ban_duration == 0:
		ban_duration = 'PERMANENT'
	else:
		ban_duration = int(ban_duration)

	server = event['Server']

	playerhistory = get_playerhistory(server,playfabid)
	if not playerhistory:
		playerhistory = []

	reason = 'None given'

	if len(playerhistory) > 10:
		playerhistory = playerhistory[-10:]

	payload={
		'PlayFabID': playfabid,
		'Server': server,
		'BanDuration': ban_duration,
		'BanAdmin': admin,
		'Type': "MUTE",
		'BanHistory': playerhistory
	}
	handlerDiscord(payload)

	playerhistory.append({
				'BanDate': datetime.datetime.isoformat(datetime.datetime.now()),
				'BanDuration': ban_duration,
				'BanAdmin': admin,
				'BanReason': reason,
				'Type': "MUTE"
			})

	update_playerhistory(server,playfabid,playerhistory)
	return True

def unmutehandler(event):
	unmute_message = event['Message']
	print("Parsing potential unmute message {}".format(unmute_message))
	admin,playfabid = parse_messageUnmute(unmute_message)

	if admin == "ERROR" and playfabid == "ERROR":
		return None

	server = event['Server']

	playerhistory = get_playerhistory(server,playfabid)
	if not playerhistory:
		playerhistory = []

	if len(playerhistory) > 10:
		playerhistory = playerhistory[-10:]

	payload={
		'PlayFabID': playfabid,
		'Server': server,
		'UnmuteAdmin': admin,
		'Type': "UNMUTE",
		'BanHistory': playerhistory
	}
	handlerDiscord(payload)
	return True

def addadminhandler(event):
	addadmin_message = event['Message']
	print("Parsing potential addadmin message {}".format(addadmin_message))
	playfabid = parse_messageAddAdmin(addadmin_message)

	if playfabid == "ERROR":
		return None

	server = event['Server']

	playerhistory = get_playerhistory(server,playfabid)
	if not playerhistory:
		playerhistory = []

	if len(playerhistory) > 10:
		playerhistory = playerhistory[-10:]

	payload={
		'PlayFabID': playfabid,
		'Server': server,
		'Type': "ADDADMIN",
		'BanHistory': playerhistory
	}
	handlerDiscord(payload)
	return True

def removeadminhandler(event):
	removeadmin_message = event['Message']
	print("Parsing potential removeadmin message {}".format(removeadmin_message))
	playfabid = parse_messageRemoveAdmin(removeadmin_message)

	if playfabid == "ERROR":
		return None

	server = event['Server']

	playerhistory = get_playerhistory(server,playfabid)
	if not playerhistory:
		playerhistory = []

	if len(playerhistory) > 10:
		playerhistory = playerhistory[-10:]

	payload={
		'PlayFabID': playfabid,
		'Server': server,
		'Type': "REMOVEADMIN",
		'BanHistory': playerhistory
	}
	handlerDiscord(payload)
	return True

def parse_messageBan(message):
	if 'reason: Idle' in message:
		# Not a ban
		return None, 0, 'Idle'
	#LogMordhauPlayerController: Display: Admin BIG | dan (76561198292933506) banned player 76561199053620235 (Duration: 0, Reason: RDM)
	#regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) banned player (\d+) \(Duration: (\d+), Reason: (.*)\)")
	#LogMordhauPlayerController: Display: Admin dan from dans duels (FFBCF4758910B074) banned player D0904EAFADF55768 (Duration: 1, Reason: test ban)
	regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) banned player (.+) \(Duration: (\d+), Reason: (.*)\)")
	regex_parse = re.search(regex_capture, message)
	if not regex_parse:
		print('Failed to parse the regex for message!!!')
		return "ERROR","ERROR","ERROR"
	admin = regex_parse[1]
	playfabid = regex_parse[2]
	duration = regex_parse[3]
	try:
		reason = regex_parse[4]
	except IndexError:
		reason = 'None given'
	return admin,playfabid,duration,reason

def parse_messageUnban(message):
	#LogMordhauPlayerController: Display: Admin dan from dans duels (FFBCF4758910B074) unbanned player D0904EAFADF55768
	#regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) unbanned player (\d+)")
	regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) unbanned player (.+)")
	regex_parse = re.search(regex_capture, message)
	if not regex_parse:
		print('Failed to parse the regex for message!!!')
		return "ERROR","ERROR"
	admin = regex_parse[1]
	playfabid = regex_parse[2]
	return admin,playfabid

def parse_messageKick(message):
	#LogMordhauPlayerController: Display: Admin dan from dans duels (FFBCF4758910B074) kicked player D0904EAFADF55768 (Reason: test kick)
	#regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) kicked player (\d+) \(Reason: (.*)\)")
	regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) kicked player (.+) \(Reason: (.*)\)")
	regex_parse = re.search(regex_capture, message)
	if not regex_parse:
		print('Failed to parse the regex for message!!!')
		return "ERROR","ERROR","ERROR"
	admin = regex_parse[1]
	playfabid = regex_parse[2]
	try:
		reason = regex_parse[3]
	except IndexError:
		reason = 'None given'
	return admin,playfabid,reason

def parse_messageMute(message):
	#LogMordhauPlayerController: Display: Admin dan from dans duels (FFBCF4758910B074) muted player D0904EAFADF55768 (Duration: 1)
	#regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) muted player (\d+) \(Duration: (\d+)\)")
	regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) muted player (.+) \(Duration: (\d+)\)")
	regex_parse = re.search(regex_capture, message)
	if not regex_parse:
		print('Failed to parse the regex for message!!!')
		return "ERROR","ERROR","ERROR"
	admin = regex_parse[1]
	playfabid = regex_parse[2]
	duration = regex_parse[3]
	return admin,playfabid,duration

def parse_messageUnmute(message):
	#LogMordhauPlayerController: Display: Admin dan from dans duels (FFBCF4758910B074) unmuted player D0904EAFADF55768
	#regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) unbanned player (\d+)")
	regex_capture = re.compile("LogMordhauPlayerController: Display: Admin (.+) unmuted player (.+)")
	regex_parse = re.search(regex_capture, message)
	if not regex_parse:
		print('Failed to parse the regex for message!!!')
		return "ERROR","ERROR"
	admin = regex_parse[1]
	playfabid = regex_parse[2]
	return admin,playfabid

def parse_messageAddAdmin(message):
	#LogMordhauGameSession: Added PlayFab ID D0904EAFADF55768 to admins
	#regex_capture = re.compile("LogMordhauGameSession: Added Steam ID (\d+) to admins")
	regex_capture = re.compile("LogMordhauGameSession: Added PlayFab ID (.+) to admins")
	regex_parse = re.search(regex_capture, message)
	if not regex_parse:
		print('Failed to parse the regex for message!!!')
		return "ERROR"
	playfabid = regex_parse[1]
	return playfabid

def parse_messageRemoveAdmin(message):
	#LogMordhauGameSession: Removed PlayFab ID D0904EAFADF55768 from admins
	#regex_capture = re.compile("LogMordhauGameSession: Removed Steam ID (\d+) from admins")
	regex_capture = re.compile("LogMordhauGameSession: Removed PlayFab ID (.+) from admins")
	regex_parse = re.search(regex_capture, message)
	if not regex_parse:
		print('Failed to parse the regex for message!!!')
		return "ERROR"
	playfabid = regex_parse[1]
	return playfabid

def get_playerhistory(server,playfabid):
	global playerhistoryData

	now = datetime.datetime.now()
	year = now.year
	month = now.month

	try:
		playerhistoryData = util.load_data(year,month,"playerhistory")
	except:
		#traceback.print_exc()
		print("Some kind of load error")
		playerhistoryData = {}

	#print(playerhistoryData)

	if str(server) in playerhistoryData:
		#print("Server has old data")
		if str(playfabid) in playerhistoryData[str(server)]:
			print("Returning old history")
			return playerhistoryData[str(server)][str(playfabid)]["history"]

	#print("No old data found")
	return None

def update_playerhistory(server,playfabid,history):
	global playerhistoryData

	now = datetime.datetime.now()
	year = now.year
	month = now.month

	if not str(server) in playerhistoryData:
		playerhistoryData[str(server)] = {}
	if not str(playfabid) in playerhistoryData[str(server)]:
		playerhistoryData[str(server)][str(playfabid)] = {}
		playerhistoryData[str(server)][str(playfabid)]["history"] = []

	playerhistoryData[str(server)][str(playfabid)]["history"] = history

	#print("Going to save: "+str(playerhistoryData))

	util.save_data(year,month,playerhistoryData, "playerhistory")

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
			past_offenses = '\n**------------------**\n' + '\n------------------\n'.join([
				(
					m['Type'] + ' by ' + m['BanAdmin'] +
					'\nDate: ' + m['BanDate'] +
					'\nReason: ' + m['BanReason'] +
					'\nDuration: ' + str(m['BanDuration']) + ' minutes'
				)
				for m in self.ban_message['BanHistory']
			]) + '\n**------------------**'
		print('Sending message: ', self.ban_message, 'to channel:', self.channel_id)
		if self.ban_message['Type'] == "BAN":
			message = f'''**BAN REPORT**:
		**Server**: {self.ban_message['Server']}
		**PlayFabID**: {self.ban_message['PlayFabID']}
		**Reason**: {self.ban_message['Reason']}
		**Admin**: {self.ban_message['BanAdmin']}
		**Duration**: {self.ban_message['BanDuration']} minutes

	**Previous and Current Offenses**: {past_offenses}
			'''
		elif self.ban_message['Type'] == "UNBAN":
			message = f'''**UNBAN REPORT**:
		**Server**: {self.ban_message['Server']}
		**PlayFabID**: {self.ban_message['PlayFabID']}
		**Admin**: {self.ban_message['UnbanAdmin']}

	**Previous and Current Offenses**: {past_offenses}
			'''
		elif self.ban_message['Type'] == "KICK":
			message = f'''**KICK REPORT**:
		**Server**: {self.ban_message['Server']}
		**PlayFabID**: {self.ban_message['PlayFabID']}
		**Reason**: {self.ban_message['Reason']}
		**Admin**: {self.ban_message['KickAdmin']}

	**Previous and Current Offenses**: {past_offenses}
			'''
		elif self.ban_message['Type'] == "MUTE":
			message = f'''**MUTE REPORT**:
		**Server**: {self.ban_message['Server']}
		**PlayFabID**: {self.ban_message['PlayFabID']}
		**Admin**: {self.ban_message['BanAdmin']}
		**Duration**: {self.ban_message['BanDuration']} minutes

	**Previous and Current Offenses**: {past_offenses}
			'''
		elif self.ban_message['Type'] == "UNMUTE":
			message = f'''**UNMUTE REPORT**:
		**Server**: {self.ban_message['Server']}
		**PlayFabID**: {self.ban_message['PlayFabID']}
		**Admin**: {self.ban_message['UnmuteAdmin']}

	**Previous and Current Offenses**: {past_offenses}
			'''
		elif self.ban_message['Type'] == "ADDADMIN":
			message = f'''**ADDADMIN REPORT**:
		**Server**: {self.ban_message['Server']}
		**PlayFabID**: {self.ban_message['PlayFabID']}

	**Previous and Current Offenses**: {past_offenses}
			'''
		elif self.ban_message['Type'] == "REMOVEADMIN":
			message = f'''**REMOVEADMIN REPORT**:
		**Server**: {self.ban_message['Server']}
		**PlayFabID**: {self.ban_message['PlayFabID']}

	**Previous and Current Offenses**: {past_offenses}
			'''
		embed = discord.Embed(description=message)

		await channel.send(embed=embed)
		print('Message sent, closing client.')
		await self.close()

readLogfilesLoop()
