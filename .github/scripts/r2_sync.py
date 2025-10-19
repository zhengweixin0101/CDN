import os
import boto3
import hashlib

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

def file_md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_local_files():
    local_files = {}
    for root, dirs, files in os.walk('.'):
        # 跳过 .git 和 .github 文件夹
        rel_root = os.path.relpath(root, '.')
        if rel_root == '.git' or rel_root.startswith('.git' + os.sep):
            continue
        if rel_root == '.github' or rel_root.startswith('.github' + os.sep):
            continue
        for file in files:
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, '.')
            local_files[rel_path] = file_md5(path)
    return local_files

def get_r2_files():
    r2_files = {}
    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.startswith('.github/') or key.endswith('.gitattributes'):
                continue
            r2_files[key] = obj['ETag'].strip('"')
    return r2_files

def sync_bucket():
    local_files = get_local_files()
    r2_files = get_r2_files()

    for path in local_files:
        if path not in r2_files:
            os.remove(path)

    for key, etag in r2_files.items():
        need_sync = False
        if key not in local_files:
            need_sync = True
        elif local_files[key] != etag:
            need_sync = True
        if need_sync:
            if '/' in key:
                os.makedirs(os.path.dirname(key), exist_ok=True)
            with open(key, 'wb') as f:
                client.download_fileobj(BUCKET_NAME, key, f)

if __name__ == "__main__":
    sync_bucket()
