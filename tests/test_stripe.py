"""Stripe Unittest"""
import sys
import os
import requests
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import unittest
from src.py.stripes import (get_stripe_data,
                            update_card,
                            update_subscription,
                            cancel_membership,
                            get_retrive_customer,
                            create_token)
from src.py.pg import PGWriter
PG = PGWriter()

#1 Create user
#2 Create Stripe customer
#3 Assign subscription default for customer
#4 Update Stripe Id into PG and update is_trial = 1
USERS = [
    {
        'email': 'test1@quodisys.com',
        'access_level': 'basic',
        'request_url': 'local',
        'is_trial': 0,
        'plan': 'pro'
    },
    {
        'email': 'test2@quodisys.com',
        'access_level': 'basic',
        'request_url': 'local',
        'is_trial': 0,
        'plan': 'proyearly'
    }
]
#Customer purchase subscription => is_trial = 0
USERS_PURCHASE = []
USERS_EXPIRED = []
# pylint: disable=W0232,C1001
class TestStripe(unittest.TestCase):
    # preparing to test
    def setUp(self):
        """ Setting up for the test """
        self.result = ''

    def tearDown(self):
        """Cleaning up after the test"""
        print '*****Result***** \n' + self.result

    def test_create_customer(self):
         self.result = 'Test create customer =>\n'
         for item in list(USERS):
             PG.delete_user(item['email'])

         for item in list(USERS):
             user = PG.get_user(item['email'])

             self.result+='-----------------------------\n';
             self.result+='- User '+user['email']+' insert into PG\n'
             data = get_stripe_data(item)
             if data['status'] is not None:
                 self.result += "- "+item['email'] + " created on Stripe with ID "+ data['stripe_id']\
                 +" status : "+data['status']+"\n"
                 obj_user = {
                    'email': item['email'],
                    'stripe_id': data['stripe_id'],
                    'request_url': 'local',
                    'plan':''
                 }
                 USERS_EXPIRED.append(obj_user)

             self.result+='- Updated stripe_id='+data['stripe_id']+' and is_trial=1 into PG\n'
             self.result+='-----------------------------\n\n'
             self.assertIsNotNone(data,\
             'Can not create customer: '+item['email'])

         self.result += 'Finished test create customer----------\n\n'

    def test_subscription_expired(self):
        self.result = 'Test subscription expired =>\n'

        for item in list(USERS_EXPIRED):
            self.result+='-----------------------------\n';
            data = get_retrive_customer(item['request_url'],item['stripe_id'])
            subscriptions = data.subscriptions.all()
            if subscriptions.data:
                if  data.subscriptions.data[0].plan.id == 'default'\
                    and data.subscriptions.data[0].status == 'active':
                    PG.update_is_trial(item['email'], 2)
                    data.cancel_subscription()
                    self.result+='Client :'+item['email']+' trial expired, Cancel subscription successfull, update is_trial = 2\\n'
                self.result+='-----------------------------\n\n'
            self.assertIsNotNone(data,\
                'Error: '+item['email'])
        self.result = 'End test subscription expired'

    def test_purchase(self):
        self.result = 'Test purchase =>\n'
        USERS_PURCHASE = USERS_EXPIRED
        USERS_PURCHASE[0]['plan'] = 'pro'
        USERS_PURCHASE[1]['plan'] = 'proyearly'
        for item in list(USERS_PURCHASE):
            token = create_token(item)
            item['stripeToken'] = token['id']
            data = update_subscription(item)
            self.result+='-----------------------------\n';
            if data is True:
                self.result += "- "+item['email'] + " purchase successfull, plan: "+item['plan']+"\n"
            else:
                self.result += "- "+item['email'] + " purchase false, plan: "+item['plan']+"\n"
            self.result+='-----------------------------\n\n'

        self.assertIsNotNone(data,\
            'Error: '+item['email'])
        self.result += 'Finished test purchase----------\n\n'

if __name__ == '__main__':
    # run all TestCase's in this module
    unittest.main()
