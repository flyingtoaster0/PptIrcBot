import re
from threading import Thread
from time import sleep
from Queue import Queue
from pipe_thread import PipeThread


class WordVoter(PipeThread):
    def get_file(self):
        file = open("words", "r")
        return file

    def get_word_list(self):
        file = self.get_file()
        line_list = file.read().splitlines()

        word_list = []
        for line in line_list:
            for word in self.splitter.split(line):
                if word:
                    word_list.append(word)

        file.close()

        return word_list

    def get_word_count(self):
        word_list = self.get_word_list()

        word_count = dict()

        for word in word_list:
            word_count[word] = 0

        for word in word_list:
            word_count[word] += 1

        return word_count

    def get_most_common_word(self):
        return self.get_most_common_word_and_amount()[0]

    def get_most_common_word_and_amount(self):
        if self.mode == "file":
            self.word_dict = self.get_word_count()

        most_occurrences = 0
        most_common_word = ""

        for word, count in self.word_dict.iteritems():
            if word and count > most_occurrences:
                most_common_word = word
                most_occurrences = count

        return most_common_word, most_occurrences

    def add_to_word_dict(self, text):

        words = self.splitter.split(text)
        words = map(lambda x: x.lower(), words)

        if not self.voting_thread.locked:
            for word in words:

                if self.word_filter:
                    word = self.word_filter.filter(word)

                if word in self.word_dict:
                    self.word_dict[word] += 1
                else:
                    self.word_dict[word] = 1

    def clear_word_dict(self):
        self.word_dict.clear()

    def start_thread(self):
        self.voting_thread.start()

    def put(self, message):
        self.queue.put(message)

    def run(self):
        self.start_thread()
        while True:
            message = self.queue.get()
            text = message['text']
            self.add_to_word_dict(text)

    def __init__(self, mode, duration, word_filter=None):
        super(WordVoter, self).__init__()
        self.mode = mode
        self.word_dict = dict()
        self.splitter = re.compile(r'[^\w]+')
        self.word_filter = word_filter
        self.voting_thread = VotingThread(self, duration)
        self.queue = Queue()


class VotingThread(Thread):
    def __init__(self, word_voter, duration):
        super(VotingThread, self).__init__()
        self.word_voter = word_voter
        self.duration = duration
        self.locked = False

    def run(self):
        while True:

            # Lock thread to ignore input during calculations
            self.locked = True
            most_common_word = self.word_voter.get_most_common_word_and_amount()
            self.word_voter.clear_word_dict()
            self.locked = False

            print(most_common_word)
            sleep(self.duration)

    # TODO actually write to a pipe when flushing the votes
    def write_to_pipe(self, write_to_pipe, message):
        """Utility function to write a message to a pipe.
           First add a newline if it doesn't have one.
           Then write the message and flush the pipe.
        """
        line = message['text']

        if not line.endswith('\n'):
            line += '\n'
        write_to_pipe.write(line)
        write_to_pipe.flush()