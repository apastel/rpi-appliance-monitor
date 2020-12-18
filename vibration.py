from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import threading
import RPi.GPIO as GPIO
import requests
import smtplib
import json
import tweepy
from time import localtime, strftime
import paho.mqtt.publish as mqttpublish
import vlc
import configparser
from tweepy import OAuthHandler as TweetHandler
# from slack import SlackClient

PUSHOVER_SOUNDS = None


def email(msg):
    try:
        message = MIMEMultipart('related')
        message['Subject'] = msg
        message['From'] = email_sender
        message['To'] = email_recipient
        message.preamble = 'This is a multi=part message in MIME format.'

        message_alternative = MIMEMultipart('alternative')
        message.attach(message_alternative)
        message_text = MIMEText(msg + '\n')

        message_text = MIMEText('<h3>' + msg + '</h3>')

        message_text.replace_header('Content-Type', 'text/html')
        message_alternative.attach(message_text)

        s = smtplib.SMTP(email_server, email_port)
        s.starttls()
        s.login(email_sender, email_password)
        s.sendmail(email_sender, email_recipient, message.as_string())
        s.quit()
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass


def mqtt(msg):
    try:
        mqtt_auth = None
        if len(mqtt_username) > 0:
            mqtt_auth = { 'username': mqtt_username, 'password': mqtt_password }

        mqttpublish.single(mqtt_topic, msg, qos=0, retain=False, hostname=mqtt_hostname,
        port=mqtt_port, client_id=mqtt_clientid, keepalive=60, will=None, auth=mqtt_auth,
        tls=None)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass

def pushbullet(cfg, msg):
    try:
        data_send = {"type": "note", "body": msg}
        requests.post(
            'https://api.pushbullet.com/v2/pushes',
            data=json.dumps(data_send),
            headers={'Authorization': 'Bearer ' + cfg,
                     'Content-Type': 'application/json'})
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass

def get_pushoversounds(app_key):
    global PUSHOVER_SOUNDS

    if not PUSHOVER_SOUNDS:
        url_data = "https://api.pushover.net/1/sounds.json?token={}" .format(app_key)

        try:
            r = requests.get(url_data)
            json_data = r.json()
            PUSHOVER_SOUNDS = json_data['sounds']
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass


def pushover(user_key, app_key, msg, device='', sound=''):
    global PUSHOVER_SOUNDS

    if not PUSHOVER_SOUNDS:
        get_pushoversounds(app_key)

    data_send = {"user": user_key, "token": app_key, "message": msg}

    if device:
        data_send['device'] = device

    if sound in PUSHOVER_SOUNDS:
        data_send['sound'] = sound

    try:
        requests.post(
            'https://api.pushover.net/1/messages.json',
            data=json.dumps(data_send),
            headers={'Content-Type': 'application/json'})
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass

def iftt(msg):
    try:
        for key in iftt_maker_channel_keys:
            iftt_url = "https://maker.ifttt.com/trigger/{}/with/key/{}".format(iftt_maker_channel_event, key)
            report = {"value1" : msg}
            resp = requests.post(iftt_url, data=report)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass

def slack_webhook(msg):
    try:
        requests.post(slack_webhook_url, json={'text': msg}, headers={"Content-type": "application/json"})
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass

def tweet(msg):
    try:
        # Twitter is the only API that NEEDS something like a timestamp,
        # since it will reject identical tweets.
        tweet = msg + ' ' + strftime("%Y-%m-%d %H:%M:%S", localtime())
        auth = TweetHandler(twitter_api_key, twitter_api_secret)
        auth.set_access_token(twitter_access_token,
                              twitter_access_token_secret)
        tweepy.API(auth).update_status(status=tweet)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass


def slack(msg):
    try:
        slack = msg + ' ' + strftime("%Y-%m-%d %H:%M:%S", localtime())
        sc = SlackClient(slack_api_token)
        sc.api_call(
            'chat.postMessage', channel='#random', text=slack)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass

def telegram(msg):
    try:
        telegram_url = "https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}".format(telegram_api_token,
                                                                           telegram_user_id, msg)
        resp = requests.post(telegram_url)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass


def send_alert(message):
    if len(message) > 1:
        logging.info(message)
        if len(pushover_user_key) > 0 and len(pushover_app_key) > 0:
            pushover(pushover_user_key, pushover_app_key, message, pushover_device, pushover_sound)
        if len(pushbullet_api_key) > 0:
            pushbullet(pushbullet_api_key, message)
        if len(pushbullet_api_key2) > 0:
            pushbullet(pushbullet_api_key2, message)
        if len(twitter_api_key) > 0:
            tweet(message)
        if len(slack_api_token) > 0:
            slack(message)
        if len (slack_webhook_url) > 0:
            slack_webhook(message)
        if len(iftt_maker_channel_keys) > 0:
            iftt(message)
        if len(mqtt_topic) > 0:
            mqtt(message)
        if len(email_recipient) > 0:
            email(message)
        if len(telegram_api_token) > 0 and len(telegram_user_id) > 0:
            telegram(message)


