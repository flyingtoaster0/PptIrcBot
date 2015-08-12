from threading import Thread


class PipeThread(Thread):
    def __init__(self):
        super(PipeThread, self).__init__()

    def write_to_pipe(self, write_to_pipe, message):
        """Utility function to write a message to a pipe.
           First add a newline if it doesn't have one.
           Then write the message and flush the pipe.
        """
        line = message['sender'] + ":" + message['text']

        if not line.endswith('\n'):
            line += '\n'
        write_to_pipe.write(line)
        write_to_pipe.flush()

    def put(self, message):
        """A function to be overriden by subclasses.
            Added to allow input while keeping queues
            encapsulated in the threads themselves.
        """
        pass
