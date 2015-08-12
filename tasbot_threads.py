from subprocess import call
import os
import time
import traceback
import re
import sys
from Queue import Queue
from pipe_thread import PipeThread


class ReplayTextThread(PipeThread):
    """This thread grabs strings off the queue and writes them to the
       pipe that the replay script should be reading from.
       This ensures thread safety between the multiple threads that need
       to write to that pipe.
       It will never stop so do not wait for it!
    """
    def __init__(self, replay_pipe_name):
        super(ReplayTextThread, self).__init__()

        self.replay_queue = Queue()
        self.replay_pipe_name = replay_pipe_name

    def put(self, msg):
        self.replay_queue.put(msg)

    def run(self):
        print 'starting replay thread'
        if not os.path.exists(self.replay_pipe_name):
            os.mkfifo(self.replay_pipe_name)
        writepipe = open(self.replay_pipe_name, 'w')
        while True:
            msg = self.replay_queue.get()
            self.write_to_pipe(writepipe, msg)


class ScreenPlayThread(PipeThread):
    def __init__(self, ircBot, screenplay_filename, enable_tasbot_pipe, tasbot_pipe_name, espeak_enable):
        super(ScreenPlayThread, self).__init__()

        self.ircBot = ircBot
        self.script = []
        self.enable_tasbot_pipe = enable_tasbot_pipe
        self.tasbot_pipe_name = tasbot_pipe_name
        self.espeak_enable = espeak_enable
        self.read_screenplay(screenplay_filename)

    def read_screenplay(self, filename):
        if self.enable_tasbot_pipe:
            if not os.path.exists(self.tasbot_pipe_name):
                os.mkfifo(self.tasbot_pipe_name)

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
            if self.enable_tasbot_pipe:
                tasbotpipe = open(self.tasbot_pipe_name, 'w')
            for delay, speaker, text in self.script:
                message = {'sender': speaker, 'text': text}
                time.sleep(delay)
                # debug("%s says %s" % (speaker, text))
                if speaker == 'red':
                    self.ircBot.put_message_to_threads(message)
                    self.ircBot.sendMessage(message['text'])
                if speaker == 'tasbot':
                    if self.enable_tasbot_pipe:
                        self.write_to_pipe(tasbotpipe, message)
                    if self.espeak_enable:
                        call(['espeak', '-p42', '-s140', '-m', text])
                        # call("espeak -p42 -s140 -m --stdout " + text)
                        #call(["espeak -p42 -s140 -m --stdout " + text + " | aplay -D 'hw'"])
                                                                                                
                if speaker == 'tasbott':
                    msg = u'TASBot says: {}'.format(text)
                    self.ircBot.sendMessage(msg)
        except:
            traceback.print_exc()
            sys.exit(1)