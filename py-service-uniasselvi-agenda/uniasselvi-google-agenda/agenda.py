import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


mail_one = "oliveiramaxsuellll@gmail.com"


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly' ,'https://www.googleapis.com/auth/calendar' , 'https://www.googleapis.com/auth/calendar.events']

def inner(service, datas):
    
    print("Todos meus eventos já cadastrado.")
    print(data['summary'])
    # Procurando se o evento já está cadastrado na minha agenda.

    # Buscando o nome dos eventos.

    for data in datas:
       
        event = {
            'summary': data['summary'],
            # 'location': '800 Howard St., San Francisco, CA 94103',
            'location' : '',
            'description': data['description'],
            'start': {
                'dateTime': data['start_dateTime'],
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': data['end_dateTime'],
                'timeZone': 'America/Sao_Paulo',
            },
            'recurrence': [
                'RRULE:FREQ=DAILY;COUNT=1'
            ],
            'attendees': [
                {'email': mail_one},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                # {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 24 * 60}
                ],
            },
        }

        # Criando eventos
        event = service.events().insert(calendarId='primary', body=event).execute()
        print('Evento criado, acesse em : %s' % (event.get('htmlLink')))
   
def get(service):
    
    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Recebendo os próximos 10 eventos')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                            maxResults=10, singleEvents=True,
                                            orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('Nenhum evento próximo encontrado.')
        return

    # Prints the start and name of the next 10 events
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

def main(datas):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
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
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        # get(service)
        
        # criando evento
        inner(service , datas)



    except HttpError as error:
        print('An error occurred: %s' % error)


if __name__ == '__main__':
    main()