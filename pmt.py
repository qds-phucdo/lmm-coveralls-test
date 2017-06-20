# pylint: disable=C0302
# coding=utf-8
"""Main Module for PMT"""

# PMT Methods
import logging
from functools import wraps
from datetime import datetime, timedelta
import hmac
import hashlib
import time
import sys
import os
from os import path
from os.path import join, dirname
from dotenv import load_dotenv
dotenv_path = join(path.dirname(path.dirname(path.abspath(__file__))+"/"), '.env')
load_dotenv(dotenv_path)
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import urlparse

import redis
import requests
# pylint: disable=W0403
from src.py.zillow import (ajax_search_zpid)
from src.py.helper import (clean_result,
                           format_one,
                           format_everything,
                           get_url,
                           represents_int,
                           update_dictionary,
                           get_current_heroku_release,
                           update_release_with_sentry,
                           get_coordinate_from_address,
                           format_currency,
                           cal_color)
from src.py.property_request import (get_property_info)
#from src.py.housecanary import (do_hc_request)
from src.py.amort import (Loan, calculate_payment)
from src.py.projections import (Projections)
from src.py.pg import PGWriter
from src.py.redissession import RedisSessionInterface
from src.py.stripes import (get_stripe_data,
                            update_card,
                            update_subscription,
                            cancel_membership,
                            get_retrive_customer)
from flask import (Flask, g, json, session,
                   redirect, render_template, request,
                   url_for, Response)
from flask_wtf.csrf import CsrfProtect
from raven.contrib.flask import Sentry
from raven import Client
from hashids import Hashids

# Sys
reload(sys)
#sys.setdefaultencoding("utf-8")

app = Flask(__name__)# pylint: disable=invalid-name
app.config.from_pyfile('src/py/config.py')
#Config release with sentry
if os.environ.get('RELEASE_SENTRY') == "PRODUCTION":
    app.config['SENTRY_CONFIG'] = { 'include_paths': [app.config['SENTRY_PROJECT']],\
        'release': os.environ['HEROKU_SLUG_COMMIT']}

# Import and run Sentry
SENTRY = Sentry()
SENTRY_DSN = os.environ.get('SENTRY_DSN')
SENTRY.init_app(app,
                dsn=SENTRY_DSN,
                logging=True,
                level=logging.ERROR,
                logging_exclusions=("logger1", "logger2"))
# App rebuild: config release tracking sentry with newest heroku release version
SENTRY_CLIENT = Client(dsn=SENTRY_DSN, release=get_current_heroku_release(),
                       environment=os.environ.get('RELEASE_SENTRY'))
# App release with sentry
if os.environ.get('RELEASE_SENTRY') == "PRODUCTION":
    if app.config['SENTRY_ORG'] != "" and app.config['SENTRY_PROJECT'] != "" \
            and app.config['REPOSITORY'] != "" \
            and app.config['SENTRY_AUTH_TOKEN'] != "":
        APP_VALUES = {
            'SENTRY_ORG': app.config['SENTRY_ORG'],
            'SENTRY_PROJECT': app.config['SENTRY_PROJECT'],
            'REPOSITORY': app.config['REPOSITORY'],
            'SENTRY_AUTH_TOKEN': app.config['SENTRY_AUTH_TOKEN'],
            'RAVEN': os.environ['HEROKU_SLUG_COMMIT']
        }
        update_release_with_sentry(APP_VALUES)

# Redis session storage
SESSION_REDIS = urlparse.urlparse(os.environ.get('REDISCLOUD_URL'))
REDIS_POOL = redis.ConnectionPool(
    host=SESSION_REDIS.hostname,
    port=SESSION_REDIS.port,
    password=SESSION_REDIS.password
)
REDIS_STORAGE = redis.Redis(connection_pool=REDIS_POOL)
app.session_interface = RedisSessionInterface(redis=REDIS_STORAGE,
                                              prefix='session:')

# Auth0 configuration
AUTH0 = {
    'AUTH0_CLIENT_ID': os.environ.get('AUTH0_CLIENT_ID'),
    'AUTH0_CLIENT_SECRET': os.environ.get('AUTH0_CLIENT_SECRET'),
    'AUTH0_DOMAIN': os.environ.get('AUTH0_DOMAIN'),
    'AUTH0_CALLBACK_URL': ''
}


CSRF = CsrfProtect()
CSRF.init_app(app)

PG = PGWriter()


@app.before_request
def before_request():
    """For base anonymous users"""
    handle_anon()

    handle_user_context()

    handle_heroku_release_on_redis()

    passthrough_conditions = [
        request.is_secure,
        request.headers.get('X-Forwarded-Proto', 'http') == 'https',
        'localhost' in request.url,
        '0.0.0.0' in request.url
    ]

    # Always use SSL, just not on dev
    if not any(passthrough_conditions):
        if request.url.startswith('http://'):
            url = request.url.replace('http://', 'https://', 1)
            code = 301
            return redirect(url, code=code)

def requires_auth(att_f):
    """Requires authentication annotation"""
    @wraps(att_f)
    def decorated(*args, **kwargs):
        """This decorated"""
        if session['profile']['user_id'] in [0, -1] and request.url is not None:
            return redirect('/login?redirectURL='+request.url)

        if trial_expired():
            return redirect('/account/trialend')

        if session['profile'].get('create_timestamp', None) is None:
            # Get the latest user info from PG
            PG.get_user(session['profile']['email'])

        return att_f(*args, **kwargs)
    return decorated

def trial_expired():
    """Send expired trials to the sales page"""
    # Free must have is_trial = 0
    if session['profile'].get('is_trial', None) and session['profile']\
            ['is_trial'] == 0:
        return True

    # Check datetime when is_trial != 0
    if session['profile'].get('create_dt', None):
        now = datetime.utcnow()

        user_trial_end = session['profile'].get('trial_end', None)
        if user_trial_end is None:
            user_trial_end = session['profile']['create_dt'] + \
                timedelta(days=int(os.environ.get('TRIAL_END_DAY')))

        if ("account" not in request.path) and ("charge" not in request.path):
            if (session['profile']['access_level'] == "free"):
                return False
            elif session['profile'].get('is_trial', None) == 2 or \
                session['profile'].get('status', None) is None:
                return True
            elif (session['profile']['access_level'] == "basic") \
                                                and (now >= user_trial_end):
                if session['profile']['is_trial'] != 2:
                    session['profile']['is_trial'] = 2
                    PG.update_is_trial(session['profile']['email'], 2)
                return True
            elif session['profile'].get('status', None) is not None:
                if session['profile']['status'] in ['past_due', 'canceled', 'unpaid']:
                    return True
            else:
                return False

@app.errorhandler(404)
def error404(att_e):
    """Handle error 404"""
    handle_anon()

    if session['profile']['user_id'] == -1:
        return redirect('/')

    PG.log_error(session['profile']['user_id'], '404', att_e,
                 request.url, session['profile'])
    header = build_header(title=att_e, active="error", request=request)
    return render_template('/base/404.html',
                           auth0=AUTH0,
                           profile=session['profile'],
                           header=header,
                           event_id=g.sentry_event_id,
                           public_dsn=SENTRY.client.get_public_dsn('https'))

@app.errorhandler(500)
def error500(att_e):
    """Handle error 500"""
    handle_anon()
    PG.log_error(session['profile']['user_id'],
                 '500',
                 att_e,
                 request.url,
                 session['profile'])
    header = build_header(title=att_e, active="error", request=request)
    return render_template('/base/500.html',
                           auth0=AUTH0,
                           profile=session['profile'],
                           header=header,
                           event_id=g.sentry_event_id,
                           public_dsn=SENTRY.client.get_public_dsn('https'))

def handle_anon():
    """Handle anon"""
    if 'profile' not in session:
        session['profile'] = {'user_id': -1}

def handle_user_context():
    """Handle user context"""
    SENTRY_CLIENT.user_context({
        'user_id': session['profile']['user_id'] if session.get('profile', \
            None) and session['profile'].get('user_id', None) else '',
        'email': session['profile']['email'] if session.get('profile', None) \
            and session['profile'].get('email', None) else ''
    })

