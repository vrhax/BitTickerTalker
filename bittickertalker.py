# -----------------------------------------------------------------------------
# This code is written by VRHax.
# It is in the public domain, so you can do what you like with it
# but a link to https://github.com/vrhax/BitTalker would be nice.
#
# It works on the Raspberry Pi computer with the standard Debian Wheezy OS and
# the festival tts module
# -----------------------------------------------------------------------------
#
# USAGE: python bittalker.py
#
# -----------------------------------------------------------------------------
# import system libraries
# -----------------------------------------------------------------------------

import ConfigParser, pygame, os, sys, traceback, time
from pygame.locals import *

os.environ["SDL_FBDEV"] = "/dev/fb1"

pygame.init()

# -----------------------------------------------------------------------------
# import json api call library (exchange api)
# -----------------------------------------------------------------------------

import urllib2, httplib, json

# -----------------------------------------------------------------------------
# import bitcoin wallet connection library
#
#   NB: must first install bitcoin-python (as follows):
#
#       sudo apt-get install python-setuptools
#       sudo easy_install pip
#       sudo pip install bitcoin-python
# -----------------------------------------------------------------------------

import bitcoinrpc

# -----------------------------------------------------------------------------
# import subprocess library for calling festival tts
#
#   NB: must first install festival tts (as follows):
#
#       sudo apt-get update
#       sudo apt-get upgrade
#       sudo apt-get install alsa-utils
#
#       sudo apt-get install mplayer
#
#       sudo nano /etc/mplayer/mplayer.conf
#
#         add nolirc=yes
#
#       sudo apt-get install festival
#
# -----------------------------------------------------------------------------

import subprocess

# -----------------------------------------------------------------------------
# constants and static
# -----------------------------------------------------------------------------

lastex  = "000.00";
lastdex = "000.00";
lastbal = "000.00";
started = False;

# -----------------------------------------------------------------------------
# configuration initialization
# -----------------------------------------------------------------------------

config  = ConfigParser.RawConfigParser();
config.read('defaults.cfg');

sname   = config.get('Default','sname');
lname   = config.get('Default','lname');
lsize   = config.getint('Default','lsize');
httpe   = config.getfloat('Default','httpe');
watch   = config.getboolean('Default','watch');
showit  = config.getboolean('Default','display');
chatter = config.getboolean('Default','sound');
debug   = config.getboolean('Default','debug');

if config.has_option('ColdStorage', 'btc'):
    btccold = config.getfloat('ColdStorage', 'btc');
else:
    btccold = 0.0;

exname  = config.get('Exchange','exname');
blo     = config.getfloat('Exchange','blow');
bhi     = config.getfloat('Exchange','bhi');
pvar    = config.getfloat('Exchange','pvar');
poll    = config.getfloat('Exchange','poll');

exurl   = config.get(exname,'exurl');
pfld    = config.get(exname,'pfld');
exhi    = config.get(exname,'high');
exlo    = config.get(exname,'low');
exvol   = config.get(exname,'vol');

# -----------------------------------------------------------------------------
# fetch BTC addresses
# -----------------------------------------------------------------------------
with open('addresses.cfg') as f:
    addresses = f.read().splitlines();

# -----------------------------------------------------------------------------
# templates
# -----------------------------------------------------------------------------

from string import Template;

plog1        = Template('$pnow: Old: $oprice New: $nprice BTC: $btc BTC Cold: $btcc Total: $ttl Value: $bval');
plog2        = Template('$pnow: Old: $oprice New: $nprice');

sbitmsg      = Template('You have $ttl bitcoins, which are worth $bval cents');
smktmsg      = Template(exname+'\'s market price is $nprice cents');
sdeltamsg    = Template(exname+'\'s market price has $mdelta from $oprice cents to $nprice cents');

from time import gmtime, strftime

# -----------------------------------------------------------------------------
# set up the colors
# -----------------------------------------------------------------------------

BLACK   = (  0,  0,  0);
WHITE   = (255,255,255);
RED     = (255,  0,  0);
GREEN   = (  0,255,  0);
BLUE    = (  0,  0,255);
TEAL    = (  0,128,255);
PURPLE  = (255,  0,255);
YELLOW  = (255,255,  0);

# -----------------------------------------------------------------------------
# set up the window (320x240) => (128x160)
# -----------------------------------------------------------------------------

