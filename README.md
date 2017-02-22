# Toys for Tots Charity Stream Alert System

My friends at [2dorksTV](http://www.twitch.tv/2dorkstv) and I wanted to do a charity stream for Toys for Tots. It's a charity we all believe in and figured that maybe some people out on Twitch do as well. The only issue we had was that we had no way to know if someone was donating to them or not, since [Streamlabs](http://www.streamlabs.com) can't connect directly to that charity.

We ended up building our own thing. Here's the breakdown of how to get this deal running if you want to use it for yourself.

## Requirements

Here are the things that we used to get it going. You can adapt some of this to your own needs, but I documented everything here to run it just like we did.

**NOTE:** I ran this thing on Linux, so this doc is written from that perspective

* python 2
* docker (if you want to do it the way we did)
* an internet accessible server (if you intend for the meter and content to be public)
* Your [Streamlabs](http://www.streamlabs.com) access token

## Getting your Streamlabs access token

This is out of scope for our documentation, but you can find some fantastic code out there for achieving this easily. Check out [Singlerider's Code](https://github.com/singlerider/twitchalerts_oauth).

The only caveat to his code is that it automatically only authorizes donation info. You can add alert permission just by appending "+alerts.create" to the URL on the authorize page. You'll know it when you see it.

## Setup

Clone the repo
```
git clone git@github.com/SteveHNH/Twitch-Alert-System-T4T
```

We're assuming that you already have your donation engine account for toys for tots and you know your own login info. You'll need to edit `parser.py` and update these two fields with your username and password. Yeah, I know it's plain text and that's bad. Don't put this where people can get to it.
```
username_field.send_keys("username") # enter in your username
password_field.send_keys("password") # enter in your password
```

Add your twitchalerts access token to this field:
```
"access_token": "API_ACCESS_TOKEN",
```

You'll also want to have your redis server up and running for storing the keys and values. To easily do that, we recommend [Docker](http://www.docker.com). It's the quickest way to get an app up and running. Installing docker is a bit out of scope, but their documentation is great so go check it out. Once you have that done,  you can just run these commands:
```
docker pull redis
docker run --name twitchalert-redis -d redis
```

Grab the IP from the redis container with `docker inspect twitchalert-redis | grep IPAddress`. You'll need to insert the IP in this line within parser.py `r = redis.StrictRedis(host='172.17.0.2', port=6379)`

That's the easy part. You can now send alerts from your donation page to twitchalerts just by running `python parser.py`. But you want to have that snazzy meter we used, right?  
![Meter Image](https://www.2dorks.net/media/gifs/meter.png)

If you want that, we have to add some stuff. You'll need a web server and a way to access it. We can do this locally with more docker magic.
```
docker pull nginx
docker run -d -v /path/to/html:/usr/share/nginx/html:ro -p 8080:80 --name twitchalerts-donations nginx
```

You can change the stuff in that second command so that you expose the port you want and the path you need. We're going to assume you need to present the html folder you pulled from the git repo, but you might move that somewhere else and we don't have any idea where you put it.

You should now be able to visit `http://localhost:8080/meter.html` in your browser and you should see the meter.

# The code

I wrote this as a grand experiment with python. I can't take credit for the HTML stuff as someone else contributed that, but I can take credit for the crappy jquery implementation. If you know of  a better way to do the automated updating of the data, feel free to help me out. I'm hoping the methods used here help someone, and maybe even open up possibilities for other charity donation systems. There are plenty that aren't aware of [Twitch](http://www.twitch.tv) and don't have easy ways of grabbing donater alerts.

# More info

Visit [this page](https://stevehnh.github.io/2017-01-03-building-a-twitch-alert-system) for more information on the challenges and reasons behind the code. I had fun building it, but I know there have to be better ways in some cases. 