def handle_heroku_release_on_redis():
    """Handle heroku release"""
    if session.get('heroku_release'):
        # Cached in Reddis and is checked maximum of once every 6 hours
        if SENTRY_CLIENT.release != session['heroku_release']['version'] or \
                time.time() > session['heroku_release']['expires']:
            update_release_and_store()
    else:
        update_release_and_store()

def update_release_and_store():
    """Update sentry to release and store in redis"""
    heroku_release_version = get_current_heroku_release()
    session['heroku_release'] = {
        'expires' : time.time() + 6 * 3600,
        'version' : heroku_release_version
    }
    SENTRY_CLIENT.release = heroku_release_version

@app.route('/')
@app.route('/index')
def realestate_page():
    """Real estate page"""
    if session['profile']['user_id'] not in [0, -1]:
        return redirect('/property')

    utm_source = request.args.get('utm_source')
    utm_medium = request.args.get('utm_medium')
    utm_campaign = request.args.get('utm_campaign')

    if utm_source or utm_medium or utm_campaign:
        session['utm_source'] = utm_source
        session['utm_medium'] = utm_medium
        session['utm_campaign'] = utm_campaign
        session['profile']['utm_source'] = utm_source
        session['profile']['utm_medium'] = utm_medium
        session['profile']['utm_campaign'] = utm_campaign

    header = build_header(title="Rental Property Calculator - "\
        "Will it cash flow?", active="index", request=request)
    return render_template('/base/index.html',
                           auth0=AUTH0,
                           profile=session['profile'],
                           header=header)

@app.route('/coaching/')
@app.route('/coaching')
def coaching_home():
    """Coaching home page"""
    coaches = PG.get_active_coaches()
    header = build_header(title="Listen Money Matters Coaching",
                          active=str(request.url_rule).split('/')[1],
                          request=request)
    return render_template('/coaching/coaching-index.html',
                           coaches=coaches,
                           auth0=AUTH0,
                           header=header,
                           profile=session['profile'])

@app.route('/coach/<coach_name>/')
@app.route('/coach/<coach_name>')
@requires_auth
def coaching_profile(coach_name="andrew"):
    """Coaching profile page"""
    coach_details = PG.get_coach(coach_name)
    coach_packages = PG.get_coach_packages(coach_name)
    cur_month = datetime.now().strftime("%B")

    header = build_header(title=coach_details["name"],
                          active=str(request.url_rule).split('/')[1],
                          request=request)
    return render_template('/coaching/coach-profile.html',
                           auth0=AUTH0,
                           header=header,
                           coach=coach_details,
                           coach_packages=coach_packages,
                           cur_month=cur_month,
                           profile=session['profile'])

@app.route('/coach/<coach_name>/schedule/', methods=['POST', 'GET'])
@app.route('/coach/<coach_name>/schedule', methods=['POST', 'GET'])
@requires_auth
def coaching_schedule(coach_name="andrew"):
    """Coaching schedule page"""
    coach_details = PG.get_coach(coach_name)
    header = build_header(title="Schedule Coaching Session",
                          active=str(request.url_rule).split('/')[1],
                          request=request)
    return render_template('/coaching/coach-schedule.html',
                           auth0=AUTH0,
                           header=header,
                           coach=coach_details,
                           profile=session['profile'])

@app.route('/home/')
@app.route('/home')
@requires_auth
def home_page():
    """Get history"""
    property_history = PG.get_history(session['profile']['user_id'],
                                      'property view')

    header = build_header(title="Home - Will this rental property cash flow?",
                          active=str(request.url_rule).split('/')[1],
                          request=request)
    return render_template('/base/home.html', header=header,
                           profile=session['profile'],
                           property_history=property_history)


@app.route('/signup/')
@app.route('/signup')
def signup_page():
    """Get sign up page"""
    redirect_url = request.args.get('redirectURL')

    if session['profile']['user_id'] not in [0, -1]:
        return redirect('/property')

    if 'last_address' in session:
        del session['last_address']

    if redirect_url:
        session['redirect_url'] = redirect_url

    header = build_header(title="Sign Up for Free - Listen Money Matters Pro",
                          active=str(request.url_rule).split('/')[1],
                          request=request)
    return render_template('/base/signup.html',
                           auth0=AUTH0,
                           profile=session['profile'],
                           header=header)

@app.route('/login/')
@app.route('/login')
def login_page():
    """Login page"""
    redirect_url = request.args.get('redirectURL')

    if session['profile']['user_id'] not in [0, -1]:
        return redirect('/property')

    if 'last_address' in session:
        del session['last_address']

    if redirect_url:
        session['redirect_url'] = redirect_url

    header = build_header(title="Log In - Listen Money Matters Pro",
                          active=str(request.url_rule).split('/')[1],
                          request=request)
    return render_template('/base/login.html',
                           auth0=AUTH0,
                           profile=session['profile'],
                           header=header)

@app.route('/logout/')
@app.route('/logout')
def logout_page():
    """Logout page"""
    if 'profile' in session:
        del session['profile']
        if session.get('utm_source') or session.get('utm_medium', None) \
                or session.get('utm_campaign', None):
            del session['utm_source']
            del session['utm_medium']
            del session['utm_campaign']
        handle_anon()
    return redirect('https://lmmpro.auth0.com/v2/logout?returnTo={}'.\
        format(get_url(request.url, 'root')))

@app.route('/search/')
@app.route('/search')
@requires_auth
def search_page():
    """Search page"""
    property_history = PG.get_history(session['profile']['user_id'],
                                      'property view')
    property_groups = PG.get_groups(session['profile']['user_id'])
    search_query = session['search_query'].replace("%20", " ") \
        if 'search_query' in session.keys() else ''
    search_results = session['search_results'] if 'search_results' \
        in session.keys() and session['search_results'] else []

    header = build_header(title="Search Results - {}".format(search_query),
                          active=str(request.url_rule).split('/')[1],
                          request=request)
    return render_template('/property/search.html',
                           header=header,
                           profile=session['profile'],
                           search_query=search_query,
                           search_results=search_results,
                           property_group="",
                           property_history=property_history,
                           property_groups=property_groups)


@app.route('/search/submit', methods=['POST'])
@requires_auth
def search_submit_page():
    """Search page"""
    return redirect('/search')


@app.route('/help/')
@app.route('/help')
@requires_auth
def property_help_page():
    """Property help page"""
    # Get sidebar info
    property_history = PG.get_history(session['profile']['user_id'],
                                      'property view')
    property_groups = PG.get_groups(session['profile']['user_id'])

    header = build_header(title="Help - Listen Money Matters Pro",
                          active=str(request.url_rule).split('/')[1])
    return render_template('/property/help.html',
                           header=header,
                           profile=session['profile'],
                           property_group="",
                           property_history=property_history,
                           property_groups=property_groups)

@app.route('/member-exclusives/')
@app.route('/member-exclusives')
@requires_auth
def member_exclusives():
    """Member exclusives page"""
    # Get menu info
    property_history = PG.get_history(session['profile']['user_id'],
                                      'property view')
    property_groups = PG.get_groups(session['profile']['user_id'])
    saved_property_count = PG.get_saved_property_count(
        session['profile']['user_id'])

    if session['profile']['access_level'] == "basic":
        return redirect('/account')

    header = build_header(title="Member Exclusives - Listen Money Matters Pro",
                          active=str(request.url_rule).split('/')[1])
    return render_template('/base/member-exclusives.html',
                           header=header,
                           profile=session['profile'],
                           property_group="",
                           property_history=property_history,
                           property_groups=property_groups,
                           saved_property_count=saved_property_count)

@app.route('/product-updates/')
@app.route('/product-updates')
@requires_auth
def change_log():
    """Update product page"""
    # Get menu info
    property_history = PG.get_history(session['profile']['user_id'],
                                      'property view')
    property_groups = PG.get_groups(session['profile']['user_id'])
    changelog = PG.get_change_log()
    header = build_header(title="Product Updates - Listen Money Matters Pro",
                          active=str(request.url_rule).split('/')[1])
    return render_template('/base/product-updates.html',
                           header=header,
                           profile=session['profile'],
                           property_group="",
                           property_history=property_history,
                           property_groups=property_groups,
                           change_log=changelog)

