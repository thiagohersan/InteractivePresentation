# -*- coding: utf-8 -*-

import sys, getopt, re
from time import time, sleep, strptime, strftime, localtime, gmtime
from calendar import timegm
from threading import Thread
from Queue import Queue
from cPickle import dump, load
from OSC import OSCClient, OSCMessage, OSCClientError, OSCServer, getUrlStr
from nltk import pos_tag, word_tokenize
from twython import TwythonStreamer
from twilio.rest import TwilioRestClient

## What to search for
SEARCH_TERMS = ["@nottoopublic", "#nottoopublic"]
PHONE_NUMBER = "+15105647823"

class TwitterStreamReceiver(TwythonStreamer):
    def __init__(self, *args, **kwargs):
        super(TwitterStreamReceiver, self).__init__(*args, **kwargs)
        self.tweetQ = Queue()
    def on_success(self, data):
        ## no re-tweets
        if ('text' in data):
            self.tweetQ.put(data['text'].encode('utf-8'))
            print "received %s" % (data['text'].encode('utf-8'))
    def on_error(self, status_code, data):
        print status_code
    def empty(self):
        return self.tweetQ.empty()
    def get(self):
        return self.tweetQ.get()

def oscSubscribeHandler(addr, tags, args, source):
    ip = getUrlStr(source).split(":")[0]
    port = int(args[0])
    print "subscribing %s:%s" % (ip,port)
    myOscSubscribers[(ip,port)] = (ip,port)

def setup():
    global lastTwitterCheck, myTwitterStream, streamThread
    global lastSmsCheck, mySmsClient, newestSmsSeconds
    global myOscSubscribers, myOscServer, oscThread, myOscClient
    global logFile
    secrets = {}
    myOscSubscribers = {}
    lastTwitterCheck = time()
    lastSmsCheck = time()
    newestSmsSeconds = timegm(gmtime())

    ## read secrets from file
    inFile = open('oauth.txt', 'r')
    for line in inFile:
        (k,v) = line.split()
        secrets[k] = v

    ## start Twitter stream reader
    myTwitterStream = TwitterStreamReceiver(app_key = secrets['CONSUMER_KEY'],
                                            app_secret = secrets['CONSUMER_SECRET'],
                                            oauth_token = secrets['ACCESS_TOKEN'],
                                            oauth_token_secret = secrets['ACCESS_SECRET'])
    streamThread = Thread(target=myTwitterStream.statuses.filter, kwargs={'track':','.join(SEARCH_TERMS)})
    streamThread.start()

    ## start Twilio client
    mySmsClient = TwilioRestClient(account=secrets['ACCOUNT_SID'],
                                   token=secrets['AUTH_TOKEN'])

    myOscClient = OSCClient()
    myOscServer = OSCServer(('127.0.0.1', 8888))
    myOscServer.addMsgHandler('/NotTooPublic/call', oscSubscribeHandler)
    myOscServer.addMsgHandler('default', lambda addr, tags, args, source:None)
    oscThread = Thread(target=myOscServer.serve_forever)
    oscThread.start()

    ## open new file for writing log
    logFile = open("data/"+strftime("%Y%m%d-%H%M%S", localtime())+".log", "a")

def cleanTagAndSendText(text):
    ## removes punctuation
    text = re.sub(r'[.,;:!?*/+=\-&%^/\\_$~()<>{}\[\]]', ' ', text)
    ## removes some bad words
    text = re.sub(r'(f *u *c *k)', 'tuck', text)
    text = re.sub(r'(s *h *i *t)', 'isht', text)
    text = re.sub(r'(c *o *c *k)', 'dock', text)
    text = re.sub(r'(d *i *c *k)', 'wick', text)
    text = re.sub(r'(c *u *n *t)', 'grunt', text)
    text = re.sub(r'(p *u *s *s *y)', 'juicy', text)
    text = re.sub(r'(b *i *t *c *h)', 'itch', text)
    text = re.sub(r'(a *s *s)', 'grass', text)
    ## replaces double-spaces with single space
    text = re.sub(r'( +)', ' ', text)

    taggedText = pos_tag(text.split())
    for (word,tag) in taggedText:
        print "(%s:%s)" % (word,tag),
    print " "

    ## log
    logFile.write(strftime("%Y%m%d-%H%M%S", localtime())+"***"+text+"\n")
    logFile.flush()

    ## forward to all subscribers
    msg = OSCMessage()
    msg.setAddress("/NotTooPublic/response")
    msg.append(" ".join([str(i[0]) for i in taggedText]))
    msg.append(" ".join([str(i[1]) for i in taggedText]))

    delQ = Queue()
    for (ip,port) in myOscSubscribers:
        try:
            myOscClient.connect((ip, port))
            myOscClient.sendto(msg, (ip, port))
            myOscClient.connect((ip, port))
        except OSCClientError:
            print "no connection to %s : %s, can't send message" % (ip, port)
            delQ.put((ip,port))

    while not delQ.empty():
        del myOscSubscribers[delQ.get()]


def loop():
    global lastTwitterCheck, myTwitterStream, streamThread, myOscSubscribers
    global lastSmsCheck, mySmsClient, newestSmsSeconds
    ## check twitter queue
    if((time()-lastTwitterCheck > 5) and (not myTwitterStream.empty())):
        tweet = myTwitterStream.get().lower()
        ## removes re-tweet
        tweet = re.sub(r'(^[rR][tT] )', '', tweet)
        ## removes hashtags, arrobas and links
        tweet = re.sub(r'(#\S+)|(@\S+)|(http://\S+)', '', tweet)
        ## clean, tag and send text
        cleanTagAndSendText(tweet)
        lastTwitterCheck = time()

    ## check sms
    if(time()-lastSmsCheck > 5):
        smss = mySmsClient.messages.list(to=PHONE_NUMBER,
                                         after=strftime("%a, %d %b %Y %H:%M:%S", gmtime(newestSmsSeconds+1)))
        for sms in smss:
            smsSeconds = timegm(strptime(sms.date_sent, "%a, %d %b %Y %H:%M:%S +0000"))
            if (smsSeconds > newestSmsSeconds):
                newestSmsSeconds = smsSeconds
            print "sms: %s" % (sms.body)
            body = str(sms.body).lower()
            ## clean, tag and send text
            cleanTagAndSendText(body)
        lastSmsCheck = time()

if __name__=="__main__":
    setup()

    try:
        while(True):
            ## keep it from looping faster than ~60 times per second
            loopStart = time()
            loop()
            loopTime = time()-loopStart
            if (loopTime < 0.016):
                sleep(0.016 - loopTime)
    except KeyboardInterrupt :
        logFile.close()
        myTwitterStream.disconnect()
        myOscServer.close()
        streamThread.join()
        oscThread.join()
        sys.exit(0)
