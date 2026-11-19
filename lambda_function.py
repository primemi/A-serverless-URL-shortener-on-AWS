"""
create_link: POST /shorten
Body: {"url": "https://example.com/some/long/path"}
Returns: {"code": "aB3xY9", "shortUrl": "https://<api-id>.execute-api.<region>.amazonaws.com/aB3xY9"}

Environment variables:
  TABLE_NAME  (required)  DynamoDB table name, e.g. "short-links"
  BASE_URL    (optional)  Override the short-link domain, e.g. a custom domain.
"""
import base64
import json
import os
import secrets
import string
import time
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_URL_LENGTH = 2048
MAX_ATTEMPTS = 5


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def parse_body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw) if raw else {}


def is_valid_url(value):
    if not isinstance(value, str) or len(value) > MAX_URL_LENGTH:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def new_code():
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def lambda_handler(event, context):
    try:
        payload = parse_body(event)
    except (ValueError, UnicodeDecodeError):
        return respond(400, {"error": "Request body must be valid JSON."})

    long_url = (payload.get("url") or "").strip()
    if not is_valid_url(long_url):
        return respond(400, {"error": "Enter a full web address starting with http:// or https://."})

    # Insert with a condition so two links can never share a code; retry on a collision.
    code = None
    for _ in range(MAX_ATTEMPTS):
        candidate = new_code()
        try:
            table.put_item(
                Item={
                    "code": candidate,
                    "url": long_url,
                    "createdAt": int(time.time()),
                    "clicks": 0,
                },
                ConditionExpression="attribute_not_exists(code)",
            )
            code = candidate
            break
        except ClientError as err:
            if err.response["Error"]["Code"] != "ConditionalCheckFailedException":
                print("DynamoDB error:", err)
                return respond(500, {"error": "Couldn't save the link. Try again."})

    if code is None:
        return respond(500, {"error": "Couldn't generate a unique code. Try again."})

    base_url = os.environ.get("BASE_URL") or "https://" + event["requestContext"]["domainName"]
    return respond(201, {"code": code, "shortUrl": f"{base_url.rstrip('/')}/{code}"})