@app.route('/welcome/')
@app.route('/welcome')
@requires_auth
def property_welcome_page():
    """Welcome page after registered"""
    # Popular properties for easy examples
    popular_properties = PG.get_popular_properties()
    header = build_header(title="Welcome - Let's get started!",
                          active=str(request.url_rule).split('/')[1])
    return render_template('/base/welcome.html',
                           header=header,
                           popular_properties=popular_properties,
                           profile=session['profile'])


@app.route('/property/')
@app.route('/property')
@requires_auth
def property_main_page():
    """Property main page"""
    # Get sidebar info
    property_history = PG.get_history(session['profile']['user_id'],
                                      'property view')
    property_groups = PG.get_groups(session['profile']['user_id'])
    saved_property_count = PG.get_saved_property_count(\
        session['profile']['user_id'])

    header = build_header(title="Property - LMM Pro",
                          active=str(request.url_rule).split('/')[1])
    return render_template('/property/property-home.html',
                           header=header,
                           profile=session['profile'],
                           property_group="",
                           property_history=property_history,
                           property_groups=property_groups,
                           saved_property_count=saved_property_count)


@app.route('/property/group/<group_name>/')
@app.route('/property/group/<group_name>')
@requires_auth
def property_group_page(group_name=None):
    """Property group page"""
    group_name_pretty = group_name.replace("_", " ")
    # Get sidebar info
    property_history = PG.get_history(session['profile']['user_id'],
                                      'property view')
    property_groups = PG.get_groups(session['profile']['user_id'])
    current_group = PG.get_property_group(session['profile']['user_id'],
                                          group_name_pretty)

    if current_group is None:
        return redirect('/property')

    # Get all the properties in the group - helps for property group page.
    current_group = PG.get_properties_in_group(session['profile']['user_id'],
                                               current_group['portfolio_id'])

    all_properties = {}
    group_summaries = {}
    group_summaries['total_cost'] = 0
    group_summaries['monthly_income'] = 0
    group_summaries['monthly_expenses'] = 0
    group_summaries['principle_gain'] = 0
    group_summaries['value_sum'] = 0
    group_summaries['avg_cash_on_cash'] = 0
    group_summaries['monthly_reserve'] = 0
    for att_property in current_group:
        property_plus = PG.get_property(user_id=session['profile']['user_id'],
                                        property_id=att_property['property_id'])
        property_plus = run_calculations(property_plus)
        all_properties[property_plus['address']] = property_plus

        group_summaries['total_cost'] += property_plus['mortgage']\
            ['down_payment_dollar'] + property_plus['cost']\
                ['closing_costs_dollar']
        group_summaries['monthly_reserve'] += property_plus['cost']\
            ['property_management_dollar'] + property_plus['cost']\
                ['vacancy_rate_dollar']
        group_summaries['monthly_income'] += property_plus['hard']['rent']
        group_summaries['monthly_expenses'] += property_plus['calc']\
            ['monthly_expenses']
        group_summaries['principle_gain'] += property_plus['calc']\
            ['monthly_principle']
        group_summaries['value_sum'] += property_plus['hard']['valuation']

    if group_summaries['total_cost'] != 0:
        group_summaries['avg_cash_on_cash'] = ((group_summaries\
            ['monthly_income'] - group_summaries['monthly_expenses']) * 12) \
            / float(group_summaries['total_cost']) * 100

    group_summaries['monthly_growth'] = group_summaries['monthly_income'] - \
        group_summaries['monthly_expenses'] - group_summaries['monthly_reserve']
    group_summaries['monthly_cashflow'] = group_summaries['monthly_income'] \
        - group_summaries['monthly_expenses']

    header = build_header(title=group_name_pretty.title(),
                          active=str(request.url_rule).split('/')[2])
    return render_template('/property/property-group.html',
                           header=header,
                           profile=session['profile'],
                           property_group=group_name,
                           all_properties=format_everything(all_properties),
                           group_summaries=format_everything(group_summaries),
                           property_history=property_history,
                           property_groups=property_groups)

@app.route('/property/compare/')
@app.route('/property/compare')
@app.route('/property/compare/<id1>/')
@app.route('/property/compare/<id1>')
@app.route('/property/compare/<id1>/<int:id2>/')
@app.route('/property/compare/<id1>/<int:id2>')
@app.route('/property/compare/<id1>/<int:id2>/')
@app.route('/property/compare/<id1>/<int:id2>')
@app.route('/property/compare/<id1>/<int:id2>/<int:id3>/')
@app.route('/property/compare/<id1>/<int:id2>/<int:id3>')
@requires_auth
def property_comparison_page(id1='', id2='', id3=''):
    """Property compare page"""
    results = {
        'p1': None,
        'p2': None,
        'p3': None
    }

    user_id = session['profile']['user_id'] if 'profile' in session \
        and 'user_id' in session['profile'] and session['profile']['user_id'] \
        not in [0, -1] else None
    properties_saved = PG.get_properties_by_user_id(user_id)
    for index, att_id in enumerate([id1, id2, id3]):
        if att_id:
            # id1 can be int or address string
            if represents_int(att_id): # for id2, id3 and id1 which was int type
                property_info = PG.get_property(property_id=att_id,
                                                user_id=user_id)
                if property_info:
                    address = property_info['address'].replace(' ', '_')
                    property_info = get_property_info(session,
                                                      address,
                                                      property_info['zpid'],
                                                      False)
                    property_info = init_costs(property_info)
                    property_info = run_calculations(property_info)

                results['p%s' % (index + 1)] = property_info
            else:    # for id1 which was address string
                results['p%s' % (index + 1)] = session.get(att_id)
            if results['p%s' % (index + 1)] is not None:
                results['p%s' % (index + 1)] = get_property_base_on_session(\
                    results['p%s' % (index + 1)])
                # Update coordinate by Google Map API if missing
                results['p%s' % (index + 1)] = update_coordinate(\
                    results['p%s' % (index + 1)])

    header = build_header(title="Property Compare",
                          active=str(request.url_rule).split('/')[2])
    return render_template('/property/property-compare.html',
                           header=header,
                           profile=session['profile'],
                           p1=format_everything(results['p1']) \
                                if results['p1'] else None,
                           p2=format_everything(results['p2']) \
                                if results['p2'] else None,
                           p3=format_everything(results['p3']) \
                                if results['p3'] else None,
                           properties_saved=properties_saved)

@app.route('/account/<action>/')
@app.route('/account/<action>')
@app.route('/account/')
@app.route('/account')
@requires_auth
def plans_billing_page(action=None):
    """Account page"""

    # Get the latest user info from PG
    user = PG.get_user(session['profile']['email'])
    user['request_url'] = request.url

    # Get Stripe Details
    user = get_stripe_data(user)
    if user.get('access_level', None) is None:
        user['access_level'] = 'basic'

    # Update session with PG + Stripe info
    session['profile'].update(user)

    # Default Page Settings
    template_location = '/base/account.html'
    title = "Your Account - Listen Money Matters"
    message = None
    message_type = "danger"

    # Page Actions
    if action == "update":
        message = "<center>Your credit card has been updated.</center>"
        message_type = "success"

    elif action == "trialend":
        message = "<center>Your free trial has ended. Subscribe to continue."\
            "</center>"
        message_type = "danger"

    elif action == "cancel":
        message = "<center>Your account has been downgraded to Basic.</center>"
        message_type = "success"

    elif action == "cardfail":
        message = "<center>Your credit card was declined.</center>"

    elif action == "cancelfail":
        message = '<center>There was an issue canceling your subscription, '\
            'please <a href="mailto:team@listenmoneymatters.com">email us</a> '\
            'for assistance.</center>'

    elif action == "congratulations":
        title = "Boom! You're in!"
        template_location = '/base/congratulations.html'

    header = build_header(title=title,
                          active=str(request.url_rule).split('/')[1],
                          request=request,
                          message=message,
                          message_type=message_type)
    return render_template(template_location,
                           header=header,
                           profile=session['profile'],
                           user=session['profile'])

