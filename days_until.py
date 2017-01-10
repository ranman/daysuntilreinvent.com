import os
import urlparse

from flask import Flask, jsonify, request
import requests
from requests_oauthlib import OAuth1

import boto3

dynamodb = boto3.resource('dynamodb')
token_table = dynamodb.Table('daysuntil_users')
auth_table = dynamodb.Table('daysuntil_auth_table')

consumer_key = os.getenv('CONSUMER_KEY')
consumer_secret = os.getenv('CONSUMER_SECRET')
base_url = 'https://api.twitter.com/1.1/'
request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authorize_url = 'https://api.twitter.com/oauth/authenticate'

oauth = OAuth1(consumer_key, client_secret=consumer_secret)

app = Flask(__name__)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', "https://daysuntilreinvent.com")
    response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
    response.headers.add('Access-Control-Allow-Methods', "GET,POST,OPTIONS")
    return response


@app.route('/access_token', methods=['POST'])
def access_token():
    if 'oauth_verifier' not in request.form and 'oauth_token' not in request.form:
        return jsonify({'error': 'malformed request needs oauth_token and oauth_token_secret'}), 400

    oauth_token = request.form['oauth_token']
    oauth_token_secret = auth_table.get_item(Key={'oauth_token': oauth_token})['Item']['oauth_token_secret']
    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        verifier=request.form['oauth_verifier']
    )

    resp = requests.post(access_token_url, auth=auth)

    if resp.status_code != 200:
        auth_table.delete_item(Key={'oauth_token': oauth_token})
        return jsonify({'error': resp.text}), resp.status_code

    parsed_resp = dict(urlparse.parse_qsl(resp.text))
    user_pic_url = requests.get(
        base_url+'users/show.json',
        params={'screen_name': parsed_resp['screen_name']},
        auth=oauth
    ).json()['profile_image_url_https']
    parsed_resp['profile_image_url_https'] = user_pic_url
    token_table.put_item(Item=parsed_resp)
    auth_table.delete_item(Key={'oauth_token': oauth_token})

    return jsonify({
        'screen_name': parsed_resp['screen_name'],
        'profile_image_url_https': parsed_resp['profile_image_url_https']
    })


@app.route('/logout', methods=['POST'])
def logout(params):
    # TODO: actually implement
    token_table.delete(Key=params['oauth_token'])


@app.route('/login')
def login():
    request_token_resp = requests.post(
        url=request_token_url,
        auth=oauth
    )

    if request_token_resp.status_code != 200:
        return jsonify({"error": request_token_resp.text}), request_token_resp.status_code

    parsed_resp = dict(urlparse.parse_qsl(request_token_resp.text))
    auth_table.put_item(
        Item={
            'oauth_token': parsed_resp['oauth_token'],
            'oauth_token_secret': parsed_resp['oauth_token_secret']
        }
    )
    return jsonify(parsed_resp)


if __name__ == '__main__':
    app.run(debug=False)
