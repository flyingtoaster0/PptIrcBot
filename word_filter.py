import re

class WordFilter:

    def set_blacklist(self, filename):
        self.blacklist_words = self.get_blacklist_from_file(filename)

    def set_whitelist(self, filename):
        self.whitelist_words = self.get_whitelist_from_file(filename)

    def get_blacklist_from_file(self, filename):
        blacklist_words_file = open(filename)
        blacklist_word_strings = set([word.strip().lower() for word in blacklist_words_file.readlines()])
        blacklist_words_file.close()

        if '' in blacklist_word_strings:
            blacklist_word_strings.remove('')

        blacklist_regex_strings = []

        for word in blacklist_word_strings:
            word = re.sub(r'[sz]', '[s5z2$]', word)
            word = re.sub(r'a', '[a4]', word)
            word = re.sub(r'e', '[e3]', word)
            word = re.sub(r'i', '[i1]', word)
            word = re.sub(r'l', '[l1]', word)
            word = re.sub(r'o', '[o0]', word)
            word = re.sub(r't', '[t7]', word)
            word = re.sub(r'g', '[g6]', word)
            word = re.sub(r'b', '[b8]', word)
            word = re.sub(r'f', '(f|ph)', word)
            word = re.sub(r'(c|k)', '[ck]', word)
            blacklist_regex_strings.append(word)

        blacklist = []

        for word in blacklist_regex_strings:
            blacklist.append(re.compile(word))

        return blacklist

    def get_whitelist_from_file(self, filename):
        whitelist_words_file = open(filename)
        whitelist_words_strings = set([word.strip().lower() for word in whitelist_words_file.readlines()])
        whitelist_words_file.close()

        return whitelist_words_strings

    def filter(self, word):
        if self.whitelist_words:
            if word in self.whitelist_words:
                return word
            else:
                return '', "not in whitelist"
        else:
            for blacklist_regex in self.blacklist_words:
                if blacklist_regex.search(word.lower()):
                    return '', "bad word: " + blacklist_regex.pattern

        #Check for non-ascii characters
        try:
            word.decode('ascii')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # self.naughtyMessage(sender, "not ascii")
            return '', "not ascii"
        except Exception:
            return '', "not ascii"

        if self.urlregex.search(word):
            # self.naughtyMessage(sender, "url")
            return '', "url"

        if self.otherbadregex.search(word):
            # self.naughtyMessage(sender, "url-like")
            return '', "url-like"

        #We probably also want to filter some typically non-printing ascii chars:
        #[18:12] <@Ilari> Also, one might want to drop character codes 0-31 and 127. And then map the icons to some of those.
        if any(c in self.nonPrintingChars for c in word):
            # self.naughtyMessage(sender, "non-printing chars")
            return '', "non-printing chars"

        return word, None

    def filter_array(self, word_array):
        naughty_message = None
        for word in word_array:
            naughty_message = self.filter(word)[1]
            if naughty_message:
                break

        filtered_array = [word for word in word_array if self.filter(word)]

        return filtered_array, naughty_message

    def __init__(self):
        self.blacklist_words = []
        self.whitelist_words = []
        self.nonPrintingChars = set([chr(i) for i in xrange(32)])
        self.nonPrintingChars.add(127)
        self.urlregex = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.otherbadregex = re.compile(r'\.((com)|(org)|(net))')

if __name__ == "__main__":
    filter = WordFilter()
    filter.set_blacklist('bad-words.txt')
    print(filter.filter_array(["penis", "test"]))
    print(filter.filter("http://www.google.ca"))
    print(filter.filter("www.google.com"))
    print(filter.filter("hello!!"))
    print(filter.filter_array(["www.google.com", "test"]))