@app.route('/charge', methods=['POST'])
@app.route('/change', methods=['POST'])
@requires_auth
# pylint: disable=R0911
def charge_card_page():
    """Update stripe"""

    # Get existing Customer ID
    user = PG.get_user(session['profile']['email'])

    # is_trial
    get_trial_end = user['create_dt'] + timedelta(\
        days=int(os.environ.get('TRIAL_END_DAY')))
    is_trial = 2 if datetime.now() >= get_trial_end else 1

    if user['stripe_id']:
        if request.form.get('update_card', None) is not None:
            # Update CC Details
            user['stripeToken'] = request.form['stripeToken']
            user['request_url'] = request.url
            if update_card(user) is True:
                return redirect('/account/update')
            return redirect('/account/cardfail')
        elif request.form.get('cancel_membership', None) is not None:
            user['is_trial'] = is_trial
            user['request_url'] = request.url
            if cancel_membership(user) is True:
                return redirect('/account/cancel')
            return redirect('/account/cancelfail')

        else:
            # Upgrade/Downgrade payment tier
            user['stripeToken'] = request.form['stripeToken']
            user['plan'] = request.form['tier']
            user['request_url'] = request.url
            if update_subscription(user) is True:
                return redirect('/account/congratulations')
            return redirect('/account/cardfail')

    return redirect('/account')


@app.route('/overview')
@app.route('/mortgage')
@app.route('/manage')
@requires_auth
def no_property_page():
    """Property page"""
    last_address = session.get('last_address', None)

    if last_address is None:
        return redirect('/property')

    address = last_address[0]
    zpid = last_address[1]
    return redirect('/property/{}/{}/overview'.format(address, zpid))

@app.route('/share/<shareid>')
def share_page(shareid):
    """Share page"""
    hashids = Hashids()
    property_id = hashids.decode(shareid)

    if session.get(property_id) is None and len(property_id) == 1:
        property_id = property_id[0]
        property_info = PG.get_property(property_id=property_id)
        if property_info:
            address = property_info['address'].replace(' ', '_')
            session[property_id] = get_property_info(session,
                                                     address,
                                                     property_info['zpid'],
                                                     False)
            session[property_id] = init_costs(session[property_id])
            session[property_id] = run_calculations(session[property_id])

            header = build_header(title="Overview - {}".format(\
                session[property_id]['pretty_address']),
                                  active="overview",
                                  request=request)
            return render_template('/property/overview.html',
                                   header=header,
                                   profile={'user_id': 0},
                                   portfolios=None,
                                   auth0=AUTH0,
                                   p=format_everything(session[property_id]))
    return redirect('/')

# Fllow get property data
# 1.Found in PG for the user
# 2.Found in a Redis session for the user
# 3.HouseCanary returned value
# 4.Zillow returned value
@app.route('/property/<address>/<zpid>/overview/')
@app.route('/property/<address>/<zpid>/overview')
def property_page(address, zpid):
    """Property overview"""
    # No free rides!
    if trial_expired():
        return redirect('/account/trialend')

    message = None
    message_type = None
    group = None

    # Go to the last property if we don't specify
    session['last_address'] = [address, zpid]

    # Get portfolios and store in session
    session['portfolios'] = PG.get_groups(session['profile']['user_id'])

    # For tracking, let's see how many properties this user has saved
    saved_property_count = PG.get_saved_property_count(\
        session['profile']['user_id'])

    # 2.Found in a Redis session for the user
    if session.get(address, None) and session[address]:
        if session[address].get("portfolio_id"):
            if session[address]["portfolio_id"] is None:
                session[address] = get_property_info(session, address, zpid)
                session[address] = init_costs(session[address])
                session[address] = run_calculations(session[address])

            group = PG.get_group_by_property_id(session['profile']['user_id'],
                                                session[address]["property_id"])

        session[address] = run_calculations(session[address])

    # 3.HouseCanary returned value AND 4.Zillow returned value
    else:
        session[address] = get_property_info(session, address, zpid)
        session[address] = init_costs(session[address])
        session[address] = run_calculations(session[address])

        # The first time property is loaded,
        # if some data is missing we show the alert
        if session[address]['hard']['valuation'] == 1:
            message = "Note: Some valuation data is missing from Zillow for "\
                "this property, you'll need to estimate this on your own."
            message_type = "warning"
        elif session[address]['hard']['rent'] == 1:
            message = "Note: The rent estimate is missing from Zillow for "\
                "this property, you'll need to estimate this on your own."
            message_type = "warning"

        sales_history = []
        if len(session[address]['sales_history']) > 0:
            for history in session[address]['sales_history']:

                grantee_1 = history['grantee_1_forenames'] if history['grantee_1_forenames']\
                    != 'None' else ''
                grantee_1 += ' ' + history['grantee_1'] if history['grantee_1']\
                    != 'None' else ''

                grantee_2 = history['grantee_2_forenames'] if history['grantee_2_forenames']\
                    != 'None' else ''
                grantee_2 += ' ' + history['grantee_2'] if history['grantee_2']\
                    != 'None' else ''

                grantor_1 = history['grantor_1_forenames'] if history['grantor_1_forenames']\
                    != 'None' else ''
                grantor_1 += ' ' + history['grantor_1'] if history['grantor_1'] != 'None' else ''

                grantor_2 = history['grantor_2_forenames'] if history['grantor_2_forenames']\
                    != 'None' else ''
                grantor_2 += ' ' + history['grantor_2'] if history['grantor_2'] != 'None' else ''

                grantee = grantee_1 if grantee_1 != '' else ''
                grantee += ' & '+ grantee_2 if grantee_2 != '' else ''
                grantor = grantor_1 if grantor_1 != '' else ''
                grantor += ' & '+ grantor_2 if grantor_2 != '' else ''

                obj_history = {
                    'record_date': history['record_date'],
                    'grantee': grantee.strip(),
                    'grantor': grantor.strip(),
                    'event_type': history['event_type'].replace('_', ' '),
                    'amount': format_currency(history['amount'])
                }

                sales_history.append(obj_history)
        session[address]['saleshistory'] = sales_history

        school = session[address]['housecanary'].get('school', None)
        if school is not None:
            elementary_location = school['elementary_name']+' '+school['elementary_state']
            elementary_location = elementary_location.replace(' ', '+')
            elementary_location = get_coordinate_from_address(elementary_location)
            school['elementary_coordinate'] = elementary_location
            school['elementary_distance_miles'] = round(float(school['elementary_distance_miles']), 2)

            school['elementary_score'] = int(round(float(school['elementary_score'])))
            school['middle_score'] = int(round(float(school['middle_score'])))
            school['high_score'] = int(round(float(school['high_score'])))
            #Color Calculate
            school['elementary_bg'] = cal_color(school['elementary_score'])
            school['middle_bg'] = cal_color(school['middle_score'])
            school['high_bg'] = cal_color(school['high_score'])

            middle_location = school['middle_name']+' '+school['middle_state']
            middle_location = middle_location.replace(' ', '+')
            middle_location = get_coordinate_from_address(middle_location)
            school['middle_coordinate'] = middle_location
            school['middle_distance_miles'] = round(float(school['middle_distance_miles']), 2)

            high_location = school['high_name']+' '+school['high_state']
            high_location = high_location.replace(' ', '+')
            high_location = get_coordinate_from_address(high_location)
            school['high_coordinate'] = high_location
            school['high_distance_miles'] = round(float(school['high_distance_miles']), 2)
        else:
            school = ''

        session[address]['school'] = school

    if group:
        session[address]["portfolio_name"] = group["portfolio_name"]

    if session[address].get('portfolio_id') is not None:
        hashids = Hashids()
        session[address]['hashid'] = hashids.encode(\
            session[address]['property_id'])


    # Update coordinate by Google Map API if missing
    session[address] = update_coordinate(session[address])

    header = build_header(title="Overview - {}".format(\
        session[address]['pretty_address']),
                          active=str(request.url).split('/')[6],
                          message=message,
                          message_type=message_type,
                          request=request)
    return render_template('/property/overview.html',
                           header=header,
                           profile=session.get('profile', None),
                           portfolios=session.get('portfolios', None),
                           auth0=AUTH0,
                           p=format_everything(session[address]),
                           school=session[address]['school'],
                           saved_property_count=saved_property_count)


