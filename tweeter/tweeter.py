from __future__ import print_function
import datetime
import boto3
import io
import json
import requests
from requests_oauthlib import OAuth1

token_table = boto3.resource('dynamodb').Table('daysuntil_users')

s3 = boto3.client('s3')
buf = io.BytesIO()
s3.download_fileobj('daysuntilreinvent-config', 'config.json', buf)
creds = json.loads(buf.getvalue())

reinvent = datetime.date(2016, 11, 28)
today = datetime.date.today()
diff = reinvent - today

status = """\
Only {} days until @AWSreInvent #RoadToReInvent!! https://reinvent.awsevents.com/
""".format(diff.days)
new_user_status = """\
I just joined http://daysuntilreinvent.com! Only {} @AWSreInvent #RoadToReInvent!! https://reinvent.awsevents.com/
""".format(diff.days)


def dynamo_triggered_new_users(event):
    tweeters = []
    for record in event.get('Records', []):
        if record['eventName'] == "INSERT":
            dynamo_event = record.get('dynamodb')
            tweeters.append({
                'oauth_token': dynamo_event['NewImage']['oauth_token']['S'],
                'oauth_token_secret': dynamo_event['NewImage']['oauth_token_secret']['S'],
                'screen_name': dynamo_event['NewImage']['screen_name']['S']
            })
    return tweeters


def lambda_handler(event, context):
    # If being invoked by a dynamodb trigger
    if 'Records' in event:
        tweeters = dynamo_triggered_new_users(event)
        status = new_user_status
    else:  # If being invoked by the cron we scan the table
        tweeters = token_table.scan()['Items']

    for tweeter in tweeters:
        auth = OAuth1(
            creds['CONSUMER_KEY'],
            creds['CONSUMER_SECRET'],
            tweeter['oauth_token'],
            tweeter['oauth_token_secret']
        )
        resp = requests.post(
            "https://api.twitter.com/1.1/statuses/update.json",
            data={'status': status},
            auth=auth
        )
        if status == 200:
            print("Tweeted from " + tweeter['screen_name'])
        else:
            print(resp.text)
