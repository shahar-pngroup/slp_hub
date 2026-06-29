import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import io

load_dotenv()

app = Flask(__name__, template_folder='templates')

AIRTABLE_TOKEN   = os.getenv('AIRTABLE_SLP2_ACCESS_TOKEN', '')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_SLP2_BASE_ID', '')
GDRIVE_FOLDER_ID = '1bfn7erhPHh57gCo_9Q2aoXdD1cVf7-VU'
NOTIFY_EMAIL     = 'shahar@pngroup.co.il'
SERVICE_ACCOUNT_FILE = '/home/ubuntu/slp_hub/service_account.json'


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


def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    return build('drive', 'v3', credentials=creds)


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
        from googleapiclient.http import MediaIoBaseUpload
        service       = get_drive_service()
        file_metadata = {
            'name'   : f'call_{call_num}_{file.filename}',
            'parents': [GDRIVE_FOLDER_ID]
        }
        media = MediaIoBaseUpload(
            io.BytesIO(file.read()),
            mimetype=file.content_type or 'application/octet-stream'
        )
        uploaded = service.files().create(
            body=file_metadata, media_body=media, fields='id,webViewLink'
        ).execute()
        service.permissions().create(
            fileId=uploaded['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        return jsonify({'url': uploaded['webViewLink']})
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
