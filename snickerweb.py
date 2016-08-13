# -*- coding: utf-8 -*-
from datetime import datetime
import argparse
import json

import requests
from flask import Flask, request, render_template
from flask_googlemaps import GoogleMaps
from flask_googlemaps import Map
from flask_googlemaps import icons
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import config as app_config
from worker import Slave
import db
import dbmore
import utils
import logging
import web

app = web.app

@app.route('/')
def snickerweb_fullmap():
    map_center = utils.get_map_center()
    return render_template(
        'newmap2.html',
        area_name=web.config.AREA_NAME,
        map_center=map_center,
    )

@app.route('/data/rares')
def rare_pokemon_data():
    return json.dumps(get_rare_pokemarkers())

@app.route('/data/pokemon')
def data_pokemon_only():
    return json.dumps(get_pokemarkers_for_pokemon())

@app.route('/data/forts')
def data_forts_only():
    return json.dumps(get_pokemarkers_for_forts())
    
@app.route('/data/pokemon/<int:pokemon_id>')
def bypokemon_data(pokemon_id):
    return json.dumps(get_pokemarkers_for_pokemon(pokemon_id))

def normalize_pokemon(hookdata): #this needs some data validation because evil endpoints
    return {
        'encounter_id': hookdata['encounter_id'],
        'spawn_id': hookdata['spawnpoint_id'],
        'pokemon_id': hookdata['pokemon_id'],
        'expire_timestamp': hookdata['disappear_time'],
        'lat': hookdata['latitude'],
        'lon': hookdata['longitude']
    }

@app.route('/hook',methods=['POST'])
def webhook():
    hookreq = request.get_json(force=True)
    if hookreq:
        if 'type' in hookreq:
            if hookreq['type'] == 'pokemon':
                sesh = db.Session()
                pokemon = normalize_pokemon(hookreq['message'])
                logging.info("Got {pokemon} from hook".format(pokemon=pokemon))
                db.add_sighting(sesh,pokemon) #this is dangerous
                sesh.commit()
                sesh.close()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/rarespawns')
def rarespawns():
    map_center = utils.get_map_center()
    return render_template(
        'newmap2.html',
        area_name=app_config.AREA_NAME,
        map_center=map_center,
        more_title="Rare Spawns",
        endpoint='/data/rares'
    )

@app.route('/<int:pokemon_id>')
def currentspawns(pokemon_id):
    map_center = utils.get_map_center()
    pokemon_name = web.POKEMON_NAMES[pokemon_id]
    return render_template(
        'newmap2.html',
        area_name=app_config.AREA_NAME,
        map_center=map_center,
        more_title=" - {} Spawns".format(pokemon_name),
        endpoint='/data/pokemon/' + str(pokemon_id)
    )

def get_rare_pokemarkers():
    session = db.Session()
    pokemons = dbmore.getRareSpawns(session)
    session.close()
    return get_pokemarkers(pokemons=pokemons)

def get_pokemarkers_for_pokemon(pokemon_id=None):
    session = db.Session()
    pokemons = dbmore.getCurrentSpawns(session,pokemon_id=pokemon_id)
    session.close()
    return get_pokemarkers(pokemons=pokemons)
    
def get_pokemarkers_for_forts(fort_id=None):
    session = db.Session()
    forts = db.get_forts(session)
    session.close()
    return get_pokemarkers(forts=forts)

def get_pokemarkers(pokemons={},forts={}):
    markers = []

    for pokemon in pokemons:
        markers.append({
            'id': 'pokemon-{}'.format(pokemon.id),
            'type': 'pokemon',
            'trash': pokemon.pokemon_id in app_config.TRASH_IDS,
            'name': web.POKEMON_NAMES[pokemon.pokemon_id],
            'pokemon_id': pokemon.pokemon_id,
            'lat': pokemon.lat,
            'lon': pokemon.lon,
            'expires_at': pokemon.expire_timestamp,
        })
    for fort in forts:
        if fort['guard_pokemon_id']:
            pokemon_name = web.POKEMON_NAMES[fort['guard_pokemon_id']]
        else:
            pokemon_name = 'Empty'
        markers.append({
            'id': 'fort-{}'.format(fort['fort_id']),
            'sighting_id': fort['id'],
            'type': 'fort',
            'prestige': fort['prestige'],
            'pokemon_id': fort['guard_pokemon_id'],
            'pokemon_name': pokemon_name,
            'team': fort['team'],
            'lat': fort['lat'],
            'lon': fort['lon'],
        })

    return markers

def get_pokemarkers_old(pokemons):
    markers = []

    for pokemon in pokemons:
        name = web.pokemon_names[str(pokemon.pokemon_id)]
        datestr = datetime.fromtimestamp(pokemon.expire_timestamp)
        dateoutput = datestr.strftime("%H:%M:%S")

        LABEL_TMPL = u'''
<div><b>{name}</b><span> - </span><small><a href='http://www.pokemon.com/us/pokedex/{id}' target='_blank' title='View in Pokedex'>#{id}</a></small></div>
<div>Disappears at - {disappear_time_formatted} <span class='label-countdown' disappears-at='{disappear_time}'></span></div>
<div><a href='https://www.google.com/maps/dir/Current+Location/{lat},{lng}' target='_blank' title='View in Maps'>Get Directions</a></div>
'''
        label = LABEL_TMPL.format(
            id=pokemon.pokemon_id,
            name=name,
            disappear_time=pokemon.expire_timestamp,
            disappear_time_formatted=dateoutput,
            lat=pokemon.lat,
            lng=pokemon.lon,
        )
        #  NOTE: `infobox` field doesn't render multiple line string in frontend
        label = label.replace('\n', '')

        markers.append({
            'type': 'pokemon',
            'name': name,
            'key': '{}-{}'.format(pokemon.pokemon_id, pokemon.spawn_id),
            'disappear_time': pokemon.expire_timestamp,
            'icon': 'static/icons/%d.png' % pokemon.pokemon_id,
            'lat': pokemon.lat,
            'lng': pokemon.lon,
            'pokemon_id': pokemon.pokemon_id,
            'infobox': label
        })

    return markers
    
if __name__ == '__main__':
    args = web.get_args()
    #from gevent.wsgi import WSGIServer
    #http_server = WSGIServer((args.host, args.port), app)
    #http_server.serve_forever()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'fullmap':
            rule.endpoint = 'snickerweb_fullmap'
            rule.refresh()
    print(app.url_map)
    app.run(threaded=True, host=args.host, port=args.port)