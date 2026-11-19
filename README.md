# A-serverless-URL-shortener-on-AWS
Serverless URL shortener on AWS. Paste a long link and get a short one that redirects and counts clicks. A static S3 page calls API Gateway, which triggers Python Lambda functions that store and look up links in DynamoDB, each with a least-privilege IAM policy. Pay-per-use, so it costs almost nothing when idle.
