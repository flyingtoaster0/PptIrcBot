#!/usr/bin/env python2.7

#IRC and yaml reading bot

import irc.client
import sys
import logging
import re
import yaml
import os
import time
from threading import Thread
import traceback
from Queue import Queue
from subprocess import call
from word_filter import WordFilter

#Setting the global logger to debug gets all sorts of irc debugging
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
TasbotEspeakEnable = settings.get('ScreenPlayFileName', True)


def write_to_pipe(write_to_pipe, msg):
    """Utility function to write a message to a pipe.
       First add a newline if it doesn't have one.
       Then write the message and flush the pipe.
    """
    if not msg.endswith('\n'):
        msg += '\n'
    write_to_pipe.write(msg)
    write_to_pipe.flush()


class ReplayTextThread(Thread):
    """This thread grabs strings off the queue and writes them to the
       pipe that the replay script should be reading from.
       This ensures thread safety between the multiple threads that need
       to write to that pipe.
       It will never stop so do not wait for it!
    """
    def __init__(self, replay_queue):
        super(ReplayTextThread, self).__init__()

        self.replay_queue = replay_queue

    def run(self):
        if not os.path.exists(ReplayPipeName):
            os.mkfifo(ReplayPipeName)
        writepipe = open(ReplayPipeName, 'w')
        while True:
            msg = self.replay_queue.get()
            write_to_pipe(writepipe, msg)


class ScreenPlayThread(Thread):
    def __init__(self, ircBot):
        super(ScreenPlayThread, self).__init__()

        self.ircBot = ircBot
        self.script = []
        self.read_screenplay(ScreenPlayFileName)

    def read_screenplay(self, filename):
        if TasbotPipeEnable:
            if not os.path.exists(TasbotPipeName):
                os.mkfifo(TasbotPipeName)

        with open(filename) as rawScript:
            for line in rawScript:
                #Commented lines with #
                if re.match("\s*#", line):
                    continue
                m = re.match(r'(?P<delay>\S+)\s+(?P<speaker>\S+?):?\s+(?P<text>.+)', line)
                if not m:
                    continue
                delay = float(m.group('delay'))
                speaker = m.group('speaker').lower()
                text = m.group('text')
                self.script.append((delay, speaker, text))
        print 'Loaded script with {} lines'.format(len(self.script))

    def run(self):
        try:
            if TasbotPipeEnable:
                tasbotpipe = open(TasbotPipeName, 'w')
            for delay, speaker, text in self.script:
                time.sleep(delay)
                debug("%s says %s" % (speaker, text))
                if speaker == 'red':
                    self.ircBot.replayQueue.put("<red>:" + text)
                    self.ircBot.sendMessage(text)
                if speaker == 'tasbot':
                    if TasbotPipeEnable:
                        write_to_pipe(tasbotpipe, text)
                    if TasbotEspeakEnable:
                        call(['espeak', '-p42', '-s140', '-m', text])
                        # call("espeak -p42 -s140 -m --stdout " + text)
                        #call(["espeak -p42 -s140 -m --stdout " + text + " | aplay -D 'hw'"])
                                                                                                
                if speaker == 'tasbott':
                    msg = u'TASBot says: {}'.format(text)
                    self.ircBot.sendMessage(msg)
        except:
            traceback.print_exc()
            sys.exit(1)


class PptIrcBot(irc.client.SimpleIRCClient):
    def __init__(self):
        irc.client.SimpleIRCClient.__init__(self)
        #Precompiled tokenizing regex
        self.splitter = re.compile(r'[^\w]+')
        self.replayQueue = Queue()

        self.word_filter = WordFilter()
        self.word_filter.set_blacklist('bad-words.txt')

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
            # self.screenPlayThread = ScreenPlayThread(self)
            self.replayThread = ReplayTextThread(self.replayQueue)
            print 'starting replay thread'
            self.replayThread.start()
            # print 'starting screenplay thread'
            # self.screenPlayThread.start()

        # self.screenPlayThread = ScreenPlayThread(self)
        # self.replayThread = ReplayTextThread(self.replayQueue)
        # print 'starting replay thread'
        # self.replayThread.start()
        # print 'starting screenplay thread'
        # self.screenPlayThread.start()

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
        text = sender + ":" + text
        text_lower = text.lower()

        words, naughty_message = self.word_filter.filter(text_lower)

        if naughty_message:
            self.notify_naughty_message(sender, naughty_message)
            return

        words = self.splitter.split(text_lower)
        words = map(lambda x: x.lower(), words)

        print(words)



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

    c = PptIrcBot()

    try:
        c.connect(server, port, IrcNick, password=IrcPassword)
    except irc.client.ServerConnectionError as x:
        print(x)
        sys.exit(1)
    c.start()

if __name__ == "__main__":
    main()
