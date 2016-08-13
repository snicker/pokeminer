import db
import dbmore
import json
import logging
import time
from geopy.geocoders import Nominatim
from slackclient import SlackClient
from twilio.rest import TwilioRestClient

geolocator = Nominatim()

from names import POKEMON_NAMES
    
class SlackMessageClient(object):
    def __init__(self, token):
        self.token = token
        self.slack = SlackClient(self.token)
    
    def send_message_to_username(self, user, message):
        return self.send_message_to_channel('@{user}'.format(user=user),message)
    
    def send_message_to_channel(self, channel, message):
        return self.slack.api_call("chat.postMessage",channel=channel,text=message,as_user="true")
        
class MessageClient(object):
    def __init__(self,twilio_number,twilio_account_sid,twilio_auth_token):
        self.twilio_number = twilio_number
        self.twilio_client = TwilioRestClient(twilio_account_sid,
                                              twilio_auth_token)

    def send_message(self, body, to):
        self.twilio_client.messages.create(body=body, to=to,
                                           from_=self.twilio_number
                                           )
def getPokemonName(pokemon_id):
    return POKEMON_NAMES[pokemon_id]

def getLocation(spawn):
    return geolocator.reverse("{lat}, {lon}".format(lat=spawn.lat,lon=spawn.lon))

def getMapLink(spawn):
    return "https://www.google.com/maps/search/{lat},{lon}".format(lat=spawn.lat,lon=spawn.lon)
    
def main():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    with open('pokesms.config.json') as f:
        config = json.load(f)
    logging.debug(config)
    twilio = MessageClient(config['twilio']['number'],config['twilio']['account_sid'],config['twilio']['auth_token'])
    slack = SlackMessageClient(config['slack']['api-token'])
    spawns = []
    
    while True:
        session = db.Session()
        newspawns = []
        logging.info("Checking spawns for {pokemon_ids}...".format(pokemon_ids=config['pokemon']))
        currentspawns = dbmore.getCurrentSpawns(session,pokemon_ids=config['pokemon'])
        for spawn in currentspawns:
            newspawns.append(spawn)
        logging.info("Checking for rare spawns...")
        rarespawns = dbmore.getRareSpawns(session)
        for spawn in rarespawns:
            newspawns.append(spawn)
        added = []
        removed = []
        if len(newspawns) > 0:
            added, removed = diff(spawns, newspawns)
            logging.debug("added: {added}".format(added=added))
            logging.debug("removed: {removed}".format(removed=removed))
            spawns = newspawns
        for newspawn in added:
            logging.info("Pokemon {id}:{name} spawned at {lat},{lon}, expires in {expires}".format(name=getPokemonName(newspawn.pokemon_id),id=newspawn.pokemon_id,lat=newspawn.lat,lon=newspawn.lon,expires=newspawn.minsRemaining))
            try:
                location, hood, zip, address, hn, road = '','','','','',''
                try:
                    location = getLocation(newspawn)
                    logging.debug(location.raw)
                    zip = location.raw['address']['postcode']
                    if 'neighbourhood' in location.raw['address']:
                        hood = location.raw['address']['neighbourhood']
                    elif 'city' in location.raw['address']:
                        hood = location.raw['address']['city']
                    elif 'town' in location.raw['address']:
                        hood = location.raw['address']['town']
                    if 'house_number' in location.raw['address']:
                        hn = location.raw['address']['house_number']
                    if 'road' in location.raw['address']:
                        road = location.raw['address']['road']
                    address = "{hn} {road}".format(hn=hn,road=road)
                except Exception as e:
                    logging.error("FUCK {e}".format(e=e))
                message = "{name} spawned in {hood} ({zip}), available for {expires} minutes. {address} {link}".format(link=getMapLink(newspawn),address=address,hood=hood,zip=zip,name=getPokemonName(newspawn.pokemon_id),expires=newspawn.minsRemaining)
                #for number in config['destinations']:
                    #logging.info('Sending "{message}" to {number}...'.format(message=message,number=number))
                    #twilio.send_message(message,number)
                slack.send_message_to_channel(config['slack']['channel'],message)
            except Exception as e:
                logging.error("FUCK {e}".format(e=e))
        for spawn in removed:
            pass
        session.close()
        time.sleep(10)

    
    
def diff(old, new):
    added = list(set(new) - set(old))
    removed = list(set(old) - set(new))   
    return filter(None,added), filter(None,removed)    

if __name__ == "__main__":
    main()