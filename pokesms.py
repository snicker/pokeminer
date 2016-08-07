import db
import dbmore
import json
import logging
import time
from geopy.geocoders import Nominatim
from twilio.rest import TwilioRestClient

geolocator = Nominatim()

with open('locales/pokemon.en.json') as f:
    pokemon_names = json.load(f)

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
    return pokemon_names[str(pokemon_id)]

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
    spawns = {}
    
    while True:
        session = db.Session()
        for pokemon_id in config['pokemon']:
            logging.info("Checking spawns for {pokemon_id}...".format(pokemon_id=pokemon_id))
            newspawns = dbmore.getCurrentSpawns(session,pokemon_id)
            added = []
            removed = []
            if pokemon_id not in spawns:
                spawns[pokemon_id] = []
            if newspawns is not None:
                added, removed = diff(spawns[pokemon_id], newspawns)
                logging.debug("added: {added}".format(added=added))
                logging.debug("removed: {removed}".format(removed=removed))
                spawns[pokemon_id] = newspawns
            for newspawn in added:
                logging.info("Pokemon {id} spawned at {lat},{lon}, expires in {expires}".format(id=newspawn.pokemon_id,lat=newspawn.lat,lon=newspawn.lon,expires=newspawn.minsRemaining))
                try:
                    location, hood, zip, address = '','','',''
                    try:
                        location = getLocation(newspawn)
                        if 'neighbourhood' in location.raw['address']:
                            hood = location.raw['address']['neighbourhood']
                        else:
                            hood = location.raw['address']['city']
                        zip = location.raw['address']['postcode']
                        if 'house_number' in location.raw['address']:
                            address = "{hn} {road}".format(hn=location.raw['address']['house_number'],road=location.raw['address']['road'])
                    except Exception as e:
                        logging.error("FUCK {e}".format(e=e))
                    message = "{name} spawned in {hood} ({zip}), available for {expires} minutes. {address} {link}".format(link=getMapLink(newspawn),address=address,hood=hood,zip=zip,name=getPokemonName(newspawn.pokemon_id),expires=newspawn.minsRemaining)
                    for number in config['destinations']:
                        logging.info('Sending "{message}" to {number}...'.format(message=message,number=number))
                        #twilio.send_message(message,number)
                except Exception as e:
                    logging.error("FUCK {e}".format(e=e))
            for spawn in removed:
                pass
            time.sleep(1)
        time.sleep(10)

    
    
def diff(old, new):
    added = list(set(new) - set(old))
    removed = list(set(old) - set(new))   
    return filter(None,added), filter(None,removed)    

if __name__ == "__main__":
    main()