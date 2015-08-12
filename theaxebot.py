#!/usr/bin/env python2.7

#IRC and yaml reading bot

import irc.client
import sys
import logging
import re
import yaml
from word_filter import WordFilter
from word_voter import WordVoter
from tasbot_threads import ReplayTextThread, ScreenPlayThread

# Setting the global logger to debug gets all sorts of irc debugging
logging.getLogger().setLevel(logging.WARNING)


def debug(msg):
    try:
        print msg
    except UnicodeEncodeError:
        pass


settingsFile = open("settings.yaml")
settings = yaml.load(settingsFile)
settingsFile.close()

IrcServer = settings.get('IrcServer', 'irc.freenode.net')
IrcNick = settings.get('IrcNick', 'TheAxeBot')
IrcPassword = settings.get('IrcPassword', None)
IrcChannel = settings.get('IrcChannel', '#lsnes')

ReplayPipeName = settings.get('ReplayPipeName', 'replay_pipe')
TasbotPipeName = settings.get('TasbotPipeName', 'tasbot_pipe')
ScreenPlayFileName = settings.get('ScreenPlayFileName', 'screenplay.txt')

TasbotPipeEnable = settings.get('TasbotPipeEnable', False)
TasbotEspeakEnable = settings.get('TasbotEspeakEnable', True)

EnableReplayThread = settings.get('EnableReplayThread', False)
EnableScreenplayThread = settings.get('EnableScreenplayThread', False)
EnableVotingThread = settings.get('EnableVotingThread', False)
VotingWhitelist = settings.get('VotingWhitelist', '')
VotingDuration = settings.get('VotingDuration', 30)


class PptIrcBot(irc.client.SimpleIRCClient):
    def __init__(self):
        irc.client.SimpleIRCClient.__init__(self)
        #Precompiled tokenizing regex
        self.splitter = re.compile(r'[^\w]+')

        self.word_filter = WordFilter()
        self.word_filter.set_blacklist('bad-words.txt')
        self.threads = []

    def sendMessage(self, msg):
        # We don't want this showing up in chat:
        msg = re.sub(r'\s*ShiftPalette\s*', ' ', msg)
        if msg.isspace():
            # This message only contained ShiftPalette.
            return
        self.connection.privmsg(IrcChannel, msg)

    def on_welcome(self, connection, event):
        print 'joining', IrcChannel
        connection.join(IrcChannel)

    def on_join(self, connection, event):
        """Fires on joining the channel.
           This is when the action starts.
        """
        if (event.source.find(IrcNick) != -1):
            print "I joined!"

            for thread in self.threads:
                thread.start()


    def on_disconnect(self, connection, event):
        sys.exit(0)

    def notify_naughty_message(self, sender, reason):
        # Be sure to get rid of the naughty message before the event!
        # An easy way is to just make this function a pass
        pass
        print("Naughty %s (%s)" % (sender, reason))

    def on_pubmsg(self, connection, event):
        # debug("pubmsg from %s: %s" % (event.source, event.arguments[0]))
        # debug("%s: %s" % (event.source, event.arguments[0]))
        text = event.arguments[0]
        sender = event.source.split('!')[0]
        text_lower = text.lower()
        text_with_sender = sender + ":" + text

        message_dict = {'sender': sender, 'text': text}

        text_lower, naughty_message = self.word_filter.filter(text_lower)

        if naughty_message:
            self.notify_naughty_message(sender, naughty_message)
            return

        self.put_message_to_threads(message_dict)
        print(text_with_sender)

    def put_message_to_threads(self, message):
        for thread in self.threads:
            thread.put(message)

    def set_threads(self, threads):
        self.threads = threads


def get_threads(irc_client):
    threads = []

    if EnableReplayThread:
        replay_thread = ReplayTextThread(ReplayPipeName)
        threads.append(replay_thread)
    if EnableScreenplayThread:
        screenplay_thread = ScreenPlayThread(irc_client, ScreenPlayFileName, TasbotPipeEnable, TasbotPipeName, TasbotEspeakEnable)
        threads.append(screenplay_thread)
    if EnableVotingThread:
        if VotingWhitelist:
            whitelist_filter = WordFilter()
            whitelist_filter.set_whitelist(VotingWhitelist)
            word_voter_thread = WordVoter("nofile", VotingDuration, whitelist_filter)
            threads.append(word_voter_thread)
        else:
            threads.append(WordVoter("nofile", VotingDuration))

    return threads


def main():

    if ':' in IrcServer:
        try:
            server, port = IrcServer.split(":")
            port = int(port)
        except Exception:
            print("Error: Bad server:port specified")
            sys.exit(1)
    else:
        server = IrcServer
        port = 6667

    irc_client = PptIrcBot()

    threads = get_threads(irc_client)

    irc_client.set_threads(threads)

    try:
        irc_client.connect(server, port, IrcNick, password=IrcPassword)
    except irc.client.ServerConnectionError as x:
        print(x)
        sys.exit(1)
    irc_client.start()

if __name__ == "__main__":
    main()
