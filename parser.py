"""
Toys For Tots Donation Engine

Collect the donation list from the toys for tots donation page and use it to send
alerts to twitch to notify of new donations. This had to be custom built because
there was no system for alerting directly from here. The basic gist is that this
system will parse the table containing all the donations and alert when any new
ones appear.
"""
import re
import redis
from selenium import webdriver
import time
import requests

#Twitchalerts API
url = 'http://www.twitchalerts.com/api/v1.0/alerts'

# Payload. Use the subscription alert function. Add the sound and gif to that.
# Used subscription because our particular channel isn't partnered and this
# alert will never fire unless it's a donation from toys for tots
payload = {
    "access_token": "i5SItwavhHtY7Cu1UxreU0DFJfzNMOiDEkMh2w3E",
    "duration": "5",
    "type": "subscription",
    "special_text_color": "#ff0000",
}

# Define the alert function that will be used to actually fire to streamlabs
def alert(name, donation):
    payload['message'] = '*' + str(name) + '* has donated *' + str(donation) + '* to Toys For Tots!'
    session = requests.Session()
    response = session.post(url, data=payload)

# initiate
driver = webdriver.PhantomJS() # initiate a driver, in this case PhatomJS. No Window PopUp
driver.get("https://p2p.charityengine.net/ToysforTotsFoundation/Dashboard/Donations/") # go to the url

# log in
username_field = driver.find_element_by_name('UserName') # get the username field
password_field = driver.find_element_by_name('Password') # get the password field
username_field.send_keys("jlh0807ecu@gmail.com") # enter in your username
password_field.send_keys("2DorksTV") # enter in your password
password_field.submit() # submit it

# gotta wait while the new site loads
time.sleep(3)

html = driver.page_source

#turn the html into ascii so we can iterate over the lines
html = html.encode('ascii','ignore')

#close PhantomJS Instance
driver.quit()

# connect to the local redis DB running in a docker container
# This IP is going to change based on your environment.
# Use `docker inspect` on your redis box to get the IP
r = redis.StrictRedis(host='172.17.0.2', port=6379)

# create a result that will hold each dictionary
result = []

# Loop over the lines in the HTML to get the lines we want
for line in str.splitlines(html):
    # Find the username line in the table
    if re.search("(<td>Opted out of communications<\/td>)", line):
        continue
    if re.search("(<td>([0-9a-zA-Z'*-*]+\s*)*<\/td>)", line):
        # Create a hold dictionary when we find a name
        hold = {}
        line = re.sub('<\/*td>', '', line)
        hold['name'] = str(line).strip()
    # Find the donation amount. It will be the next lien so we should be good
    if re.search("<td>\$[0-9]+\.[0-9]{2}<\/td>", line):
        line = re.sub('<\/*td>', '', line)
        hold['donation'] = str(line).strip()
        # Append the hold dictionary to result so we have something like this:
        # {'donation': '$10.00', 'name':'SteveHNH'}
        result.append(hold)


# open a file for writing in append mode. This adds lines to the bottom of the
# file, rather than overwriting it.
f = open('./html/donations.txt', 'a+')

# iterate over the result list, load each dict into the redis db as a keypair
# and write the data set to donations.txt for use in a webservice
for i in result:
    if r.get(i.get('name')) != i.get('donation'):
        f.write(i.get('name') + ': ' + i.get('donation') + '<br />' + '\n')
        r.set(i.get('name'), i.get('donation'))
        # Send the alert to twitch alerts using the defined function
        # Sleep time set to 15 to avoid overloading streamlabs. Not sure if this is
        # a problem or not.
        time.sleep(15)
        # Pull the name and donation from the dictionary, not redis.
        alert(i.get('name'), i.get('donation'))
f.close()

with open('./html/donations.txt', 'r') as content_file:
    content = content_file.read()

f = open('./html/total.txt', 'w+')
total = 0
for line in content.splitlines():
   dollar = re.search("[0-9]+\.[0-9]{2}", line)
   dollar = dollar.group()
   total = total + float(dollar)
f.write('${:,.2f}'.format(total) + '\n')
f.close()

# write the percentage to a file
f = open('./html/percent.txt', 'w+')
percentage = float(total) / 500
f.write("{:.0%}".format(percentage) + '   \n')
f.close()

# Get the number of lines so we can feed it to the meter
num_lines = sum(1 for line in open('./html/donations.txt'))
f = open('./html/lines.txt', 'w+')
f.write(str(num_lines) + '\n')
f.close()
