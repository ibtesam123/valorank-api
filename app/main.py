from flask import Flask, request, jsonify
import json
import time
from .valAPI import ValorantAPI
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["30 per hour", "15 per minute", "2 per second"],
)

maps = {
    '/Game/Maps/Duality/Duality': 'bind',
    '/Game/Maps/Bonsai/Bonsai': 'split',
    '/Game/Maps/Ascent/Ascent': 'ascent',
    '/Game/Maps/Port/Port': 'icebox',
    '/Game/Maps/Triad/Triad': 'haven',
    '': 'unknown'
}

match_movement_hash = {
    'INCREASE': ['Increase', 'Victory'],
    'MINOR_INCREASE': ['Minor Increase', 'Victory'],
    'MAJOR_INCREASE': ['Major Increase', 'Victory'],
    'DECREASE': ['Decrease', 'Defeat'],
    'MAJOR_DECREASE': ['Major Decrease', 'Defeat'],
    'MINOR_DECREASE': ['Minor Decrease', 'Defeat'],
    'PROMOTED': ['Promoted', 'Victory'],
    'DEMOTED': ['Demoted', 'Defeat'],
    'STABLE': ['Stable', 'Draw']
}


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'success': False, 'message': 'Rate limit exceeded'})


@app.route('/', methods=['GET'])
def hello():
    return jsonify({'success': True, 'message': 'Hello World'})


@app.route('/matches', methods=['POST'])
def getmatches():

    username = request.json['username']
    password = request.json['password']
    region = request.json['region']

    # Get client ip
    try:
        client_ip = request.headers.getlist('X-Forwarded-For')[0]
    except:
        print('Unknown ip address')
        client_ip = request.remote_addr

    # Attempt Login
    try:
        valorant = ValorantAPI(username, password, region, client_ip)
    except:
        return jsonify({'success': False, 'message': 'Login Error'})

    # Attempt to get the match history
    try:
        json_res = valorant.get_match_history()
    except:
        return jsonify({'success': False, 'message': 'Cannot get matches'})

    # Parse match data
    try:
        matches = []
        for match in json_res['Matches']:
            if match['CompetitiveMovement'] == 'MOVEMENT_UNKNOWN':
                continue

            game_map = maps[match['MapID']]

            match_movement, game_outcome = match_movement_hash[
                match['CompetitiveMovement']]

            tier = match['TierAfterUpdate']

            before = match['TierProgressBeforeUpdate']
            after = match['TierProgressAfterUpdate']

            epoch_time = match['MatchStartTime'] // 1000
            date = time.strftime('%m-%d-%Y', time.localtime(epoch_time))

            if match['CompetitiveMovement'] == 'PROMOTED':
                lp_change = '+' + str(after + 100 - before)
            elif match['CompetitiveMovement'] == 'DEMOTED':
                lp_change = '-' + str(before + 100 - after)
            else:
                if before < after:
                    # won
                    lp_change = '+' + str(after - before)
                else:
                    # lost
                    lp_change = str(after - before)

            match_data = {
                'point_change': lp_change,
                'current_point': after,
                'game_outcome': game_outcome,
                'movement': match_movement,
                'tier': tier,
                'date': date,
                'game_map': game_map
            }
            matches.append(match_data)

        return jsonify({'success': True, 'message': matches})
    except:
        return jsonify({'success': False, 'message': 'Cannot get matches'})
