import sys
sys.path.insert(0, r'C:\SSIS\Prod\Python')

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from Connections.outlook import send_outlook_email
import os
import io

load_dotenv()

app = Flask(__name__, template_folder='templates')

AIRTABLE_TOKEN   = os.getenv('AIRTABLE_SLP2_ACCESS_TOKEN', '')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_SLP2_BASE_ID', '')

GDRIVE_FOLDER_ID = '1bfn7erhPHh57gCo_9Q2aoXdD1cVf7-VU'
CREDENTIALS_PATH = r'C:\SSIS\Prod\Python\connections\credentials_oauth.json'
TOKEN_PATH       = r'C:\SSIS\Prod\Python\connections\token.json'
SCOPES           = ['https://www.googleapis.com/auth/drive.file']

NOTIFY_EMAIL     = 'shahar@pngroup.co.il'  # ← שנה לפי הצורך


def get_drive_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as t:
                t.write(creds.to_json())
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
        media    = MediaIoBaseUpload(
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
        send_outlook_email(
            subject    = subject,
            body       = body,
            to_email   = NOTIFY_EMAIL,
            email_type = 'slp_chat_notify'
        )
        print(f'[notify] Email sent → {NOTIFY_EMAIL} | קריאה {call_num}')
        return jsonify({'ok': True})
    except Exception as e:
        print(f'[notify] Error: {e}')
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('Chat Server → http://localhost:5050/chat?call_num=XXX')
    app.run(host='0.0.0.0', port=5050, debug=False)