"""Helper Functionality"""
from copy import deepcopy
import urlparse
import os
import json
import logging
import requests

# Annoyingness
try:
    import locale
    locale.setlocale(locale.LC_ALL, 'en_US.utf8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        logging.error('An error occurred')

def update_dictionary(diction, _id, new_value):
    '''Update dictionary'''
    for key, value in diction.iteritems():
        if key == _id:
            diction[key] = new_value
        elif isinstance(value, dict):
            diction[key] = update_dictionary(value, _id, new_value)
    return diction

def format_one(single):
    '''format_one'''
    return locale.currency(round(float(single), 2), symbol=False, grouping=True)

def format_everything(orig_dict):
    '''Format everything'''
    diction = deepcopy(orig_dict)
    for key, value in diction.iteritems():
        if isinstance(value, (int, long, float, complex)):
            if key not in ["zpid", "property_id"]:
                diction[key] = locale.currency(round(value, 2),
                                               symbol=False,
                                               grouping=True)
        elif isinstance(value, dict):
            diction[key] = format_everything(value)
    return diction


def float_everything(data):
    '''Convert to float'''
    for key, value in data.iteritems():
        if isinstance(value, (int, long, float, complex)):
            data[key] = float(value)
        elif isinstance(value, dict):
            data[key] = float_everything(value)
    return data


def clean_result(value):
    '''Replace special chars'''
    return float(value.replace('$', '').replace(',', ''))


def get_url(url, part):
    '''Parse url'''
    url_parts = urlparse.urlparse(url)

    if part == 'root':
        url_root = url_parts.scheme + '://' + url_parts.netloc
        return url_root

def represents_int(data):
    '''Check int type'''
    try:
        int(data)
        return True
    except:# pylint: disable=W0702
        return False

def get_current_heroku_release():
    '''Heroku release'''
    app_name = os.environ.get('HEROKU_APP_NAME') \
        if os.environ.get('HEROKU_APP_NAME') else 'unknown'
    release_version = 'unknown'
    url = 'https://api.heroku.com/apps/%s/releases' % (app_name)
    headers = {'Accept': 'application/vnd.heroku+json; version=3'}
    result = requests.get(url, headers=headers)
    if result.status_code == 200:
        # pylint: disable=W0212
        app_releases = json.loads(result._content)
        applen = len(app_releases)
        if applen:
            last_app_release = app_releases[applen - 1]
            release_version = last_app_release['version']
    return release_version

def get_date_suffix(create_day):
    '''get_date_suffix'''
    create_day = int(create_day)
    if 4 <= create_day <= 20 or 24 <= create_day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][create_day % 10 - 1]
    return suffix

def get_coordinate_from_address(address):
    '''get_coordinate_from_address'''
    try:
        response = requests.get('https://maps.googleapis.com/maps/api/'\
            'geocode/json?address=%s' % (address))
        resp_json_payload = response.json()
        return resp_json_payload['results'][0]['geometry']['location']
    except requests.exceptions.RequestException:
        return

#Phuc Do - 20173105
def update_release_with_sentry(app_values):
    """Release with sentry"""
    sentry_url_release = 'https://sentry.io/api/0/organizations/%s/releases/' \
        % (app_values['SENTRY_ORG'])
    headers = {'Authorization': 'Bearer ' + app_values['SENTRY_AUTH_TOKEN'],
               'Accept': 'application/json'}
    data = {
        'version': app_values['RAVEN'],
        'refs': [
            {
                'repository': str(app_values['REPOSITORY']),
                'commit': str(app_values['RAVEN'])
            }
        ],
        'projects': [app_values['SENTRY_PROJECT']]
    }
    try:
        requests.post(sentry_url_release, json=data, headers=headers)
    except:# pylint: disable=W0702
        return

#Phuc Do - 20171206
def format_currency(value):
    return locale.currency(round(value, 2),
                                   symbol=False,
                                   grouping=True)

#phuc Do - 20172506
def cal_color(score):
    """Calculate color for school map"""
    """100 => Green 0,255,0
    75 => Yellow 255,255,0
    50 => Orange 255,140,0
    0 => Red 255,0,0"""

    if score == 0:
        return '#000000'
    elif score > 0 and score < 20: # Red
        return '#cd3333'
    elif score >=20 and score < 40: # red -> orange
        return '#d77900'
    elif score >=40 and score < 60: # orange -> yellow
        return '#d7b600'
    elif score >=60 and score < 80: # yellow -> green
        return '#6d9521'
    elif score >= 80: # green
        return '#4c762e'