@app.route('/property/<address>/<zpid>/mortgage/')
@app.route('/property/<address>/<zpid>/mortgage')
@requires_auth
def mortgage_page(address, zpid):
    """Property mortgage"""
    if address in session.keys():
        header = build_header(title="Mortgage - {}".format(\
            session[address]['pretty_address']),
                              active=str(request.url).split('/')[6],
                              request=request)
        return render_template('/property/mortgage.html',
                               header=header,
                               profile=session['profile'],
                               p=format_everything(session[address]))

    return redirect('/property/{}/{}/overview'.format(address, zpid))


@app.route('/property/<address>/<zpid>/projections/')
@app.route('/property/<address>/<zpid>/projections')
@requires_auth
def projection_page(address, zpid):
    """Property projections"""
    if address in session.keys():
        projection_infos = get_projections(address)
        projections = projection_infos[0]
        projections_table = projection_infos[1]
        yearly_equity_table = projection_infos[2]
        yearly_equity = projection_infos[3]
        header = build_header(title="Projections - {}".format(session[address]\
            ['pretty_address']),
                              active=str(request.url).split('/')[6], \
                                    request=request)
        return render_template('/property/projections.html',
                               header=header,
                               profile=session['profile'],
                               p=format_everything(session[address]),
                               projections=json.dumps(projections),
                               projections_table=projections_table,
                               yearly_equity_table=yearly_equity_table,
                               yearly_equity=json.dumps(yearly_equity),)

    return redirect('/property/{}/{}/overview'.format(address, zpid))

@app.route('/property/<address>/<zpid>/manage/')
@app.route('/property/<address>/<zpid>/manage')
@requires_auth
def manage_page(address, zpid):
    """Property manage"""
    header = build_header(title="Manage - {}".format(\
        session[address]['pretty_address']),
                          request=request)
    return render_template('/property/manage.html',
                           header=header,
                           profile=session['profile'],
                           p=format_everything(session[address]),
                           get_zpid=zpid)

@app.route('/_zillow_search_ajax', methods=['POST'])
def zillow_search():
    """Ajax Zillow API searching"""
    ajax_results = request.get_json(force=True)
    street_number = ajax_results['street_number']
    route = ajax_results['route'].replace(' ', '%20')
    postal_code = ajax_results['postal_code']
    hc_address = street_number + ' ' + ajax_results['route']

    if street_number and route and postal_code:
        action_text = "|".join([street_number, route, postal_code])
        address_format = '{},_{}_{}'.format(street_number +'-'+ \
            ajax_results['route'], ajax_results['locality'] +'-'+ \
            ajax_results['administrative_area_level_1'] +'-'+ \
            ajax_results['country'], postal_code)
        url_address = address_format.replace('# ', '').replace(', ', '-').\
            replace(' ', '-').replace(',', '')
        session['hc_' + url_address] = {'hc_address' : hc_address}
        zpid = ajax_search_zpid(hc_address, postal_code)
        if isinstance(zpid, list):
            session['search_results'] = []
            session['search_query'] = "{} {} {}".format(\
                street_number, route.replace('%20', ' '), postal_code)

            zillow_results = zpid
            for at_property in zillow_results:
                zpid = at_property['zpid']
                zestimate = at_property['zestimate']['amount'].get('#text', 0)
                at_property = at_property['address']
                city_state = at_property['city'] + ', ' + at_property['state']
                address_format = '{}, {} {}'.format(at_property['street'], \
                    city_state, at_property['zipcode'])
                url_address = address_format\
                    .replace(' ' + city_state + ' ', '_' + city_state + '_')\
                    .replace('# ', '').replace(', ', '-').replace(' ', '-')\
                    .replace(',', '')
                url = '<a href="/property/{}/{}/overview">{}</a>'\
                    .format(url_address, zpid, address_format)

                if zestimate != 0:
                    session['search_results'].append([url, zestimate])
            length_search = len(session['search_results'])
            if length_search:
                PG.log_action(session['profile']['user_id'],
                              'search',
                              action_text)
                AUTH0['AUTH0_REDIRECT_URL'] = '/search'
                return json.dumps({'status': 'OK',
                                   'search': len(zillow_results)})
        else:
            url = '/property/{}/{}/overview'.format(url_address, zpid)
            PG.log_action(session['profile']['user_id'], 'search', action_text)
            AUTH0['AUTH0_REDIRECT_URL'] = url
            return json.dumps({'status': 'OK', 'match': url})

    return json.dumps({'status': 'Failed', 'message': 'Invalid Address'})


@app.route('/_property_value_change_ajax', methods=['POST'])
@requires_auth
def property_value_change():
    """Change property by ajax"""
    ajax_results = request.get_json(force=True)
    get_p = session.get(ajax_results['property'], None)

    if ajax_results['object_id'] == 'refresh' and get_p is not None:
        address = session[ajax_results['property']]['address']
        zpid = session[ajax_results['property']]['zillow']['zpid']
        PG.delete_property(session[ajax_results['property']],
                           session['profile']['user_id'])
        del session[ajax_results['property']]
        #convert zpid to string
        zpid = str(zpid)
        session[address] = get_property_info(session, address, zpid)
        session[address] = init_costs(session[address])
        session[address] = run_calculations(session[address])
        session[address]['refresh'] = ""
        return json.dumps({'status': 'OK', 'reset': 'true',
                           'data': format_everything(session[address])})

    if get_p is not None:
        get_p = build_property_model(get_p, ajax_results)

        # Update in DB if it's saved
        pg_property = PG.get_property(get_p['address'],
                                      session['profile']['user_id'])
        if pg_property:
            PG.update_property(get_p, session['profile']['user_id'])

        session[ajax_results['property']] = get_p
        session[ajax_results['property']]['refresh'] = """
        <i id="refresh" rel="tooltip" class="fa fa-refresh kv-icon kv-icon-secondary ui-tooltip"
        data-toggle="tooltip" data-placement="top"
        data-original-title="Reset this property"></i>"""
        return json.dumps({'status': 'OK', 'data': format_everything(get_p)})

    return json.dumps({'status': 'No property history found.'})

@app.route('/_update_group_name_ajax', methods=['POST'])
@requires_auth
def update_group_name():
    """Update group name by ajax"""
    ajax_results = request.get_json(force=True)

    if 'new_name' in ajax_results:
        PG.update_group_name(ajax_results['new_name'],
                             ajax_results['old_name'],
                             session['profile']['user_id'])
        return json.dumps({'status': 'OK', 'new_name': ajax_results['new_name'],
                           'message': 'Group name updated.'})

    return json.dumps({'status': 'FAILED', 'message': 'No new name was sent.'})


@app.route('/_delete_group_name_ajax', methods=['POST'])
@requires_auth
def delete_group_name():
    """Delete group name by ajax"""
    ajax_results = request.get_json(force=True)

    if 'old_name' in ajax_results:
        if 'profile' in session.keys():
            return json.dumps({'status': 'FAILED', \
                'message': 'Profile is empty'})

        PG.delete_group(session['profile']['user_id'],
                        ajax_results['old_name'])
        return json.dumps({'status': 'OK', 'old_name': ajax_results['old_name'],
                           'message': 'Group name deleted.'})

    return json.dumps({'status': 'FAILED', 'message': 'No group was deleted.'})

