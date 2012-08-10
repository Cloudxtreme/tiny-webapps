#!/usr/bin/env python2.6

import logging
import os
import smtplib
import re
import urlparse
from cStringIO import StringIO
from email.mime.text import MIMEText
from ConfigParser import SafeConfigParser as ConfigParser, \
        NoSectionError, NoOptionError
from spambayes.storage import PickledClassifier

log = logging.getLogger("email_gateway")
handler = logging.FileHandler("/var/log/webapps/email_gateway.log")
log.addHandler(handler)
log.setLevel(logging.DEBUG)


config = ConfigParser()
with open("/etc/email_gateway.cfg") as fp:
    config.readfp(fp)


def send_message(text, subject, to, from_email):
    msg = MIMEText(text.getvalue(), "plain")

    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to

    p = os.popen("/usr/sbin/sendmail -t", "w")
    p.write(msg.as_string())
    p.close()


def looks_like_spam(message, config, section):
    log.info("Checking message for spam...")
    log.debug(message)
    pickle_filename = config.get(section, 'spam.pickle_file')
    min_spam_prob = config.getfloat(section, 'spam.min_spam_prob') or 0.90

    log.debug("Loading pickle from %s", pickle_filename)
    bayes = PickledClassifier(pickle_filename)

    spamprob = bayes.chi2_spamprob(message)

    if spamprob >= min_spam_prob:
        log.debug("spamprob %s >= %s, probably spam", spamprob, min_spam_prob)
        return True

    log.debug("spamprob %s <= %s, probably not spam", spamprob, min_spam_prob)
    return False


def email_app(environ, start_response):
    ignored_fields = []
    useful_fields = []
    form_key = None
    message_buffer = StringIO()

    context = {}
    to_check = []

    fields = urlparse.parse_qsl(environ["wsgi.input"].read())
    for key, value in fields:
        if key == "mailer.form-key":
            form_key = value
        elif key == "mailer.redirect":
            context["redirect"] = value
        elif key == "mailer.subject":
            context["subject"] = value
        elif key == "mailer.message":
            context["message"] = value
        elif key == "mailer.fields.ignore":
            ignored_fields = value.split(",")
        else:
            to_check.append(value)
            useful_fields.append((key, value))

    try:
        my_config = dict(config.items(form_key))
        site_matcher = re.compile(my_config["site"])
    except NoSectionError:
        start_response('403 Forbidden', [('Content-Type', 'text/plain')])
        return "Invalid form key!"

    if not site_matcher.match(environ["HTTP_REFERER"]):
        start_response('403 Forbidden', [('Content-Type', 'text/plain')])
        return "Invalid send!"

    try:
        if config.getboolean(form_key, 'spam.check') \
                and looks_like_spam(" ".join(to_check), config, form_key):
            start_response('403 Forbidden', [('Content-Type', 'text/plain')])
            return "I don't like SPAM!"
    except NoOptionError:
        pass

    useful_fields = ["{0}: {1}".format(*f)
                     for f in useful_fields
                     if f[0] not in ignored_fields]

    message_buffer.write(context.get("message", my_config["message"]))
    message_buffer.write("\n\n")
    message_buffer.write("\n".join(useful_fields))

    send_message(message_buffer,
        context.get("subject", my_config["subject"]),
        my_config["to"],
        my_config["from"])

    redirect_location = context.get("redirect", my_config["redirect"])
    start_response('302 Found', [('Location', redirect_location)])

    return ""


if __name__ == "__main__":
    from flup.server.fcgi_fork import WSGIServer
    WSGIServer(email_app, maxSpare=1).run()
