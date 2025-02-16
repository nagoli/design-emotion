# Design Transcript Processor

A serverless solution for analyzing design meeting transcripts using AWS Textract and Comprehend.

## Features
- PDF transcript processing with Amazon Textract
- Sentiment analysis using Amazon Comprehend
- Automatic S3 bucket integration for file storage
- Lambda function deployment ready

## Prerequisites
- AWS CLI configured with proper permissions
- Python 3.8+
- Required packages (see [requirements.txt](./aws/requirements.txt))

## Installation
```bash
git clone https://github.com/your-repo/design-emotion.git
cd design-emotion/aws
pip install -r requirements.txt
```

## Configuration
1. Create S3 buckets for input/output
2. Set environment variables in Lambda:
   - `INPUT_BUCKET`
   - `OUTPUT_BUCKET`
   - `AWS_REGION`

## Deployment
1. Package Lambda function:
```bash
zip -r function.zip design_transcript.py
```
2. Create Lambda function with Python 3.8 runtime
3. Configure S3 trigger for input bucket

## Example Transcript
```
[Design Review 2025-02-16]
Participant A: I'm concerned about the color scheme accessibility
Participant B: Let's run contrast checks on the primary palette
```

## License
MIT License
