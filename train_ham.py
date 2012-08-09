"""
A rudimentary way to train additional ham into our pickle file.

Example usage:

$ python train_spam.py /path/to/spam.pkl
blah blah blah^D
"""
import sys
from ConfigParser import SafeConfigParser as ConfigParser, \
        NoSectionError, NoOptionError
from spambayes.storage import PickledClassifier


config = ConfigParser()
with open("/etc/email_gateway.cfg") as fp:
    config.readfp(fp)


def main():
    pickle_filename = sys.argv[-1]
    bayes = PickledClassifier(pickle_filename)
    message = sys.stdin.readlines()
    bayes.learn(message, False)
    bayes.store()


if __name__ == '__main__':
    main()
