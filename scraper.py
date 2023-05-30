from __future__ import print_function

import os.path
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import html2text
import requests
import datetime

SCOPES = ['https://www.googleapis.com/auth/documents']

DOCUMENT_ID = '14JuTNkqzHb5_GIpq6a1edRyS17GT1L-eVYWi70GuZYU'


def verify():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('docs', 'v1', credentials=creds)


def get_doc_text(service):
    try:
        # Retrieve the documents contents from the Docs service.
        doc = service.documents().get(documentId=DOCUMENT_ID).execute()
        # Extract the text content from the document
        content = doc['body']['content']
        # Iterate over the elements and extract the text
        text = ''
        for element in content:
            if 'paragraph' in element:
                elements = element['paragraph']['elements']
                for el in elements:
                    text += el['textRun']['content']
        return text
    except HttpError as err:
        print(err)


def date_is_written(time, doc_text):
    time = time.strftime("%B %-d, %Y")
    lines = doc_text.splitlines()
    for line in lines:
        if line == time:
            return True
    return False


def get_oldest_date(date, doc_text):
    if date_is_written(date, doc_text):
        return date + datetime.timedelta(days=1)
    return get_oldest_date(date - datetime.timedelta(days=1), doc_text)


def scrape_website(time):
    response = requests.get('https://theweek.com/daily-briefing')
    text = response.text
    text = text.split('href="')
    time = datetime.datetime.now()
    date = time.strftime("%B-%-d-%Y").lower()
    text = [t for t in text if t.startswith('/briefing')
            and t.find(date) != -1]
    text = text[0]
    if len(text) == 0:
        print("Article not found for date: {}", time.strftime("%m-%d-%y"))
        return
    url = 'https://theweek.com' + text[0:text.find('"')]
    response = requests.get(url)
    text = html2text.html2text(response.text)
    text = text[text.find("Daily briefing"):]
    text = text.replace("Skip advert", "")
    text = text[:text.find('[Share on Facebook]')]
    return text


def update_doc(service):
    requests = []
    date = get_oldest_date(datetime.datetime.today(), get_doc_text(service))
    while date <= datetime.datetime.today():
        text = scrape_website(date)
        requests.append(
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': text
                }
            }
        )
        date += datetime.timedelta(days=1)
        time.sleep(1.1)
    if len(requests) == 0:
        print('Document is up to date!')
        return
    service.documents().batchUpdate(
        documentId=DOCUMENT_ID, body={'requests': requests}).execute()


service = verify()
date = get_oldest_date(datetime.datetime.today(), get_doc_text(service))
update_doc(service)