@app.route('/_save_to_group_ajax', methods=['POST'])
@requires_auth
def save_to_group():
    """Create a group and save data in this group"""
    ajax_results = request.get_json(force=True)
    address = ajax_results['property']
    pg_property = PG.get_property(address, session['profile']['user_id'])

    if 'portfolio_id' in ajax_results:
        if not pg_property:
            property_id = PG.save_property(session[address],
                                           session['profile']['user_id'],
                                           ajax_results['portfolio_id'])
        else:
            PG.add_property_to_portfolio(session[address],
                                         session['profile']['user_id'],
                                         ajax_results['portfolio_id'])
            property_id = pg_property['property_id']

        session[address]['portfolio_id'] = ajax_results['portfolio_id']
        session[address]['property_id'] = property_id
        return json.dumps({'status': 'OK', 'property_id': property_id,
                           'message': 'Property added to existing group.'})
    elif 'portfolio_name' in ajax_results:
        if not pg_property:
            # Create Portfolio, then get ID, then get property_id
            portfolio = PG.get_property_group(session['profile']['user_id'],
                                              ajax_results['portfolio_name'])
            if not portfolio:
                portfolio = PG.create_property_group(session['profile']\
                    ['user_id'], ajax_results['portfolio_name'])
            property_id = PG.save_property(session[address],
                                           session['profile']['user_id'],
                                           portfolio['portfolio_id'])
        else:
            # Create Portfolio, then get ID, then get property_id
            portfolio = PG.get_property_group(session['profile']['user_id'],
                                              ajax_results['portfolio_name'])
            if not portfolio:
                portfolio = PG.create_property_group(session['profile']\
                    ['user_id'], ajax_results['portfolio_name'])
            PG.add_property_to_portfolio(session[address],
                                         session['profile']['user_id'],
                                         portfolio['portfolio_id'])
            property_id = pg_property['property_id']

        session['portfolios'] = PG.get_groups(session['profile']['user_id'])
        session[address]['portfolio_id'] = portfolio['portfolio_id']
        session[address]['property_id'] = property_id
        return json.dumps({'status': 'OK', 'property_id': property_id,
                           'message': 'Property added to a new group.'})
    else:
        return json.dumps({'status': 'FAILED',
                           'message': 'No Portfolio ID or Name was sent.'})

@app.route('/_get_group_list_ajax', methods=['GET'])
def get_group_list():
    """Get Group"""
    session['portfolios'] = PG.get_groups(session['profile']['user_id'])
    return json.dumps(session['portfolios'])

@app.route('/callback')
def callback_handling():
    """Handle callback check token"""
    AUTH0['AUTH0_CALLBACK_URL'] = get_url(request.url, 'root') + '/callback'
    code = request.args.get('code')

    json_header = {'content-type': 'application/json'}

    token_url = "https://{domain}/oauth/token".format(\
        domain=AUTH0["AUTH0_DOMAIN"])
    token_payload = {
        'client_id' : AUTH0['AUTH0_CLIENT_ID'], \
        'client_secret' : AUTH0['AUTH0_CLIENT_SECRET'], \
        'redirect_uri' : AUTH0['AUTH0_CALLBACK_URL'], \
        'code' : code, \
        'grant_type': 'authorization_code' \
    }

    token_info = requests.post(token_url, data=json.dumps(token_payload),
                               headers=json_header).json()

    if 'access_token' not in token_info:
        return redirect('/login')

    user_url = "https://{domain}/userinfo?access_token={access_token}"  \
        .format(domain=AUTH0["AUTH0_DOMAIN"], \
            access_token=token_info['access_token'])

    user_info = requests.get(user_url).json()

    session['profile'] = user_info
    session['profile']['auth0_user_id'] = user_info['user_id']
    session['profile']['user_hash'] = hmac.new(\
        "ywyPSHnrzsfMRfKQ_x_yHa5naWCyyv0ELDKKXqIL", \
            session['profile']['email'], hashlib.sha256).hexdigest()

    # Check if in DB, if not, store it!
    user = PG.get_user(session['profile']['email'])
    user['request_url'] = request.url

    # Set/Update tracking info
    if session.get('utm_source') or session.get('utm_medium') \
            or session.get('utm_campaign'):
        PG.update_user_track(session['profile']['email'],
                             session['utm_source'],
                             session['utm_medium'],
                             session['utm_campaign'])
        user['utm_source'] = session.get('utm_source')
        user['utm_medium'] = session.get('utm_medium')
        user['utm_campaign'] = session.get('utm_campaign')

    # Get Stripe Details
    user = get_stripe_data(user)
    if user.get('access_level', None) is None:
        user['access_level'] = 'basic'

    # Update session with PG + Stripe info
    session['profile'].update(user)

    if session['profile'].get('welcome', None) is not None:
        redirect_url = '/welcome'
    elif 'redirect_url' in session:
        redirect_url = session['redirect_url']
        session['redirect_url'] = None
    elif 'last_address' not in session:
        redirect_url = '/property'
    else:
        redirect_url = '/property/{}/{}/overview'.format(\
            session['last_address'][0], session['last_address'][1])

    if redirect_url is None:
        redirect_url = '/property'

    return redirect(redirect_url)

@app.route('/_get_projections_ajax', methods=['POST'])
def get_projections(address=None, number_of_years=30):
    """Get projections by ajax. This function can use both inside and ajax"""
    projections = []
    ren_growth = 0.02
    appreciation_percent = 0.03
    tax_increase = 0.02
    insurance_increase = 0.02
    if request.is_xhr:
        ajax_results = request.get_json(force=True)
        address = ajax_results['address'] if 'address' in ajax_results else None
        number_of_years = int(ajax_results['number_years']) \
            if 'number_years' in ajax_results else 30
        ren_growth = float(ajax_results['rent_growth']) \
            if 'rent_growth' in ajax_results else 0.02
        appreciation_percent = float(ajax_results['apprection_percent']) \
            if 'apprection_percent' in ajax_results else 0.03
        tax_increase = float(ajax_results['tax_increase']) \
            if 'tax_increase' in ajax_results else 0.02
        insurance_increase = float(ajax_results['insurance_increase']) \
            if 'insurance_increase' in ajax_results else 0.02

    if  address and address in session.keys():
        projections_obj = Projections(
            at_property=session[address],
            number_of_years=number_of_years,
            ren_growth=ren_growth,
            appreciation_percent=appreciation_percent,
            tax_increase=tax_increase,
            insurance_increase=insurance_increase)

        projections = projections_obj.calculate_schedule()
        projections_table = projections_obj.table_html()
        yearly_equity_table = projections_obj.yearly_equity_table_html()
        yearly_equity = projections_obj.equity_schedule

    if request.is_xhr:
        return json.dumps({'status': 'OK',
                           'projections': projections,
                           'projections_table': projections_table,
                           'yearly_equity_table': yearly_equity_table,
                           'yearly_equity': yearly_equity})

    return (projections, projections_table, yearly_equity_table, yearly_equity)


def build_property_model(get_p, ajax=None):
    """Property model"""
    # Update fields in core dataset
    if ajax is not None:
        clean_key = ajax['object_id'].replace('txt', '').lower()
        get_p = update_dictionary(get_p, clean_key,
                                  float(clean_result(ajax['object_value'])))

        # Redo percentage calculations
        if "dollar" in clean_key:
            get_p = run_costs(get_p, "dollar")
            get_p = run_calculations(get_p)
        # Redo dollar calculations
        else:
            get_p = run_costs(get_p, "percent")
            get_p = run_calculations(get_p)

    return get_p


def init_costs(att_p):
    """Init costs"""
    att_p['mortgage']['down_payment_dollar'] = att_p['hard']\
        ['purchase_price'] * 0.2
    att_p['mortgage']['down_payment_percent'] = 20.0
    att_p['mortgage']['rate'] = 4.5        # Assumption
    att_p['mortgage']['term'] = 30
    att_p['mortgage']['points'] = 0

    if att_p['tax_amount'] != 0:
        att_p['cost']['property_taxes'] = att_p['tax_amount']
    else:
        # Assumption
        att_p['cost']['property_taxes'] = att_p['hard']['purchase_price'] * 0.01
    att_p['cost']['property_insurance'] = (att_p['hard']\
        ['purchase_price'] / 1000) * 4.6 # Assumption
    att_p['cost']['renovation_budget'] = 0.00
    att_p['cost']['hoa_misc'] = 0.00
    att_p['cost']['closing_costs_dollar'] = att_p['hard']\
        ['purchase_price'] * 0.040 # Assumption
    att_p['cost']['closing_costs_percent'] = 4.0
    att_p['cost']['property_management_dollar'] = att_p['hard']['rent'] * 0.1
    att_p['cost']['property_management_percent'] = 10.0
    att_p['cost']['vacancy_rate_dollar'] = att_p['hard']\
        ['rent'] * 0.05 # Assumption
    att_p['cost']['vacancy_rate_percent'] = 5.0
    att_p['cost']['capex_dollar'] = att_p['hard']['rent'] * 0.1 # Assumption
    att_p['cost']['capex_percent'] = 10.0

    return att_p