screen = pygame.display.set_mode((160, 128), 0, 32)
pygame.display.set_caption('Drawing')

# -----------------------------------------------------------------------------
# Fill background
#    stamp       = pygame.transform.rotate(stamp,270);
# -----------------------------------------------------------------------------
if(showit):
    background  = pygame.Surface(screen.get_size())
    background  = background.convert()
    background.fill(BLACK)

    stamp       = pygame.image.load("bitstamp.jpg");
    stampos     = stamp.get_rect(centerx=background.get_width()/1.75,centery=background.get_height()/2);
    background.blit(stamp,stampos);
    pygame.mouse.set_visible(0);

# -----------------------------------------------------------------------------
# update the screen
# -----------------------------------------------------------------------------

def refresh():
    screen.blit(background, (0, 0));
    pygame.display.flip();
    pygame.display.update();

# -----------------------------------------------------------------------------
# logging macro.
# -----------------------------------------------------------------------------

def log(phrase):
    old_stdout      = sys.stdout;
    if(os.path.isfile(lname)):
        if(os.path.getsize(lname) >= lsize):
            say('Max filesize reached. Creating new file.');
            log_file    = open(lname,"w");
            sys.stdout  = log_file;
            print '# ----------------------------------------------------------------------------- #';
        else:
            log_file    = open(lname,"a");
            sys.stdout  = log_file;
    else:
        log_file    = open(lname,"w");
        sys.stdout  = log_file;
        print '# ----------------------------------------------------------------------------- #';
    print phrase;
    sys.stdout = old_stdout;
    log_file.close();
# -----------------------------------------------------------------------------
# speech macros
# -----------------------------------------------------------------------------

def say(phrase):
    if(watch):
        print((phrase.replace('00 cents','00')).replace('\$','$'));
    if(chatter):
        subprocess.call('echo "'+phrase.replace('00 cents','00')+'" | festival --tts', shell=True);

def talk(delta,price,btcbal):

    now = strftime("%Y-%m-%d %H:%M:%S", time.localtime());

    if(delta != ''):
        say(sdeltamsg.substitute(mdelta=delta,oprice='\$'+lastex,nprice='\$'+price));
    else :
        say(smktmsg.substitute(nprice='\$'+price));

    btcttl  = str(float(btcbal)+float(btccold));
    btcval  = str("%.2f" % round((float(price) * float(btcttl)),2));
    say(sbitmsg.substitute(ttl=btcttl,bval='\$'+btcval));
    if(debug):log(plog1.substitute(pnow=now,oprice='$'+lastex,nprice='$'+price,btc=btcbal,btcc=btccold,ttl=btcttl,bval='$'+btcval));

# -----------------------------------------------------------------------------
# Display some text
#    text = pygame.transform.rotate(text,270);
# -----------------------------------------------------------------------------

def ticker(bval, val, hi, lo, tvol, ttl, tcolor):

    box  = pygame.draw.rect(background, BLACK ,(0, 0,160, 128));
    background.blit(stamp,stampos);

# -----------------------------------------------------------------------------
# Variation
# -----------------------------------------------------------------------------

    font = pygame.font.SysFont("Comic Sans MS", 20);
    text = font.render("${:,.2f}".format(lo), 1, (RED));
    textpos = text.get_rect(centerx=background.get_width()/5,centery=background.get_height()/6)
    background.blit(text, textpos);

    font = pygame.font.SysFont("Comic Sans MS", 20);
    text = font.render("${:,.2f}".format(hi), 1, (GREEN));
    textpos = text.get_rect(centerx=background.get_width()/1.25,centery=background.get_height()/6)
    background.blit(text, textpos);

# -----------------------------------------------------------------------------
#    font = pygame.font.SysFont("Comic Sans MS", 25);
#    text = font.render("{:,.2f}".format(tvol), 1, (PURPLE));
#    textpos = text.get_rect(centerx=background.get_width()/2,centery=background.get_height()/2.75)
#    background.blit(text, textpos);
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Current price
# -----------------------------------------------------------------------------

    font = pygame.font.SysFont("Comic Sans MS", 40);
    text = font.render("${:,.2f}".format(val), 1, (tcolor));
    textpos = text.get_rect(centerx=background.get_width()/2,centery=background.get_height()/2.1)
    background.blit(text, textpos);