def send_appliance_active_message():
    send_alert(start_message)
    global appliance_active
    appliance_active = True


def send_appliance_inactive_message():
    send_alert(end_message)
    global appliance_active
    appliance_active = False


def vibrated(pin):
    global vibrating
    global last_vibration_time
    global start_vibration_time
    logging.info('Vibrated')
    last_vibration_time = time.time()
    if not vibrating:
        start_vibration_time = last_vibration_time
        vibrating = True


def make_very_loud_noise():
    logging.info('Commence very loud noise....fuck you neighbors!!')
    p = vlc.MediaPlayer("sounds/most_annoying_sound_in_world.mp3")
    p.play()

def heartbeat():
    current_time = time.time()
    if int(current_time) % 60 == 0:
        logging.debug("Heartbeat")
    global vibrating
    delta_vibration = last_vibration_time - start_vibration_time
    if (vibrating and delta_vibration > begin_seconds
            and not appliance_active):
        send_appliance_active_message()
        make_very_loud_noise()
    if (not vibrating and appliance_active
            and current_time - last_vibration_time > end_seconds):
        send_appliance_inactive_message()
    vibrating = current_time - last_vibration_time < 2
    threading.Timer(1, heartbeat).start()

config = configparser.ConfigParser()
config.read(sys.argv[1])
logfile = config.get('main', 'LOGFILE')
handler = TimedRotatingFileHandler(logfile, when='midnight', interval=1, backupCount=20)
formatter = logging.Formatter('%(asctime)s %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel('INFO')

if len(sys.argv) == 1:
    logging.critical("No config file specified")
    sys.exit(1)

vibrating = False
appliance_active = False
last_vibration_time = time.time()
start_vibration_time = last_vibration_time

verbose = config.getboolean('main', 'VERBOSE')
sensor_pins = config.get('main', 'SENSOR_PINS').split(" ")
begin_seconds = config.getint('main', 'SECONDS_TO_START')
end_seconds = config.getint('main', 'SECONDS_TO_END')
pushbullet_api_key = config.get('pushbullet', 'API_KEY')

pushover_user_key = config.get('pushover', 'user_api_key')
pushover_app_key = config.get('pushover', 'app_api_key')
pushover_device  = config.get('pushover', 'device')
pushover_sound   = config.get('pushover', 'sound')

mqtt_hostname = config.get('mqtt', 'mqtt_hostname')
mqtt_port = config.get('mqtt', 'mqtt_port')
mqtt_topic = config.get('mqtt', 'mqtt_topic')
mqtt_username = config.get('mqtt', 'mqtt_username')
mqtt_password = config.get('mqtt', 'mqtt_password')
mqtt_clientid = config.get('mqtt', 'mqtt_clientid')

pushbullet_api_key2 = config.get('pushbullet', 'API_KEY2')
start_message = config.get('main', 'START_MESSAGE')
end_message = config.get('main', 'END_MESSAGE')
twitter_api_key = config.get('twitter', 'api_key')
twitter_api_secret = config.get('twitter', 'api_secret')
twitter_access_token = config.get('twitter', 'access_token')
twitter_access_token_secret = config.get('twitter', 'access_token_secret')
slack_api_token = config.get('slack', 'api_token')
slack_webhook_url = config.get('slack','webhook_url')
iftt_maker_channel_event = config.get('iftt','maker_channel_event')
iftt_maker_channel_keys = config.get('iftt','maker_channel_keys')
email_recipient = config.get('email', 'recipient')
email_sender = config.get('email', 'sender')
email_password = config.get('email', 'password')
email_server = config.get('email', 'server')
email_port = config.get('email', 'port')
telegram_api_token = config.get('telegram', 'telegram_api_token')
telegram_user_id = config.get('telegram', 'telegram_user_id')

if verbose:
    logging.getLogger().setLevel(logging.DEBUG)

send_alert(config.get('main', 'BOOT_MESSAGE'))

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in sensor_pins:
    GPIO.setup(int(pin), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(int(pin), GPIO.RISING)
    GPIO.add_event_callback(int(pin), vibrated)
    logging.info('Monitoring GPIO pin {}'.format(pin))

logging.info('Running config file {}'.format(sys.argv[1]))

threading.Timer(1, heartbeat).start()

