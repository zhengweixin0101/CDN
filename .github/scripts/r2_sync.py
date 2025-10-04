import os
import boto3
import shutil

ACCESS_KEY_ID = os.environ['R2_ACCESS_KEY_ID']
SECRET_ACCESS_KEY = os.environ['R2_SECRET_ACCESS_KEY']
ACCOUNT_ID = os.environ['R2_ACCOUNT_ID']
BUCKET_NAME = os.environ['R2_BUCKET_NAME']

R2_ENDPOINT = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

session = boto3.session.Session()
client = session.client(
    's3',
    region_name='auto',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
)

def sync_bucket():
    for item in os.listdir('.'):
        if item in ('.git', '.github'):
            continue
        if os.path.isdir(item):
            shutil.rmtree(item)
        else:
            os.remove(item)
            
    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.startswith('.github/'):
                continue
            if '/' in key:
                os.makedirs(os.path.dirname(key), exist_ok=True)
            with open(key, 'wb') as f:
                client.download_fileobj(BUCKET_NAME, key, f)

if __name__ == "__main__":
    sync_bucket()