def run_costs(att_p, g_type="percent"):
    """Run costs"""
    # Redo dollar calculations
    if g_type == "percent":
        att_p['mortgage']['down_payment_dollar'] = att_p['mortgage']\
            ['down_payment_percent']/100 * att_p['hard']['purchase_price']
        att_p['cost']['closing_costs_dollar'] = att_p['cost']\
            ['closing_costs_percent']/100 * att_p['hard']['purchase_price']
        att_p['cost']['property_management_dollar'] = att_p['cost']\
            ['property_management_percent']/100 * att_p['hard']['rent']
        att_p['cost']['vacancy_rate_dollar'] = att_p['cost']\
            ['vacancy_rate_percent']/100 * att_p['hard']['rent']
        att_p['cost']['capex_dollar'] = att_p['cost']['capex_percent']\
            /100 * att_p['hard']['rent']
    # Redo percentage calculations
    elif g_type == "dollar":
        att_p['mortgage']['down_payment_percent'] = round(att_p['mortgage']\
            ['down_payment_dollar'] / att_p['hard']['purchase_price'] * 100, 2)
        att_p['cost']['closing_costs_percent'] = round(att_p['cost']\
            ['closing_costs_dollar'] / att_p['hard']['purchase_price'] * 100, 2)
        att_p['cost']['property_management_percent'] = round(att_p['cost']\
            ['property_management_dollar'] / att_p['hard']['rent'] * 100, 2)
        att_p['cost']['vacancy_rate_percent'] = round(att_p['cost']\
            ['vacancy_rate_dollar'] / att_p['hard']['rent'] * 100, 2)
        att_p['cost']['capex_percent'] = round(att_p['cost']['capex_dollar'] \
            / att_p['hard']['rent'] * 100, 2)

    return att_p

# pylint: disable=R0915,R0912,R0914
def run_calculations(att_p):
    """Calculations"""
    # No zero down payments, or term
    if att_p['mortgage']['down_payment_dollar'] <= 0:
        att_p['mortgage']['down_payment_dollar'] = 1
    if att_p['mortgage']['down_payment_percent'] <= 0:
        att_p['mortgage']['down_payment_percent'] = 1 \
            / float(att_p['hard']['purchase_price'])
    if att_p['mortgage']['term'] <= 0:
        att_p['mortgage']['term'] = 1

    ##############################
    # Run Core Calculation
    ##############################
    # How much the property management costs for a year
    yearly_pm = att_p['cost']['property_management_dollar'] * 12
    yearly_rent = att_p['hard']['rent'] * 12 # How much we earn in rent a year

    # How much we will borrow from the bank.
    att_p['calc']['mortgage_principle'] = att_p['hard']['purchase_price'] \
        - att_p['mortgage']['down_payment_dollar']
    if att_p['mortgage']['down_payment_percent'] < 100:
        # Get the mortgage payment given all of the details the user input
        att_p['calc']['mortgage_payment'] = calculate_payment(att_p['calc']\
            ['mortgage_principle'], (att_p['mortgage']['term'] * 12), \
            (att_p['mortgage']['rate'] / 100))
    else:
        att_p['calc']['mortgage_payment'] = 0

    # What will a property yield not considering any expenses
    att_p['calc']['gross_yield'] = round((yearly_rent / att_p['hard']\
        ['purchase_price'] * 100), 2)

    # Yearly profit after all expenses.
    att_p['calc']['noi'] = yearly_rent - att_p['cost']['property_insurance'] \
        - yearly_pm - att_p['cost']['property_taxes'] - \
            (att_p['cost']['hoa_misc'] * 12)

    # Annual NOI divided by Purchase Price
    att_p['calc']['purchase_cap_rate'] = round((att_p['calc']['noi'] \
        / att_p['hard']['purchase_price']) * 100, 2)

    # This number is the income from the property after all expenses
    # AND the mortgage.
    att_p['calc']['ideal_cashflow'] = (att_p['calc']['noi'] / 12) \
        - att_p['calc']['mortgage_payment']

    # This is a conservative version of ideal_cashflow
    # - it subtracts vacancy and maintenance expenses
    att_p['calc']['medium_cashflow'] = (att_p['calc']['noi'] / 12) - att_p\
        ['cost']['capex_dollar'] - att_p['cost']['vacancy_rate_dollar'] - \
            att_p['calc']['mortgage_payment']

    # This takes 50% off of the income and then subtracts expenses
    att_p['calc']['long_cashflow'] = att_p['hard']['rent'] - (att_p['hard']\
        ['rent'] * 0.5) - att_p['calc']['mortgage_payment'] - att_p['cost']\
            ['hoa_misc']

    # Annual NOI minus mortgage payments.
    att_p['calc']['annual_cashflow'] = ((att_p['calc']['noi'] / 12) \
        - att_p['calc']['mortgage_payment']) * 12

    # This is the sum of downpayment,
    # all closing costs and potential renovations.
    att_p['calc']['purchase_cost'] = att_p['mortgage']['down_payment_dollar'] \
        + att_p['cost']['closing_costs_dollar'] \
        + att_p['cost']['renovation_budget']

    # This is the yearly return you receive on your investment
    att_p['calc']['cash_on_cash'] = round(att_p['calc']['annual_cashflow'] \
        / att_p['calc']['purchase_cost'] * 100, 2)

    # For aggregation views
    att_p['calc']['monthly_expenses'] = (att_p['cost']['property_insurance'] \
        + att_p['cost']['property_taxes'])/12 \
        + att_p['cost']['property_management_dollar'] \
        + att_p['calc']['mortgage_payment']
    att_p['calc']['monthly_reserve'] = att_p['cost']['vacancy_rate_dollar'] \
        + att_p['cost']['capex_dollar']
    att_p['calc']['monthly_cash_flow'] = att_p['hard']['rent'] \
        - att_p['calc']['monthly_expenses'] \
        - att_p['calc']['monthly_reserve']
    att_p['calc']['total_cost'] = att_p['mortgage']['down_payment_dollar'] \
        + att_p['cost']['closing_costs_dollar'] \
        + att_p['cost']['renovation_budget']

    # Get the full loan schedule
    if att_p['mortgage']['down_payment_percent'] < 100:
        # Run simulations here: http://nepotism.net/amort/
        loan = Loan(origindate=datetime.now().strftime("%Y-%m-%d"),
                    loan_amount=att_p['calc']['mortgage_principle'],
                    interest=att_p['mortgage']['rate'],
                    days="actual",
                    basis="actual",
                    number_of_payments=int(att_p['mortgage']['term'] * 12))
        loan_schedule = loan.amort()

    # Get first year mortgage principle
    payment_num = 1
    principle = 0
    if att_p['mortgage']['down_payment_percent'] == 100:
        att_p['calc']['first_year_principle'] = 0
        att_p['calc']['monthly_principle'] = 0
    else:
        if 'loan_schedule' in locals():
            while payment_num < 13:
                # Break while loop if payment_num not in loan_schedule
                if payment_num > len(loan_schedule):
                    break
                # Check index 6 in loan_schedule[payment_num]
                principle += loan_schedule[payment_num][6] \
                    if len(loan_schedule[payment_num]) > 6 else 0
                payment_num += 1
        att_p['calc']['first_year_principle'] = principle
        att_p['calc']['monthly_principle'] = principle/12

    # Build full amortization schedule HTML + JS Graph
    yearly_appreciation = 1.03         # 3% default for now
    monthly_appreciation = pow(yearly_appreciation, (1/float(12)))
    property_value_int = att_p['hard']['valuation']
    equity_value_int = att_p['hard']['valuation'] \
        - (att_p['mortgage']['down_payment_dollar'] \
        / float(att_p['mortgage']['down_payment_percent']/float(100)) \
        * (1 - att_p['mortgage']['down_payment_percent']/float(100)))

    loan_balance = ""
    property_value = ""
    equity_value = ""
    amortization_html = ""
    mortgage_start = ""
    #mortgage_end = ""
    amort_total_payment = 0
    amort_total_interest = 0
    amort_total_principal = 0
    interval_unixtime = 0
    if att_p['mortgage']['down_payment_percent'] < 100:
        for row in loan_schedule:
            interval_unixtime = time.mktime(row[1].timetuple())
            property_value_int = property_value_int * monthly_appreciation
            equity_value_int = property_value_int - row[7]

            # if first loop
            if row[0] == 1:
                mortgage_start = interval_unixtime
                format_string = "[{ut}, {v}]"
            else:
                format_string = ", [{ut}, {v}]"

            loan_balance += format_string.format(ut=interval_unixtime,
                                                 v=row[7])
            property_value += format_string.format(ut=interval_unixtime,
                                                   v=property_value_int)
            equity_value += format_string.format(ut=interval_unixtime,
                                                 v=equity_value_int)

            amort_total_payment += row[3]
            amort_total_interest += row[5]
            amort_total_principal += row[6]

            amortization_html += """
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>${}</td>
                <td>${}</td>
                <td>${}</td>
                <td>${}</td>
                <td>${}</td>
            </tr>
            """.format(row[0],
                       row[1],
                       format_one(row[2]),
                       format_one(row[3]),
                       format_one(row[5]),
                       format_one(row[6]),
                       format_one(row[7]))

    # Add amortization total
    amortization_html += """
    <tr>
        <th>TOTAL</th>
        <td>&nbsp;</td>
        <td>&nbsp;</td>
        <td>${}</td>
        <td>${}</td>
        <td>${}</td>
        <td>&nbsp;</td>
    </tr>
    """.format(format_one(amort_total_payment),
               format_one(amort_total_interest),
               format_one(amort_total_principal))


    att_p['calc']['amortization_schedule'] = amortization_html
    att_p['calc']['mortgage_start'] = mortgage_start
    if interval_unixtime:
        att_p['calc']['mortgage_end'] = interval_unixtime
    else:
        att_p['calc']['mortgage_end'] = mortgage_start
    att_p['calc']['chart_loan_balance'] = loan_balance
    att_p['calc']['chart_property_value'] = property_value
    att_p['calc']['chart_equity_value'] = equity_value

    return att_p

