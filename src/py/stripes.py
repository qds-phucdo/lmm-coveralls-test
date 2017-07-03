"""Stripe Methods"""
import sys
import os
from os import path
sys.path.append(os.getcwd())
import time
import stripe
from datetime import datetime
from src.py.pg import PGWriter
PG = PGWriter()

# Reference:
# https://stripe.com/docs/api#create_subscription-trial_period_days
# https://stripe.com/docs/api#subscription_object-status

def get_stripe_data(user):
    """Returns the Stripe data for a user"""

    stripe.api_key = get_stripe_key(user['request_url'])

    # Free user
    if user['access_level'] == "free":
        user['is_trial'] = 0
        return user

    # Everyone else
    else:
        # No stripe_id is a new user, otherwise retrieve details from stripe
        if user.get('stripe_id', None) is None:
            customer = create_stripe_default_customer(stripe, user['email'])
            PG.update_stripeid_and_trial_flag(user['email'], customer.id)
        else:
            customer = retrive_customer(stripe, user['stripe_id'])

        subscriptions = customer.subscriptions.all()

        # This should pretty much always be true.
        if subscriptions.data:
            status = subscriptions.data[0].status
            plan_id = subscriptions.data[0].plan.id
            plan_amount = subscriptions.data[0].plan.amount

            # New user trial
            if status == "trialing":
                sell_to = "true"
                period_end = customer.subscriptions.data[0].current_period_end
                trial_end = datetime.fromtimestamp(int(period_end))
                day = time.strftime("%d", time.localtime(int(period_end)))
                month = time.strftime("%b", time.localtime(int(period_end)))

            # Paying customer
            else:
                sell_to = "false"
                created = subscriptions.data[0].created
                trial_end = created
                day = datetime.fromtimestamp(int(created)).strftime('%d')
                month = datetime.fromtimestamp(int(created)).strftime('%B')

        # To catch canceled users
        else:
            status = 'trialing'
            sell_to = "true"
            plan_id = 'default'
            plan_amount = 0
            trial_end = datetime.utcnow()
            day = trial_end.strftime("%d")
            month = trial_end.strftime("%B")

        # Add stripe details to user dictionary in session['profile']
        user_stripe = {
            'stripe_id': customer.id,
            'customer': customer,
            'access_level': 'basic' if status == 'trialing' else 'pro',
            'trial_end': trial_end,
            'sell_to': sell_to,
            'status': status,
            'subscription': {
                'month': month,
                'day': day + get_suffix(day),
                'plan': {
                    'id': plan_id,
                    'amount': plan_amount,
                }
            }
        }
        user.update(user_stripe)

        return user

    # This should really never happen
    return None

# MaVu - 20170504
def create_stripe_default_customer(stripe, email): # pylint: disable=W0621
    """Create new stripe customer for new register"""
    plan = retrive_or_create_default_plan(stripe=stripe)
    card = {
        "number": os.environ.get('STRIPE_CARD_NUMBER'),
        "exp_month": os.environ.get('STRIPE_CARD_EXP_MONTH'),
        "exp_year": os.environ.get('STRIPE_CARD_EXP_YEAR'),
        "cvc": os.environ.get('STRIPE_CARD_CVC')
    }
    try:
        result = stripe.Token.create(card=card)
        customer = stripe.Customer.create(
            source=result["id"],
            plan=plan,
            email=email
        )
        return customer
    except: # pylint: disable=W0702
        return
    return

# MaVu - 20170504
def retrive_or_create_default_plan(stripe): # pylint: disable=W0621
    """Retrive or Create default plan, return Plan Id or None"""
    try:
        result = retrive_plan(stripe=stripe, plan="default")
        if result is None:
            result = stripe.Plan.create(
                amount=0,
                interval="month",
                name="Default for new register",
                currency="usd",
                id="default",
                trial_period_days=int(os.environ.get('TRIAL_END_DAY'))
            )
        return result.id
    except: # pylint: disable=W0702
        return

# MaVu - 20170504
def retrive_plan(stripe, plan): # pylint: disable=W0621
    """Retrive a plan, return Object or None"""
    try:
        return stripe.Plan.retrieve(plan)
    except: # pylint: disable=W0702
        return
    return

# MaVu - 20170505
def retrive_customer(stripe, customer_id): # pylint: disable=W0621
    """Retrive a customer by Id, return Object or None"""
    try:
        return stripe.Customer.retrieve(customer_id)
    except:# pylint: disable=W0702
        return
    return

# MaVu - 20170524 - Phuc re edit
def get_stripe_key(request_url):
    """Detect stripe key"""

    if 'stg-pro' in request_url:
        return os.environ.get('STRIPE_API_KEY_TEST')
    elif 'pro' in request_url or 'simplewealth.co' in request_url:
        return os.environ.get('STRIPE_API_KEY')

    return os.environ.get('STRIPE_API_KEY_TEST')

#PhucDo - 20170606
def update_card(user):
    """Update card to stripe"""

    stripe.api_key = get_stripe_key(user['request_url'])
    try:
        customer = retrive_customer(stripe, user['stripe_id'])
        card = customer.sources.create(\
            source=user['stripeToken'])
        newcard_id = card.id
        customer.default_source = newcard_id
        customer.save()
        return True
    except: # pylint: disable=W0702
        return False

#PhucDo - 20170606
def update_subscription(user):
    """Update subscription to stripe"""
    stripe.api_key = get_stripe_key(user['request_url'])
    try:
        customer = retrive_customer(stripe, user['stripe_id'])
        card = customer.sources.create(\
            source=user['stripeToken'])

        newcard_id = card.id
        customer.default_source = newcard_id
        customer.update_subscription(plan=user['plan'])
        customer.save()
        PG.update_is_trial(user['email'], 0)
        return True
    except: # pylint: disable=W0702
        return False

#PhucDo - 20170606
def cancel_membership(user):
    """Cancel subscription to stripe"""
    stripe.api_key = get_stripe_key(user['request_url'])
    try:
        customer = retrive_customer(stripe, user['stripe_id'])
        customer.cancel_subscription()
        PG.update_is_trial(user['email'], user['is_trial'])
        return True
    except:# pylint: disable=W0702
        return False

# MaVu - 20170505
def get_retrive_customer(url, user_stripe_id): # pylint: disable=W0621
    """Retrive a customer by Id, return Object or None"""
    stripe.api_key = get_stripe_key(url)
    try:
        return retrive_customer(stripe, user_stripe_id)
    except:# pylint: disable=W0702
        return
    return

#PhucDo - 20170609 for test
def create_token(user):
    stripe.api_key = get_stripe_key(user['request_url'])
    try:
        token = stripe.Token.create(
            card={
                "number": os.environ['STRIPE_CARD_NUMBER'],
                "exp_month": os.environ['STRIPE_CARD_EXP_MONTH'],
                "exp_year": os.environ['STRIPE_CARD_EXP_YEAR'],
                "cvc": os.environ['STRIPE_CARD_CVC'],
            },
        )
        return token
    except:
        return False

def get_suffix(day):
    if 4 <= int(day) <= 20 or 24 <= int(day) <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][int(day) % 10 - 1]

    return suffix