# -----------------------------------------------------------------------------
# Balance
# -----------------------------------------------------------------------------

    font = pygame.font.SysFont("Comic Sans MS", 30);
    text = font.render("${:,.2f}".format(bval), 1, (TEAL));
    textpos = text.get_rect(centerx=background.get_width()/2,centery=background.get_height()/1.25)
    background.blit(text, textpos);

    font = pygame.font.SysFont("Comic Sans MS", 20);
    text = font.render("[{:,.9f}]".format(ttl), 1, (WHITE));
    textpos = text.get_rect(centerx=background.get_width()/2,centery=background.get_height()/1.1)
    background.blit(text, textpos);


    refresh();

# -----------------------------------------------------------------------------
# fetch balance for each address in address section
# -----------------------------------------------------------------------------
# http://blockchain.info/address/$bitcoin_address?format=json

btcdivider = '100000000';
bcpre = 'https://blockchain.info/address/';
bcap  = '?format=json';

def getBalance():
    balance = 0;
    for i in range(len(addresses)):
        bcurl    = bcpre+addresses[i]+bcap;
        try:
            jsonurl = urllib2.urlopen(bcurl);
            data = json.loads(jsonurl.read());
        except (urllib2.HTTPError):
            say('Blockchain info unaccessible. Continuing.');
            continue;
        balance += data["final_balance"];
    return float(balance)/int(btcdivider);

# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------

refresh();

# say('Hello!');
# say(sname+' started.');
say(exname+' polling set to '+str(poll)+' seconds.');

# -----------------------------------------------------------------------------
# polling loop
# -----------------------------------------------------------------------------

while True:

    try:

# -----------------------------------------------------------------------------
# get bitcoin balance
# -----------------------------------------------------------------------------
        btcbalance = getBalance();

# -----------------------------------------------------------------------------
# get market data
# -----------------------------------------------------------------------------

        try:
            jsonurl = urllib2.urlopen(exurl);
            data = json.loads(jsonurl.read());
            btcprice = data[pfld];
            high     = data[exhi];
            low      = data[exlo];
            vol      = data[exvol];


# -----------------------------------------------------------------------------
# site down or slow response. check again in 30 seconds
# -----------------------------------------------------------------------------

        except (urllib2.HTTPError):
            say(exname+' unaccessible. Rechecking in '+str(httpe/60.0)+' minutes');
            time.sleep(httpe);
            continue;

# -----------------------------------------------------------------------------
# display ${:,.2f}
# -----------------------------------------------------------------------------
        if(showit):
            btcttl  = (float(btcbalance) + float(btccold));
            btcval  = (float(btcprice) * float(btcttl));

            if (float(btcprice) > float(lastdex)):
                ticker(float(btcval), float(btcprice), float(high), float(low), float(vol), float(btcttl), GREEN);
            elif (float(btcprice) < float(lastdex)):
                ticker(float(btcval), float(btcprice), float(high), float(low), float(vol), float(btcttl), RED);

            lastdex = btcprice;

# -----------------------------------------------------------------------------
# check reporting status (little/no change, stay silent)
# -----------------------------------------------------------------------------

        if not(started):
            lastex  = btcprice;
            started = True;

# -----------------------------------------------------------------------------
#        if (float(btcprice) >= float(bhi)):
#            talk('Maximum Reached',btcprice,btcbalance);
#            lastbal = btcbalance;
#        elif (float(btcprice) <= float(blo)):
#            talk('Minimum Reached',btcprice,btcbalance);
#            lastbal = btcbalance;
# -----------------------------------------------------------------------------

        if (btcbalance != lastbal) :
            talk('',btcprice,btcbalance);
            lastbal = btcbalance;
        elif (float(btcprice) >= float(lastex) + float(pvar)) :
            talk('increased',btcprice,btcbalance);
            lastex  = btcprice;
        elif (float(btcprice) <= float(lastex) - float(pvar)) :
            talk('decreased',btcprice,btcbalance);
            lastex  = btcprice;

# -----------------------------------------------------------------------------
# poll once every n seconds
# -----------------------------------------------------------------------------

        time.sleep(poll);

# -----------------------------------------------------------------------------
# ctrl-c halts script
# -----------------------------------------------------------------------------

    except (KeyboardInterrupt, SystemExit):
        break;

# -----------------------------------------------------------------------------
# The End. Clean exit.
# -----------------------------------------------------------------------------

say(sname+' halted. Good-bye!');
exit(0);