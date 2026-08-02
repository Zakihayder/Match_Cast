import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

endpoint = os.getenv('B2_S3_ENDPOINT') or 'https://s3.us-east-005.backblazeb2.com'
key_id = os.getenv('B2_APPLICATION_KEY_ID') or ''
app_key = os.getenv('B2_APPLICATION_KEY') or ''
bucket = os.getenv('B2_BUCKET_NAME') or ''

print('Endpoint:', endpoint)
print('Key ID prefix:', (key_id or '')[:16] + '...')
print('Key ID length:', len(key_id))
print('App key length:', len(app_key))
print('Bucket:', bucket)

try:
    s3 = boto3.client('s3', endpoint_url=endpoint,
                      aws_access_key_id=key_id,
                      aws_secret_access_key=app_key,
                      region_name=None)
    resp = s3.list_buckets()
    names = [b['Name'] for b in resp.get('Buckets', [])]
    print('Success: listed', len(names), 'buckets')
    print('Buckets:', names)
except ClientError as e:
    print('ClientError:', e)
except Exception as e:
    print('Error:', e)

# If the key is bucket-scoped it may not be allowed to list all buckets.
# Try listing objects in the configured bucket as a scoped-key friendly test.
if bucket:
    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix='', MaxKeys=10)
        objs = [o['Key'] for o in resp.get('Contents', [])]
        print(f"Objects in bucket '{bucket}':", objs)
    except ClientError as e:
        print('Bucket-level ClientError:', e)
    except Exception as e:
        print('Bucket-level Error:', e)

    # Try a small put_object (non-multipart) to verify write permission.
    try:
        key_name = 'diagnose/test_put.txt'
        s3.put_object(Bucket=bucket, Key=key_name, Body=b'hello from diagnose')
        print('PutObject succeeded for', key_name)
        resp = s3.list_objects_v2(Bucket=bucket, Prefix='diagnose/', MaxKeys=10)
        print('Diagnose objects:', [o['Key'] for o in resp.get('Contents', [])])
    except ClientError as e:
        print('PutObject ClientError:', e)
    except Exception as e:
        print('PutObject Error:', e)
