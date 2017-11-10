# -*- coding: utf-8 -*-

import sys, re
import json
from time import time, sleep
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue
from OSC import OSCClient, OSCMessage, OSCClientError
from twython import TwythonStreamer
from twilio.rest import Client
import pytz
import codecs

utc=pytz.UTC

DISPLAY_ADDR = '127.0.0.1'
DISPLAY_PORT = 8888

class TwitterStreamReceiver(TwythonStreamer):
    def __init__(self, *args, **kwargs):
        super(TwitterStreamReceiver, self).__init__(*args, **kwargs)
        self.tweetQ = Queue()
    def on_success(self, data):
        if ('text' in data):
            self.tweetQ.put(data['text'].encode('utf-8'))
            print("received %s" % (data['text'].encode('utf-8')))
    def on_error(self, status_code, data):
        print(status_code)
    def empty(self):
        return self.tweetQ.empty()
    def get(self):
        return self.tweetQ.get()

def setup():
    global lastTwitterCheck, myTwitterStream, streamThread
    global lastSmsCheck, mySmsClient, newestSmsSeconds
    global myOscClient
    global logFile
    global PHONE_NUMBER
    lastTwitterCheck = time()
    lastSmsCheck = time()
    newestSmsSeconds = datetime.now(utc)

    ## read secrets from file
    with open('secrets.json') as dataFile:
        secrets = json.load(dataFile)

    SEARCH_TERMS = secrets["search_terms"]
    PHONE_NUMBER = secrets["phone_number"]
    ## start Twitter stream reader
    myTwitterStream = TwitterStreamReceiver(app_key = secrets["twitter"]['CONSUMER_KEY'],
                                            app_secret = secrets["twitter"]['CONSUMER_SECRET'],
                                            oauth_token = secrets["twitter"]['ACCESS_TOKEN'],
                                            oauth_token_secret = secrets["twitter"]['ACCESS_SECRET'])
    streamThread = Thread(target=myTwitterStream.statuses.filter, kwargs={'track':','.join(SEARCH_TERMS)})
    streamThread.daemon = True
    streamThread.start()

    ## start Twilio client
    mySmsClient = Client(secrets["twilio"]['ACCOUNT_SID'],secrets["twilio"]['AUTH_TOKEN'])

    myOscClient = OSCClient()

    ## open new file for writing log
    now = datetime.now(utc)
    logFile = codecs.open("logs/" + now.isoformat() + ".log", "a", "utf-8")

def cleanTagAndSendText(text):
    ## removes punctuation
    text = re.sub(r'[.,;:!?*/+=\-&%^/\\_$~()<>{}\[\]]', ' ', text)
    ## replaces double-spaces with single space
    text = re.sub(r'( +)', ' ', text)
    ## log
    now = datetime.now(utc)
    logFile.write(now.isoformat() + "  ***  "+ text +"\n")
    logFile.flush()

    ## forward to all subscribers
    msg = OSCMessage()
    msg.setAddress("/airmsg/response")
    msg.append(text.encode('utf-8'))

    try:
        myOscClient.connect((DISPLAY_ADDR, DISPLAY_PORT))
        myOscClient.sendto(msg, (DISPLAY_ADDR, DISPLAY_PORT))
        myOscClient.connect((DISPLAY_ADDR, DISPLAY_PORT))
    except OSCClientError:
        print("no connection to %s : %s, can't send message" % (DISPLAY_ADDR, DISPLAY_PORT))

def loop():
    global lastTwitterCheck, myTwitterStream, streamThread
    global lastSmsCheck, mySmsClient, newestSmsSeconds
    ## check twitter queue
    if((time()-lastTwitterCheck > 5) and (not myTwitterStream.empty())):
        tweet = myTwitterStream.get().lower()
        tweet = tweet.decode('utf-8')

        ## removes re-tweet
        tweet = re.sub(r'(^[rR][tT] )', '', tweet)
        ## removes hashtags, arrobas and links
        tweet = re.sub(r'(#\S+)|(@\S+)|(http://\S+)', '', tweet)
        ## clean, tag and send text
        cleanTagAndSendText(tweet)
        lastTwitterCheck = time()

    ## check sms
    if(time()-lastSmsCheck > 5):
        smss = mySmsClient.messages.list(to=PHONE_NUMBER, date_sent_after = newestSmsSeconds)
        for sms in smss:
            smsSeconds = sms.date_sent
            if (smsSeconds > newestSmsSeconds):
                newestSmsSeconds = smsSeconds
            print("sms: %s" % (sms.body.encode("utf-8")))
            body = sms.body.lower()
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
        sys.exit(0)
