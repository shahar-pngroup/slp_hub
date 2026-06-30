import smtplib
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, template_folder='templates')

AIRTABLE_TOKEN   = os.getenv('AIRTABLE_SLP2_ACCESS_TOKEN', '')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_SLP2_BASE_ID', '')
NOTIFY_EMAIL     = 'office@pngroup.co.il'
S3_BUCKET        = os.getenv('AWS_S3_BUCKET', '')


def send_email(subject, body, to_email):
    from_email  = 'pngispngis@gmail.com'
    password    = os.getenv('SMTP_PASSWORD', '')
    smtp_server = 'smtp.gmail.com'
    smtp_port   = 587

    msg            = MIMEMultipart()
    msg['From']    = from_email
    msg['To']      = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())


def get_s3_client():
    return boto3.client(
        's3',
        region_name='eu-north-1',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )


@app.route('/chat')
def chat():
    return render_template(
        'chat.html',
        airtable_token=AIRTABLE_TOKEN,
        airtable_base=AIRTABLE_BASE_ID
    )


@app.route('/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400

    file     = request.files['file']
    call_num = request.form.get('call_num', 'unknown')

    try:
        s3       = get_s3_client()
        file_key = f'slp-calls/call_{call_num}_{file.filename}'

        s3.put_object(
            Bucket      = S3_BUCKET,
            Key         = file_key,
            Body        = file.read(),
            ContentType = file.content_type or 'application/octet-stream'
        )

        url = f'https://{S3_BUCKET}.s3.eu-north-1.amazonaws.com/{file_key}'
        return jsonify({'url': url})

    except Exception as e:
        print(f'[upload] Error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/notify', methods=['POST'])
def notify():
    data      = request.get_json()
    slp_name  = data.get('slp_name',  '')
    call_num  = data.get('call_num',  '')
    supporter = data.get('supporter', '')
    slp_issue = data.get('slp_issue', '')

    subject = f'הסוכן {slp_name} השיב לקריאה {call_num}'
    body    = (
        f'שם תומכת: {supporter}\n'
        f'מדובר בקריאה בנושא: {slp_issue}'
    )

    try:
        send_email(subject, body, NOTIFY_EMAIL)
        print(f'[notify] Email sent → {NOTIFY_EMAIL} | קריאה {call_num}')
        return jsonify({'ok': True})
    except Exception as e:
        print(f'[notify] Error: {e}')
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 80))
    print(f'Chat Server → http://localhost:{port}/chat?call_num=XXX')
    app.run(host='0.0.0.0', port=port, debug=False)
