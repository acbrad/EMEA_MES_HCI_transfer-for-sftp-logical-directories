# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Custom resource handler for the AWS SFTP Logical Directories blog post.
This code will generate a folder structure in two S3 buckets specific to the
needs of the blog post.  Much of the helper code was pulled directory from the
the custom-resource-helper code at https://github.com/aws-cloudformation/custom-resource-helper.
We did not use the CfnResource code deliberately so we could keep the Lambda
function lightweight.
"""

import logging
import os
import boto3
import json
import time
import random
import string
import urllib3
#from botocore.vendored import requests

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

ACTION_CREATE = "Create"
ACTION_UPDATE = "Update"
ACTION_DELETE = "Delete"

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"

def _send_response(response_url, response_body):
    try:
        json_response_body = json.dumps(response_body)
    except Exception as e:
        msg = "Failed to convert response to json: {}".format(str(e))
        logger.error(msg, exc_info=True)
        response_body = {'Status': 'FAILED', 'Data': {}, 'Reason': msg}
        json_response_body = json.dumps(response_body)
    logger.debug("CFN response URL: {}".format(response_url))
    logger.debug(json_response_body)
    headers = {'content-type': '', 'content-length': str(len(json_response_body))}
    http = urllib3.PoolManager()
    while True:
        try:
##            response = put(response_url, data=json_response_body, headers=headers)
            response = http.request(method="PUT", url=response_url, body=json_response_body, headers=headers)
            logger.info("CloudFormation returned status code: {}".format(response.reason))
            print ("CloudFormation returned status code: {}".format(response.reason))
            break
        except Exception as e:
            logger.error("Unexpected failure sending response to CloudFormation {}".format(e))
            print ("Unexpected failure sending response to CloudFormation {}".format(e))
            time.sleep(5)

def _rand_string(l):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(l))

def _gen_physical_resource_id(event):
    if "PhysicalResourceId" in event.keys():
        logger.info("PhysicalResourceId present in event, Using that for response")
        return event['PhysicalResourceId']
    else:
        logger.info("No physical resource id returned, generating one...")
        return event['StackId'].split('/')[1] + '_' + event['LogicalResourceId'] + '_' + _rand_string(8)

def _process(event, context, action):

    public_research_bucket = os.environ['public_research']
    subscriptions_bucket = os.environ['subscriptions']

    files = [
        [public_research_bucket, 'global/document1.txt'],
        [public_research_bucket, 'global/northamer/document1-northamer.txt'],
        [public_research_bucket, 'global/northamer/document2-northamer.txt'],
        [public_research_bucket, 'global/southamer/document1-southamer.txt'],
        [subscriptions_bucket, 'historical/2018/indices/index1-2018.txt'],
        [subscriptions_bucket, 'historical/2018/indices/index2-2018.txt'],
        [subscriptions_bucket, 'historical/2018/equities/equity1-2018.txt'],
        [subscriptions_bucket, 'historical/2019/credit/credit1-2019.txt'],
        [subscriptions_bucket, 'historical/2019/equities/equity1-2019.txt'],
        [subscriptions_bucket, 'historical/2019/equities/equity2-2019.txt'],
        [subscriptions_bucket, 'historical/2019/indices/index1-2019.txt'],
        [subscriptions_bucket, 'historical/2019/indices/index2-2019.txt'],
        [subscriptions_bucket, 'historical/2019/indices/index3-2019.txt'],
    ]

    s3 = boto3.client('s3')

    if action == ACTION_CREATE:
        file_text = "Test data generated by CloudFormation stack %s. These objects will be automatically deleted on stack cleanup." % event['StackId']
        for bucket, key in files:
            print ("Putting data to s3://{}/{}".format (bucket, key))
            s3.put_object(Bucket=bucket, Key=key, Body=file_text)
    elif action == ACTION_DELETE:
        for bucket, key in files:
            s3.delete_object(Bucket=bucket, Key=key)

    response_body = {
        'Status': STATUS_SUCCESS,
        'PhysicalResourceId': _gen_physical_resource_id(event),
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Reason': "",
        'Data': {},
    }
    print ("Sending SUCCESS response back to cloudformation ResposeURL")
    _send_response(event['ResponseURL'], response_body)

def handler(event, context):
    logger.debug(event)
    try:
        _process(event, context, event['RequestType'])
    except Exception as e:
        msg = "Failed to process custom resource event: {}".format(str(e))
        logger.error(msg, exc_info=True)
        response_body = {'Status': STATUS_FAILED, 'Data': {}, 'Reason': msg}
        ## send response back to cloud formation caller in case of Exception
        _send_response(event['ResponseURL'], response_body)

