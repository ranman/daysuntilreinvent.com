cd tweeter && zip -r -9 ../tweeter.zip . && cd -
aws lambda update-function-code --function-name daysuntilreinvent-tweeter --zip-file fileb://tweeter.zip
