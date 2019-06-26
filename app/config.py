import os
import boto3
URL = os.environ['URL']
API_TITLE = os.environ['API_TITLE']
API_DESCRIPTION = os.environ['API_DESCRIPTION']
SPACES = boto3.session.Session().client('s3',
                        region_name=os.environ['REGION_NAME'],
                        endpoint_url=os.environ['ENDPOINT_URL'],
                        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'])
BUCKET = os.environ['BUCKET']

