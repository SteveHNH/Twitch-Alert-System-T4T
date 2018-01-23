"""
Toys For Tots Donation Engine

Collect the donation list from the toys for tots donation page and use it to send
alerts to twitch to notify of new donations. This had to be custom built because
there was no system for alerting directly from here. The basic gist is that this
system will parse the table containing all the donations and alert when any new
ones appear.
"""
import re
from selenium import webdriver
import time
import requests
import os
import sqlite3
import hashlib

# Twitchalerts API
url = 'https://streamlabs.com/api/v1.0/alerts'

# Donate API
durl = 'https://streamlabs.com/api/v1.0/donations'

# Payload. Use the subscription alert function. Add the sound and gif to that.
# Used subscription because our particular channel isn't partnered and this
# alert will never fire unless it's a donation from toys for tots
payload = {
    "access_token": "ACCESS_TOKEN",
    "duration": "12000",
    "type": "subscription",
    "special_text_color": "#ff0000",
    "sound_href": "https://uploads.twitchalerts.com/000/108/569/223/TwitchAlertAudio.ogg",
    "image_href": "https://uploads.twitchalerts.com/000/108/569/223/Make%20it%20rain.gif",
}

query = {
    "access_token": "ACCESS_TOKEN",
    "currency": "USD",
}

sqlite_file = '/root/db.sqlite'


# Define the alert function that will be used to actually fire to streamlabs
def alert(name, donation):
    payload['message'] = '*' + str(name) + '* has donated *' + str(donation) + '* to Toys For Tots!'
    session = requests.Session()
    session.post(url, data=payload)


def donate(name, donation, hash_):
    query['name'] = name.replace(' ', '_')
    query['identifier'] = hash_
    query['amount'] = donation.strip('$')
    session = requests.Session()
    session.post(durl, data=query)


def get_driver():
    cwd = os.path.dirname(os.path.realpath(__file__))
    kwargs = {'service_log_path': os.path.devnull}
    kwargs['executable_path'] = os.path.join(cwd, 'bin/phantomjs')

    driver = webdriver.PhantomJS(**kwargs)  # initiate a driver, in this case PhatomJS. No Window PopUp
    return driver

driver = get_driver()
driver.get("URL containing table of donations")  # go to the url

# log in
username_field = driver.find_element_by_name('user[email]')  # get the username field
password_field = driver.find_element_by_name('user[password]')  # get the password field
username_field.send_keys("username")  # enter in your username
password_field.send_keys("password")  # enter in your password
driver.find_element_by_id('new_user').submit()

# gotta wait while the new site loads
time.sleep(3)

html = driver.page_source

# turn the html into ascii so we can iterate over the lines
html = html.encode('ascii', 'ignore')

# close PhantomJS Instance
driver.quit()

# use MD5 for usernames
m = hashlib.md5()

# Connect to the sqlite database
conn = sqlite3.connect(sqlite_file)
db = conn.cursor()
db.execute('CREATE TABLE IF NOT EXISTS donations ("id" PRIMARY KEY, name TEXT, amount TEXT, timestamp TEXT)')

# create a result that will hold each dictionary
result = []

split = str.splitlines(html)
# Loop over the lines in the HTML to get the lines we want
for line in split:
    match = re.search('\s*<td id="donor_name\d+">', line)
    money = re.search('\s*<td id="donation_amount\d+" class="text-center">', line)
    # Find the username line in the table
    if re.search("(<td>Opted out of communications<\/td>)", line):
        continue
    if match:
        donate_id = '\n'.join(re.findall('\d+', match.group(0)))
        # Create a hold dictionary when we find a name
        hold = {}
        hold['name'] = split[split.index(match.group(0)) + 1].strip().split()[0]
        hold['donate_id'] = donate_id
    # Find the donation amount. It will be the next line so we should be good
    if money:
        hold['donation'] = split[split.index(money.group(0)) + 1].strip()
        # Append the hold dictionary to result so we have something like this:
        # {'donation': '$10.00', 'name':'SteveHNH'}
        result.append(hold)

# open a file for writing in append mode. This adds lines to the bottom of the
# file, rather than overwriting it.
f = open('/root/Twitch-Alert-System-T4T/html/donations.txt', 'a+')

# iterate over the result list, load each dict into the redis db as a keypair
# and write the data set to donations.txt for use in a webservice
for i in result:
    db.execute('SELECT "id" FROM "donations" WHERE "id"=' + i.get('donate_id'))
    exists = db.fetchone()
    if not exists:
        f.write(i.get('name') + ': ' + i.get('donation') + '<br />' + '\n')
        db.execute('INSERT INTO "donations" ("id", "name", "value", "timestamp") VALUES ("' +
                  i.get('donate_id') + '", "' + i.get('name') + '", "' +
                  i.get('donation') + '", + "' + time.strftime("%c") + '")')
        db.commit()
        # get md5 hash of username for donation compilation
        m.update(i.get('name'))
        # Send the alert to twitch alerts using the defined function
        # Sleep time set to 15 to avoid overloading streamlabs. Not sure if this is
        # a problem or not.
        time.sleep(15)
        # Pull the name and donation from the dictionary, not redis.
        alert(i.get('name'), i.get('donation'))
        donate(i.get('name'), i.get('donation'), m.hexdigest())
f.close()
db.close()

with open('/root/Twitch-Alert-System-T4T/html/donations.txt', 'r') as content_file:
    content = content_file.read()

f = open('/root/Twitch-Alert-System-T4T/html/total.txt', 'w+')
total = 0
for line in content.splitlines():
    dollar = re.search("[0-9]+\.[0-9]{2}", line)
    dollar = dollar.group()
    total = total + float(dollar)
f.write('${:,.2f}'.format(total) + '\n')
f.close()

# write the percentage to a file. Change second numeral to goal
f = open('/root/Twitch-Alert-System-T4T/html/percent.txt', 'w+')
percentage = float(total) / 1000
f.write("{:.0%}".format(percentage) + '   \n')
# Get the number of lines so we can feed it to the meter
num_lines = sum(1 for line in open('/root/Twitch-Alert-System-T4T/html/donations.txt'))
f = open('/root/Twitch-Alert-System-T4T/html/lines.txt', 'w+')
f.write(str(num_lines) + '\n')
f.close()
