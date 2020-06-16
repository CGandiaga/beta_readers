# -*- coding: utf-8 -*-
import logging
import os
import re
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google_drive_downloader import GoogleDriveDownloader as gdd

import codecs
from pathlib import Path


logging.basicConfig(level=logging.DEBUG)

EMAIL_PATTERN = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
SUBJECT = ["¿Te acuerdas de nosotros?", "¡Más y mejor!"]

ESSAYS = {
    'AL': {
        'id': '1IXMpYoZM-uIIhnlpy1cJ79DW_jDrwH_x',
        'title': 'Tú a Roma y yo a Nueva York'
    },
    'ES': {
        'id': '1cluT5dyjKSTP8iTA0jtr5RZBT-kbWZy3',
        'title': 'Un plátano de 100.000€'
    },
    'HP': {
        'id': '12vGWAA_uBXz0HFUJ43hxr-ZyhtWPwSzj',
        'title': 'Harry Potter y el misterio del más allá'
    },
    'IM': {
        'id': '1brKZyNp3Ua6ckQzV4YXoIEpp3m6TY9HS',
        'title': 'Iron Man, el héroe que llevamos por fuera'
    },
    'KA': {
        'id': '19gk7_I2pnfhUisrcy9_QrCu5tBEW1XSa',
        'title': 'El kit del anarquista'
    },
    'MQ': {
        'id': '1Ks1c6Hvzq9zdBTsUtq0n6zrNI1YHfj2B',
        'title': 'La Mecanica Cuántica os hará libres'
    },
    'NP': {
        'id': '1tmHWV9hhj9BeDzpdVefDX6QZpOjB5ncH',
        'title': 'Netflix VS Platón'
    },
}

MESSAGES = []
def concatenate_list_data(list):
    result= ''
    for element in list:
        result += str(element)
    return result

for i in range (1, 3):
    body_path = f'html_templates/body_{i}.html'
    with open(body_path, 'r') as template_html:
        message_list = template_html.readlines()
    MESSAGES.append(concatenate_list_data(message_list))

class InvalidMailAddressError(Exception):
    pass

def send_email(destinations, subject, message, files=None, origin=None):
    """Función para enviar emails.

    Args:
        destinations (str or list of str): email or emails to sent the email to.
        subject (str): subject of the email.
        message (str): message of the email. Can be written in html.
        files (str or list of str, optional): Entire filepath or list of filepaths to
            include in the email. Defaults to None.
        origin (str, optional): Alias to be shown in the email. Defaults to None.

    Raises:
        InvalidMailAddressError: if some destinations are invalid.
        TypeError: if destinations is neither a str nor a list of strings.

    Returns:
        bool: True if the email was sent sucessfully, False otherwise.
    """

    logger = logging.getLogger(__name__)
    logger.debug("Sending mail %r to %r", subject, destinations)

    if isinstance(destinations, (list, tuple)):
        for address in destinations:
            if EMAIL_PATTERN.search(address) is None:
                logger.critical("%r is not a valid email address", address)
                raise InvalidMailAddressError(
                    f"{address!r} is not a valid email address."
                )
        destinations = ", ".join(destinations)

    if not isinstance(destinations, str):
        logger.critical("destinations must be iterable or str.")
        raise TypeError("destinations must be iterable or str.")

    if not EMAIL_PATTERN.search(destinations):
        logger.critical("%r is not a valid email address", destinations)
        raise InvalidMailAddressError(f"{destinations!r} is not a valid email address.")

    password = ''
    username = ''

    msg = MIMEMultipart()
    msg['From'] = f'{origin} <{username}>' if origin else username
    msg['To'] = destinations
    msg['Subject'] = subject

    # body = message.replace("\n", "<br>")
    body = message
    msg.attach(MIMEText(body, "html"))

    if files:
        for file in files:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(Path(file).read_bytes())
            encoders.encode_base64(part)
            filename = file.split('/')[1]
            part.add_header(
                "Content-Disposition", "attachment", filename=filename
            )
            msg.attach(part)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(username, password)
    server.sendmail(username, msg["To"], msg.as_string())
    server.quit()
    return True

def get_data_from_spreadsheet(filename: str, credentials_file: str):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
    client = gspread.authorize(creds)
    sheet = client.open(filename).sheet1
    return sheet.get()

def get_files():
    for item in ESSAYS:
        gdd.download_file_from_google_drive(file_id = ESSAYS[item]['id'],
                                            dest_path = f'./data/{ESSAYS[item]["title"]}.pdf')

def pretty_print(d, indent=0):
   for key, value in d.items():
      print('    - ' * indent + str(key))
      if isinstance(value, dict):
         pretty_print(value, indent+1)
      else:
         print('     ' * (indent+1) + str(value))

def template(beta_reader, n_essays):
    message_str = MESSAGES[n_essays - 1]
    message = message_str.replace("var_to_change_nombre", beta_reader.title())

    # if n_essays == 2:
    #     message = message_str.replace("var_to_change_nombre", beta_reader.title())
    #     message = message_str.replace("var_to_change_nombre", beta_reader.title())
    return message

if __name__ == "__main__":
    data = get_data_from_spreadsheet('NL1', 'beta_readers.json')
    get_files()

    print(data)
    beta_readers = {}
    for column in data:
        beta_readers.update({column[0].strip().title(): {'email': column[1].strip(), 'essays_number': len(column) - 2, 'essays': column[2:]}})

    pretty_print(beta_readers)

    for beta_reader in beta_readers:
        message = template(beta_reader, beta_readers[beta_reader]['essays_number'])

        files_to_send = []
        for item in beta_readers[beta_reader]['essays']:
            files_to_send.append(f'data/{ESSAYS[item]["title"]}.pdf')
        try:
            send_email(beta_readers[beta_reader]['email'], SUBJECT[beta_readers[beta_reader]['essays_number'] - 1], message, files = files_to_send, origin='Filosofía para Millennials')
        except:
            print("An exception occurred with ", beta_reader.title(), " - ", beta_readers[beta_reader]['email'])