# pylint: disable=W0621
def build_header(title="Rental Real Estate by Listen Money Matters",
                 request=request,
                 active=None,
                 message=None,
                 message_type="danger"):
    """Header building"""
    message_html = ""
    if message:
        message_html = u"""
        <div class="alert alert-{0}">
            <a class="close" data-dismiss="alert"
                href="#" aria-hidden="true">×</a>
            {1}
        </div>
        """.format(message_type, message)

    # Pull in all of our Stripe info
    #stripe.api_key = get_stripe(request_url=request.url)

    # if session['profile'].get('is_trial', None) \
    #         and session['profile']['is_trial'] is not 0:
    #     session['profile']['access_level'] = "basic"
    # elif session['profile'].get('stripe_id', None):
    #     session['profile']['customer'] = retrive_customer(stripe=stripe, \
    #         customer_id=session['profile']['stripe_id'])
    #
    #     if session['profile']['access_level'] != "free":
    #         if session['profile']['customer'] and \
    #                 session['profile']['customer'].get('subscriptions', None):
    #             if session['profile']['customer']['subscriptions']\
    #                     ['total_count'] == 0:
    #                 session['profile']['access_level'] = "basic"
    #             else:
    #                 session['profile']['access_level'] = "pro"
    #         else:
    #             session['profile']['access_level'] = "basic"
    #     else:
    #         session['profile']['access_level'] = "basic"



    AUTH0['AUTH0_CALLBACK_URL'] = get_url(request.url, 'root') + '/callback'
    header = {
        'title': title,
        'active': str(request.url).split('/')[4] if not active else active,
        'url_root': get_url(request.url, 'root'),
        'property_history': PG.get_history(session['profile']['user_id'],
                                           'property view'),
        'property_groups': PG.get_groups(session['profile']['user_id']),
        'message': message_html
    }
    return header

def get_property_base_on_session(vproperty):
    """Get property base on session"""
    session['portfolios'] = PG.get_groups(session['profile']['user_id'])

    # Create a session key for this property and give it some details
    if session.get(vproperty['address']) is None:

        if session['profile']['user_id'] != -1:
            # Check DB First
            session[vproperty['address']] = PG.get_property(
                vproperty['address'],
                session['profile']['user_id']
            )
        else:
            session[vproperty['address']] = None

    if session[vproperty['address']]:
        if session[vproperty['address']].get("portfolio_id"):
            if session[vproperty['address']]["portfolio_id"] is None:
                session[vproperty['address']] = PG.get_property(\
                    vproperty['address'], session['profile']['user_id'])

            group = PG.get_group_by_property_id(
                session['profile']['user_id'],
                session[vproperty['address']]["property_id"]
            )

            if group:
                session[vproperty['address']]\
                    ["portfolio_name"] = group["portfolio_name"]
            else:
                session[vproperty['address']]\
                    ["portfolio_name"] = "My Saved Properties"

        session[vproperty['address']] = run_calculations(
            session[vproperty['address']]
        )

    else:
        session[vproperty['address']] = get_property_info(
            session,
            vproperty['address'],
            vproperty['zillow']['zpid']
        )
        session[vproperty['address']] = init_costs\
            (session[vproperty['address']])
        session[vproperty['address']] = run_calculations\
            (session[vproperty['address']])

    if session[vproperty['address']].get('portfolio_id') is not None:
        hashids = Hashids()
        session[vproperty['address']]['hashid'] = hashids.encode(\
            session[vproperty['address']]['property_id'])

    return session[vproperty['address']]

def update_coordinate(vproperty):
    """Update coordinate"""
    empty_cases = ['', None, 'None']
    if vproperty['hard']['latitude'] in empty_cases or \
            vproperty['hard']['longitude'] in empty_cases:
        coordinate = get_coordinate_from_address(vproperty['address'][\
            :vproperty['address'].rfind('_')]\
                .replace('_', ",").replace('-', '+'))
        if coordinate:
            vproperty['hard']['latitude'] = coordinate['lat']
            vproperty['hard']['longitude'] = coordinate['lng']
    return vproperty

@app.context_processor
def override_url_for():
    """Override url"""
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    """Date url"""
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


# Custom template filters
@app.template_filter('currency')
def currency_filter(value):
    """Currency filter"""
    return "${:,.2f}".format(int(value))

@app.template_filter('pretty_address')
def pretty_address_filter(address):
    """Pretty address filter"""
    address_list = address.split('_')
    pretty_address = [a.replace("-", " ") for a in address_list]
    if isinstance(pretty_address, list) and len(pretty_address) == 3:
        pretty_address = "{}, {}, {}".format(pretty_address[0],
                                             pretty_address[1],
                                             pretty_address[2])
    else:
        pretty_address = "N/A"
    return pretty_address

# Stripe callback - Mavu 20170508
@app.route('/callbackstripe', methods=['POST'])
@CSRF.exempt
def callback_stripe():
    """This is a webhook for Stripe
    Update is_trial = 2 and cancel the subscription
    """
    data = json.loads(request.data)
    s_type = data.get('type', None)
    if s_type and s_type == 'invoice.created':
        customer = get_retrive_customer(request.url,
                                        data['data']['object']['customer'])
        if customer:
            subscriptions = customer.subscriptions.all()
            if subscriptions.data:
                subscriptions = customer.subscriptions.data[0]
                plan = subscriptions.plan.id
                status = subscriptions.status
                if plan == "default" and status == "active":
                    PG.update_is_trial(customer.email, 2)
                    customer.cancel_subscription()
                    return Response(status=200)

    return Response(status=400)

if __name__ == '__main__':
    app.run(debug=True)
