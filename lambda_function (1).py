"""
redirect: GET /{code}
Looks the code up in DynamoDB and answers with a 302 redirect to the original URL.

Environment variables:
  TABLE_NAME  (required)  DynamoDB table name, e.g. "short-links"
"""
import os
import re

import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{4,12}$")

NOT_FOUND_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Link not found</title>
<style>body{font-family:system-ui,sans-serif;max-width:32rem;margin:15vh auto;padding:0 1.5rem;color:#14213d}</style>
</head><body><h1>Link not found</h1>
<p>This short link doesn’t exist or was typed incorrectly. Check the address and try again.</p>
</body></html>"""


def not_found():
    return {
        "statusCode": 404,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": NOT_FOUND_PAGE,
    }


def lambda_handler(event, context):
    code = (event.get("pathParameters") or {}).get("code", "")
    if not CODE_PATTERN.match(code):
        return not_found()

    item = table.get_item(Key={"code": code}).get("Item")
    if not item:
        return not_found()

    # Count the visit. A failure here should never block the redirect.
    try:
        table.update_item(
            Key={"code": code},
            UpdateExpression="ADD clicks :one",
            ExpressionAttributeValues={":one": 1},
        )
    except Exception as err:
        print("Click count failed:", err)

    return {
        "statusCode": 302,
        "headers": {
            "Location": item["url"],
            # 302 + no-store so browsers ask us every time and clicks get counted.
            "Cache-Control": "no-store",
        },
        "body": "",
    }
