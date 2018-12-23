"""
Toys For Tots Donation Engine

Collect the donation list from the toys for tots donation page and use it to send
alerts to twitch to notify of new donations. This had to be custom built because
there was no system for alerting directly from here. The basic gist is that this
system will parse the table containing all the donations and alert when any new
ones appear.
"""
import re
import time
import os
import sqlite3
import hashlib
import logging
import cookielib

import configparser
import requests
import mechanize
from bs4 import BeautifulSoup

# Establish logging
logging.basicConfig(level="INFO",
                    format="%(asctime)s %(levelname)s -- %(message)s")
logger = logging.getLogger("parser")

cwd = os.getcwd()

# Read the configuration file
config = configparser.ConfigParser()
config.read('config.ini')
ACCESS_TOKEN = config['default']['access_token']
USERNAME = config['default']['username']
PASSWORD = config['default']['password']
URL = config['default']['url']

cj = cookielib.CookieJar()
br = mechanize.Browser()
br.set_cookiejar(cj)

# Twitchalerts API
url = 'https://streamlabs.com/api/v1.0/alerts'

# Donate API
durl = 'https://streamlabs.com/api/v1.0/donations'

# Payload. Use the subscription alert function. Add the sound and gif to that.
# Used subscription because our particular channel isn't partnered and this
# alert will never fire unless it's a donation from toys for tots
payload = {
    "access_token": ACCESS_TOKEN,
    "duration": "12000",
    "type": "subscription",
    "special_text_color": "#ff0000",
    "sound_href": "https://uploads.twitchalerts.com/000/108/569/223/TwitchAlertAudio.ogg",
    "image_href": "https://uploads.twitchalerts.com/000/108/569/223/Make%20it%20rain.gif",
}

query = {
    "access_token": ACCESS_TOKEN,
    "currency": "USD",
    "skip_alert": "yes"
}

sqlite_file = cwd + '/db.sqlite'


# Define the alert function that will be used to actually fire to streamlabs
def alert(d):
    payload['message'] = '*{name}* has donated *{amount}* to Toys For Tots!'.format(**d)
    result = requests.post(url, data=payload)
    if result.status_code != 200:
        logger.error("Alert Post Failure: %s", result.json())
        return "error"


def donate(name, donation, hash_):
    query['name'] = name.replace(' ', '_')
    query['identifier'] = hash_
    query['amount'] = donation.strip('$')
    result = requests.post(durl, data=query)
    if result.status_code != 200:
        logger.error("Donation Alert Post Failure: %s", result.json())
        return "error"


def login():
    br.open(URL)
    br.select_form(nr=0)
    try:
        br.form['user[email]'] = USERNAME
        br.form['user[password]'] = PASSWORD
        br.submit()
    except mechanize.ControlNotFoundError:
        return


def scrape_page():
    br.open(URL)
    return br.response().read()


def init_db():
    conn = sqlite3.connect(sqlite_file)
    db = conn.cursor()
    db.execute('CREATE TABLE IF NOT EXISTS donations ("id" PRIMARY KEY, name TEXT, amount TEXT, timestamp TEXT)')


def main():

    conn = sqlite3.connect(sqlite_file)
    db = conn.cursor()

    # use MD5 for usernames
    m = hashlib.md5()

    # create a result that will hold each dictionary
    result = []

    # Loop over the lines in the HTML to get the lines we want
    login()

    soup = BeautifulSoup(scrape_page(), 'html.parser')

    for tr in soup.find_all('tr')[1:]:
        hold = {}
        tds = tr.find_all('td')
        hold['name'] = tds[1].text.strip().split(' ')[0]
        hold['amount'] = tds[2].text.strip()
        hold['id'] = re.sub('[^0-9]', '', tds[1].get('id').strip())

        result.append(hold)

    # open a file for writing in append mode. This adds lines to the bottom of the
    # file, rather than overwriting it.
    f = open(cwd + '/html/donations.txt', 'a+')

    # iterate over the result list, load each dict into the redis db as a keypair
    # and write the data set to donations.txt for use in a webservice
    for i in result:
        db.execute('SELECT "id" FROM "donations" WHERE "id"="' + i.get('id') + '"')
        exists = db.fetchone()
        if not exists:
            m.update(i.get('name'))
            if alert(i) == "error":
                pass
            elif donate(i.get('name'), i.get('amount'), m.hexdigest()) == "error":
                pass
            else:
                f.write(i.get('name') + ': ' + i.get('amount') + '<br />' + '\n')
                db.execute('INSERT INTO "donations" ("id", "name", "amount", "timestamp") VALUES ("' +
                           i.get('id') + '", "' + i.get('name') + '", "' +
                           i.get('amount') + '", + "' + time.strftime("%c") + '")')
                conn.commit()
                logger.info("Donation recorded for %s for %s", i.get('name'), i.get('amount'))
                # get md5 hash of username for donation compilation
                time.sleep(5)
    f.close()
    db.close()

    with open(cwd + '/html/donations.txt', 'r') as content_file:
        content = content_file.read()

    f = open(cwd + '/html/total.txt', 'w+')
    total = 0
    for line in content.splitlines():
        dollar = re.search(r"[0-9]+\.[0-9]{2}", line)
        dollar = dollar.group()
        total = total + float(dollar)
    f.write('${:,.2f}'.format(total) + '\n')
    f.close()

    # write the percentage to a file. Change second numeral to goal
    f = open(cwd + '/html/percent.txt', 'w+')
    percentage = float(total) / 1500
    f.write("{:.0%}".format(percentage) + '   \n')
    # Get the number of lines so we can feed it to the meter
    num_lines = sum(1 for line in open(cwd + '/html/donations.txt'))
    f = open(cwd + '/html/lines.txt', 'w+')
    f.write(str(num_lines) + '\n')
    f.close()


if __name__ == "__main__":
    init_db()
    while True:
        main()
        time.sleep(30)
