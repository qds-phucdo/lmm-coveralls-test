# pylint: disable=C0302
"""Database Processing"""
from datetime import datetime, timedelta
import urlparse
import pickle
import sys
import os
from os import path
sys.path.append(os.getcwd())
import psycopg2
import psycopg2.extras

urlparse.uses_netloc.append("postgres")
URL = urlparse.urlparse(os.environ["DATABASE_URL"])

# Simple class to make sure we keep our PG tidy and cheap (for now)
# pylint: disable=R0904,C1001
class PGWriter():
    """Business Logical"""
    conn = None

    def __init__(self):
        self.conn = psycopg2.connect(
            database=URL.path[1:],
            user=URL.username,
            password=URL.password,
            host=URL.hostname,
            port=URL.port
        )

    def get_conn(self):
        """Connection"""
        self.conn.autocommit = True
        return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql):
        """Execute sql string"""
        conn = self.get_conn()
        conn.execute(sql)
        conn.close()

    def fetch(self, sql):
        """Fetch"""
        conn = self.get_conn()
        conn.execute(sql)
        results = conn.fetchall()
        conn.close()
        return results

    def fetchone(self, sql):
        """Fetchone"""
        conn = self.get_conn()
        conn.execute(sql)
        results = conn.fetchone()
        conn.close()
        return results

    def get_coach(self, slug):
        """get_coach"""
        query_get = """
        SELECT * FROM public.coaches WHERE slug='{}';
        """.format(slug)
        result = self.fetchone(query_get)
        return result

    def get_coach_packages(self, slug):
        """get_coach_packages"""
        query_get = """
        SELECT * FROM public.coach_packages WHERE coach_slug='{}' ORDER BY orderid ASC;
        """.format(slug)
        result = self.fetch(query_get)
        return result

    def get_active_coaches(self):
        """get_active_coaches"""
        query_get = """
        SELECT * FROM public.coaches WHERE is_active is true ORDER BY orderid ASC;
        """
        result = self.fetch(query_get)
        return result

    def get_user(self, email):
        """get_user"""
        query_get = """
        SELECT
            *,
            date_part('epoch',create_dt)::int as create_timestamp
        FROM
            public.user_details WHERE email='{}';
        """.format(email)
        result = self.fetchone(query_get)

        if not result:
            query_set = """
            INSERT INTO public.user_details (email) VALUES('{}');
            """.format(email)
            self.execute(query_set)
            result = self.fetchone(query_get)
            result['welcome'] = 1
        return result

    def update_user_track(self, email, utm_source, utm_medium, utm_campaign):
        """Update user"""
        query_set = """
        UPDATE public.user_details
        SET utm_source='{utm_source}', utm_medium='{utm_medium}',
        utm_campaign='{utm_campaign}'
        WHERE email='{email}'
        """.format(
            email=email,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign
        )
        self.execute(query_set)

    def update_access_level(self, email, access_level="basic"):
        """update_access_level"""
        query_set = """
        UPDATE public.user_details
        SET access_level='{access_level}'
        WHERE email='{email}'
        """.format(
            access_level=access_level,
            email=email
        )
        self.execute(query_set)

    def update_stripe_id(self, email, stripe_id="null", is_trial=0):
        '''Update user stripe, access_level, is_trail for update or cancel
        is_trial = 0 is not on trial time
        is_trial = 1 is on trial time
        is_trial = 2 is trial expired
        '''
        if stripe_id != "null":
            stripe_id = "'{}'".format(stripe_id)
            access_level = "pro"
        else:
            access_level = "basic"

        query_set = """
        UPDATE public.user_details
        SET stripe_id={stripe_id}, access_level='{access_level}', is_trial={is_trial}
        WHERE email='{email}'
        """.format(
            stripe_id=stripe_id,
            access_level=access_level,
            email=email,
            is_trial=is_trial
        )
        self.execute(query_set)

    def update_stripeid_and_trial_flag(self, email, stripe_id):
        """update_stripeid_and_trial_flag"""
        stripe_id = "'{}'".format(stripe_id)
        query_set = """
        UPDATE public.user_details
        SET stripe_id={stripe_id}, is_trial=1
        WHERE email='{email}'
        """.format(
            stripe_id=stripe_id,
            email=email
        )
        self.execute(query_set)

    def update_is_trial(self, email, is_trial):
        '''Update is_trial fields
        is_trial = 2 trial is expired, updated by stripe
        is_trial = 1 on trial
        is_trial = 0 not on trial
        '''
        query_set = """
        UPDATE public.user_details
        SET is_trial={is_trial}
        WHERE email='{email}'
        """.format(
            email=email,
            is_trial=is_trial
        )
        self.execute(query_set)

    # pylint: disable=R0913
    def log_error(self, user_id, error_id, error_desc, error_url, debug_data):
        '''Store error'''
        debug_data = psycopg2.Binary(pickle.dumps(debug_data, -1))
        query_set = """
        INSERT INTO public.error_log
        (user_id, error_id, error_desc, error_url, debug_data)
        VALUES({user_id}, '{error_id}', '{error_desc}', '{error_url}', {debug_data})
        """.format(
            user_id=user_id,
            error_id=error_id,
            error_desc=error_desc,
            error_url=error_url,
            debug_data=debug_data
        )
        self.execute(query_set)

    def log_action(self, user_id, action_type, action_text):
        '''Store history'''
        query_set = """
        UPDATE public.history SET create_dt=now()
        WHERE user_id={uid} and action_type='{atype}' and action_text='{atext}';
        INSERT INTO public.history (user_id, action_type, action_text)
            SELECT '{uid}', '{atype}', '{atext}' WHERE NOT EXISTS (
                SELECT 1 FROM public.history
                WHERE user_id={uid} and action_type='{atype}' and action_text='{atext}');
        """.format(
            uid=user_id,
            atype=action_type,
            atext=action_text.replace("'", "''") # Replace single quotes by "''"
            # to fix SQL query error
        )
        return self.execute(query_set)

    def get_history(self, user_id, action_type='property view'):
        '''Get history'''
        query_get = """
        SELECT REPLACE(REPLACE(action_text, ',', ''), '.00', '') as action_text, max(create_dt) as create_dt
        FROM public.history
        WHERE user_id={user_id} AND action_type='{action_type}'
        GROUP BY REPLACE(REPLACE(action_text, ',', ''), '.00', '')
        ORDER BY create_dt DESC LIMIT 5;
        """.format(user_id=user_id, action_type=action_type)
        return self.fetch(query_get)

    def get_property(self, property_name=None, user_id=None, property_id=None):
        '''Get property'''
        if property_name is not None:
            query_get = """
            SELECT *
            FROM public.properties
            WHERE property_name='{property_name}' and user_id={user_id};
            """.format(
                property_name=property_name,
                user_id=user_id
            )
            result = self.fetchone(query_get)
        else:
            query_get = """
            SELECT *
            FROM public.properties
            WHERE property_id={property_id};
            """.format(property_id=property_id)
            result = self.fetchone(query_get)

        if result:
            address_list = result['property_name'].split('_')
            pretty_address = [a.replace("-", " ") for a in address_list]
            pretty_address = "{}, {}, {}".format(pretty_address[0], \
            pretty_address[1], pretty_address[2])

            if result['images']:
                images = pickle.loads(str(result['images']))
            else:
                images = None

            at_property = {
                'property_id': result['property_id'],
                'address': result['property_name'],
                'portfolio_id': result['portfolio_id'],
                'street_address': result['street_address'],
                'zip_code': result['zip_code'],
                'pretty_address': pretty_address,
                'zpid': result['zpid'], # fix for some cases
                'zillow': {
                    'zpid': result['zpid']
                },
                'housecanary': {},
                'hard': {
                    'latitude': result['latitude'],
                    'longitude': result['longitude'],
                    'valuation': result['valuation'],
                    'purchase_price': result['purchase_price'],
                    'rent': result['rent']
                },
                'soft': {
                    'images': images,
                    'finished_sqft': result['finished_sqft'],
                    'bedrooms': result['bedrooms'],
                    'bathrooms': result['bathrooms']
                },
                'mortgage': {
                    'down_payment_dollar': result['down_payment_dollar'],
                    'down_payment_percent': result['down_payment_percent'],
                    'rate': result['mortgage_rate'],
                    'term': result['mortgage_term'],
                    'points': result['mortgage_points']
                },
                'cost': {
                    'property_taxes': result['property_taxes'],
                    'property_insurance': result['property_insurance'],
                    'renovation_budget': result['renovation_budget'],
                    'hoa_misc': result['hoa_misc'],
                    'closing_costs_dollar': result['closing_costs_dollar'],
                    'closing_costs_percent': result['closing_costs_percent'],
                    'property_management_dollar': result\
                        ['property_management_dollar'],
                    'property_management_percent': result\
                        ['property_management_percent'],
                    'vacancy_rate_dollar': result['vacancy_rate_dollar'],
                    'vacancy_rate_percent': result['vacancy_rate_percent'],
                    'capex_dollar': result['capex_dollar'],
                    'capex_percent': result['capex_percent']
                },
                'calc': {},
                'refresh': '<i id="refresh" class="fa fa-refresh'\
                    ' kv-icon kv-icon-secondary"></i>',
                'is_manual': result.get('is_manual', 0)
            }
        else:
            at_property = None

        return at_property


    def save_property(self, prope, user_id, portfolio_id=-1):
        '''Save property data'''
        if prope['soft'] not in [0, 1]:
            finished_sqft = prope['soft']['finished_sqft']
            bedrooms = prope['soft']['bedrooms']
            bathrooms = prope['soft']['bathrooms']

            if prope['soft'].get('images') is not None:
                images_safe = psycopg2.Binary(pickle.dumps(\
                    prope['soft']['images'], -1))
            else:
                images_safe = "null"
        else:
            images_safe = "null"
            finished_sqft = ""
            bedrooms = ""
            bathrooms = ""

        is_manual = prope.get('is_manual', 0) if isinstance(\
            prope.get('is_manual', 0), int) else 0

        query_set = """
        INSERT INTO public.properties (
            property_name, user_id, portfolio_id, is_owned, street_address, zip_code,
            zpid, latitude, longitude, valuation, purchase_price, rent, down_payment_dollar,
            down_payment_percent, mortgage_rate, mortgage_term, mortgage_points,
            property_taxes, property_insurance, renovation_budget, hoa_misc,
            closing_costs_dollar, closing_costs_percent, property_management_dollar,
            property_management_percent, vacancy_rate_dollar, vacancy_rate_percent,
            capex_dollar, capex_percent, images, finished_sqft, bedrooms, bathrooms, is_manual
        )
        VALUES (
            '{property_name}', {user_id}, {portfolio_id}, {is_owned}, '{street_address}', '{zip_code}', '{zpid}',
            '{latitude}', '{longitude}', {valuation}, {purchase_price}, {rent}, {down_payment_dollar}, {down_payment_percent},
            {mortgage_rate}, {mortgage_term}, {mortgage_points}, {property_taxes}, {property_insurance}, {renovation_budget},
            {hoa_misc}, {closing_costs_dollar}, {closing_costs_percent}, {property_management_dollar}, {property_management_percent},
            {vacancy_rate_dollar}, {vacancy_rate_percent}, {capex_dollar}, {capex_percent}, {images}, '{finished_sqft}', '{bedrooms}',
            '{bathrooms}', '{is_manual}'
        )
        """.format(
            property_name=prope['address'],
            user_id=user_id,
            portfolio_id=portfolio_id,
            is_owned='false',
            street_address=prope['street_address'],
            zip_code=prope['zip_code'],
            zpid=prope['zpid'],
            latitude=prope['hard']['latitude'],
            longitude=prope['hard']['longitude'],
            valuation=prope['hard']['valuation'],
            purchase_price=prope['hard']['purchase_price'],
            rent=prope['hard']['rent'],
            down_payment_dollar=prope['mortgage']['down_payment_dollar'],
            down_payment_percent=prope['mortgage']['down_payment_percent'],
            mortgage_rate=prope['mortgage']['rate'],
            mortgage_term=prope['mortgage']['term'],
            mortgage_points=prope['mortgage']['points'],
            property_taxes=prope['cost']['property_taxes'],
            property_insurance=prope['cost']['property_insurance'],
            renovation_budget=prope['cost']['renovation_budget'],
            hoa_misc=prope['cost']['hoa_misc'],
            closing_costs_dollar=prope['cost']['closing_costs_dollar'],
            closing_costs_percent=prope['cost']['closing_costs_percent'],
            property_management_dollar=prope['cost']\
                ['property_management_dollar'],
            property_management_percent=prope['cost']\
                ['property_management_percent'],
            vacancy_rate_dollar=prope['cost']['vacancy_rate_dollar'],
            vacancy_rate_percent=prope['cost']['vacancy_rate_percent'],
            capex_dollar=prope['cost']['capex_dollar'],
            capex_percent=prope['cost']['capex_percent'],
            images=images_safe,
            finished_sqft=finished_sqft,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            is_manual=is_manual
        )
        self.execute(query_set)

        at_property = self.get_property(prope['address'], user_id)
        return at_property['property_id']

    def update_property(self, prope, user_id):
        '''Update property'''
        is_manual = prope.get('is_manual', 0) if isinstance(\
            prope.get('is_manual', 0), int) else 0
        query_set = """
        UPDATE public.properties
        SET purchase_price={purchase_price}, valuation={valuation}, rent={rent}, down_payment_dollar={down_payment_dollar},
            down_payment_percent={down_payment_percent}, mortgage_rate={mortgage_rate}, mortgage_term={mortgage_term},
            mortgage_points={mortgage_points}, property_taxes={property_taxes}, property_insurance={property_insurance},
            renovation_budget={renovation_budget}, hoa_misc={hoa_misc}, closing_costs_dollar={closing_costs_dollar},
            closing_costs_percent={closing_costs_percent}, property_management_dollar={property_management_dollar},
            property_management_percent={property_management_percent}, vacancy_rate_dollar={vacancy_rate_dollar},
            vacancy_rate_percent={vacancy_rate_percent}, capex_dollar={capex_dollar}, capex_percent={capex_percent},
            update_dt='{update_dt}', is_manual='{is_manual}'
        WHERE property_name='{property_name}' AND user_id={user_id}
        """.format(
            purchase_price=prope['hard']['purchase_price'],
            valuation=prope['hard']['valuation'],
            rent=prope['hard']['rent'],
            down_payment_dollar=prope['mortgage']['down_payment_dollar'],
            down_payment_percent=prope['mortgage']['down_payment_percent'],
            mortgage_rate=prope['mortgage']['rate'],
            mortgage_term=prope['mortgage']['term'],
            mortgage_points=prope['mortgage']['points'],
            property_taxes=prope['cost']['property_taxes'],
            property_insurance=prope['cost']['property_insurance'],
            renovation_budget=prope['cost']['renovation_budget'],
            hoa_misc=prope['cost']['hoa_misc'],
            closing_costs_dollar=prope['cost']['closing_costs_dollar'],
            closing_costs_percent=prope['cost']['closing_costs_percent'],
            property_management_dollar=prope['cost']\
                ['property_management_dollar'],
            property_management_percent=prope['cost']\
                ['property_management_percent'],
            vacancy_rate_dollar=prope['cost']['vacancy_rate_dollar'],
            vacancy_rate_percent=prope['cost']['vacancy_rate_percent'],
            capex_dollar=prope['cost']['capex_dollar'],
            capex_percent=prope['cost']['capex_percent'],
            update_dt=datetime.now(),
            property_name=prope['address'],
            user_id=user_id,
            is_manual=is_manual
        )
        return self.execute(query_set)

    def add_property_to_portfolio(self, prope, user_id, portfolio_id):
        '''Add to protfolio'''
        query_set = """
        UPDATE public.properties
        SET portfolio_id={portfolio_id}
        WHERE property_name='{property_name}' and user_id={user_id}
        """.format(
            portfolio_id=portfolio_id,
            property_name=prope['address'],
            user_id=user_id
        )
        return self.execute(query_set)

    def delete_property(self, prope, user_id):
        '''Delete a property'''
        query_set = """
        DELETE FROM public.properties
        WHERE property_name='{property_name}' AND user_id={user_id}
        """.format(
            property_name=prope['address'],
            user_id=user_id
        )
        return self.execute(query_set)

    def update_group_name(self, new_name, old_name, user_id):
        '''Edit group name'''
        query_get = """
        SELECT * FROM public.portfolios
        WHERE portfolio_name='{new_name}' and user_id={user_id};
        """.format(
            new_name=new_name,
            user_id=user_id
        )
        result = self.fetchone(query_get)

        # No group has the same name, change name
        if not result:
            query_set = """
            UPDATE public.portfolios
            SET portfolio_name='{new_name}'
            WHERE portfolio_name='{old_name}' AND user_id={user_id}
            """.format(
                new_name=new_name,
                old_name=old_name,
                user_id=user_id
            )
            return self.execute(query_set)

        # If group name already exists, combine groups
        query_get = """
        SELECT * FROM public.portfolios
        WHERE portfolio_name='{old_name}' and user_id={user_id};
        """.format(
            old_name=old_name,
            user_id=user_id
        )
        old_group = self.fetchone(query_get)

        # Move all properties from old_name to new_name
        query_set = """
        UPDATE public.properties
        SET portfolio_id={new_id}
        WHERE portfolio_id={old_id} AND user_id={user_id}
        """.format(
            new_id=result['portfolio_id'],
            old_id=old_group['portfolio_id'],
            user_id=user_id
        )
        self.execute(query_set)

        # Delete old_name
        query_set = """
        DELETE FROM public.portfolios
        WHERE portfolio_id={old_id} AND user_id={user_id}
        """.format(
            old_id=old_group['portfolio_id'],
            user_id=user_id
        )
        return self.execute(query_set)

    def delete_group(self, user_id, group_name):
        '''Delete group'''
        # Check for "My Saved Properties"
        query_get = """
        SELECT * FROM public.portfolios
        WHERE portfolio_name='My Saved Properties' and user_id={user_id};
        """.format(user_id=user_id)
        default_group = self.fetchone(query_get)

        query_get = """
        SELECT * FROM public.portfolios
        WHERE portfolio_name='{group_name}' and user_id={user_id};
        """.format(
            user_id=user_id,
            group_name=group_name
        )
        delete_group = self.fetchone(query_get)

        # Exists, move properties and delete requested group
        if default_group:
            query_set = """
            UPDATE public.properties
            SET portfolio_id={new_id}
            WHERE portfolio_id={old_id} AND user_id={user_id}
            """.format(
                new_id=default_group['portfolio_id'],
                old_id=delete_group['portfolio_id'],
                user_id=user_id
            )
            self.execute(query_set)

            query_set = """
            DELETE FROM public.portfolios
            WHERE portfolio_name='{old_name}' AND user_id={user_id}
            """.format(
                old_name=group_name,
                user_id=user_id
            )
            return self.execute(query_set)

        # Create default group first,
        # then move properties and delete requested group
        query_set = """
        INSERT INTO public.portfolios
        (user_id, portfolio_name, portfolio_type)
        VALUES ({user_id}, 'My Saved Properties', 'default')
        """.format(user_id=user_id)
        self.execute(query_set)

        query_get = """
        SELECT * FROM public.portfolios
        WHERE portfolio_name='My Saved Properties' and user_id={user_id};
        """.format(user_id=user_id)
        default_group = self.fetchone(query_get)

        query_set = """
        UPDATE public.properties
        SET portfolio_id={new_id}
        WHERE portfolio_id={old_id} AND user_id={user_id}
        """.format(
            new_id=default_group['portfolio_id'],
            old_id=delete_group['portfolio_id'],
            user_id=user_id
        )
        self.execute(query_set)

        query_set = """
        DELETE FROM public.portfolios
        WHERE portfolio_name='{old_name}' AND user_id={user_id}
        """.format(
            old_name=group_name,
            user_id=user_id
        )
        return self.execute(query_set)

    def get_groups(self, user_id):
        '''Get group by user_id'''
        query_get = """
        SELECT *
        FROM public.portfolios
        WHERE user_id={user_id}
        ORDER BY create_dt DESC;
        """.format(user_id=user_id)
        return self.fetch(query_get)

    def get_group_by_id(self, user_id, portfolio_id):
        '''Get group by user_id and portfolio_id'''
        query_get = """
        SELECT *
        FROM public.portfolios
        WHERE user_id={user_id} AND portfolio_id={portfolio_id};
        """.format(user_id=user_id, portfolio_id=portfolio_id)
        return self.fetchone(query_get)

    def get_group_by_property_id(self, user_id, property_id):
        '''Get group by property_id'''
        query_get = """
        SELECT g.portfolio_name, g.portfolio_id
        FROM public.properties p
        LEFT JOIN public.portfolios g
        ON p.portfolio_id = g.portfolio_id
        WHERE p.user_id={user_id} AND p.property_id={property_id};
        """.format(user_id=user_id, property_id=property_id)
        return self.fetchone(query_get)

    def get_property_group(self, user_id, portfolio_name):
        '''Get property group'''
        query_get = """
        SELECT portfolio_id, portfolio_name
        FROM public.portfolios
        WHERE user_id={user_id} AND lower(portfolio_name)=lower('{portfolio_name}');
        """.format(user_id=user_id, portfolio_name=portfolio_name)
        result = self.fetchone(query_get)
        return result

    def get_properties_in_group(self, user_id, portfolio_id):
        '''Get properties in group'''
        query_get = """
        SELECT *
        FROM public.properties
        WHERE user_id={user_id} AND portfolio_id='{portfolio_id}';
        """.format(user_id=user_id, portfolio_id=portfolio_id)
        result = self.fetch(query_get)
        return result

    def get_popular_properties(self):
        '''Get popular properties'''
        query_get = """
        SELECT property_name, zpid
        FROM properties
        WHERE update_dt > (CURRENT_DATE - INTERVAL '14 days')
        GROUP BY property_name, zpid
        ORDER BY count(*) desc
        limit 3;
        """
        result = self.fetch(query_get)
        return result

    def get_properties_by_user_id(self, user_id=None):
        '''Get properties by user_id'''
        query_get = """
        SELECT *
        FROM public.properties
        WHERE user_id={user_id};
        """.format(user_id=user_id)
        results = self.fetch(query_get)
        properties = []
        result_len = len(results)
        if result_len:
            for result in results:
                address_list = result['property_name'].split('_')
                pretty_address = [a.replace("-", " ") for a in address_list]
                pretty_address = "{}, {}, {}".format(pretty_address[0], \
                pretty_address[1], pretty_address[2])

                if result['images']:
                    images = pickle.loads(str(result['images']))
                else:
                    images = None

                properties.append({
                    'property_id': result['property_id'],
                    'address': result['property_name'],
                    'portfolio_id': result['portfolio_id'],
                    'street_address': result['street_address'],
                    'zip_code': result['zip_code'],
                    'pretty_address': pretty_address,
                    'zillow': {
                        'zpid': result['zpid']
                    },
                    'housecanary': {},
                    'hard': {
                        'latitude': result['latitude'],
                        'longitude': result['longitude'],
                        'valuation': result['valuation'],
                        'purchase_price': result['purchase_price'],
                        'rent': result['rent']
                    },
                    'soft': {
                        'images': images,
                        'finished_sqft': result['finished_sqft'],
                        'bedrooms': result['bedrooms'],
                        'bathrooms': result['bathrooms']
                    },
                    'mortgage': {
                        'down_payment_dollar': result['down_payment_dollar'],
                        'down_payment_percent': result['down_payment_percent'],
                        'rate': result['mortgage_rate'],
                        'term': result['mortgage_term'],
                        'points': result['mortgage_points']
                    },
                    'cost': {
                        'property_taxes': result['property_taxes'],
                        'property_insurance': result['property_insurance'],
                        'renovation_budget': result['renovation_budget'],
                        'hoa_misc': result['hoa_misc'],
                        'closing_costs_dollar': result['closing_costs_dollar'],
                        'closing_costs_percent': result\
                            ['closing_costs_percent'],
                        'property_management_dollar': result\
                            ['property_management_dollar'],
                        'property_management_percent': result\
                            ['property_management_percent'],
                        'vacancy_rate_dollar': result['vacancy_rate_dollar'],
                        'vacancy_rate_percent': result['vacancy_rate_percent'],
                        'capex_dollar': result['capex_dollar'],
                        'capex_percent': result['capex_percent']
                    },
                    'calc': {},
                    'refresh': '<i id="refresh" \
                    class="fa fa-refresh kv-icon kv-icon-secondary"></i>'
                })
        return properties

    def get_saved_property_count(self, user_id):
        '''Save property count'''
        query_get = """
        SELECT count(*) as num
        FROM public.properties
        WHERE user_id={user_id};
        """.format(user_id=user_id)
        result = self.fetchone(query_get)
        return result

    def create_property_group(self, user_id, portfolio_name):
        '''create_property_group'''
        query_set = """
        INSERT INTO public.portfolios
        (user_id, portfolio_name, portfolio_type)
        VALUES ({user_id}, '{portfolio_name}', 'default')
        """.format(
            user_id=user_id,
            portfolio_name=portfolio_name
        )
        self.execute(query_set)
        return self.get_property_group(user_id, portfolio_name)

    def get_change_log(self):
        '''get_change_log'''
        query_get = """
        SELECT change_type, change_description, to_char(create_dt, 'Mon DD') as create_dt_formatted
        FROM public.change_log
        ORDER BY create_dt DESC;
        """
        result = self.fetch(query_get)
        return result

    # pylint: disable=R0914
    def save_property_zillow(self,
                             property_name,
                             street_address,
                             deepcomps,
                             propertydetails):
        '''Save property data from zillow'''
        try:
            deepcomps_detail = deepcomps['properties']['principal']
            zpid = deepcomps_detail['zpid']
            state = deepcomps_detail['address']['state']
            zip_code = deepcomps_detail['address']['zipcode']
            latitude = deepcomps_detail['address']['latitude']
            longitude = deepcomps_detail['address']['longitude']
            valuation = deepcomps_detail['zestimate']['amount']['#text']\
            .replace('$', '').replace(',', '')
            purchase_price = valuation


            if deepcomps_detail.get('rentzestimate', 1) == 1:
                rent = 1
            else:
                rent = deepcomps_detail['rentzestimate']['amount']['#text']\
                .replace('$', '').replace(',', '')


            finished_sqft = deepcomps_detail.get('finishedSqFt', None)
            bedrooms = deepcomps_detail.get('bedrooms', None)
            bathrooms = deepcomps_detail.get('bathrooms', None)

            todaydate = datetime.today()
            if todaydate.day > 25:
                todaydate += timedelta(7)
            dtime = todaydate.replace(day=1).date()

            if propertydetails != 0:
                if propertydetails.get('images') is not None:
                    images = psycopg2.Binary(pickle.dumps(\
                        propertydetails.get('images'), -1))
                else:
                    images = "null"
            else:
                images = "null"

            query_set = """
            INSERT INTO public.fct_zillow (
                dt, property_name, street_address, state, zip_code, zpid, latitude,
                longitude, valuation, purchase_price, rent, images, finished_sqft,
                bedrooms, bathrooms
            )
            VALUES (
                '{dt}', '{property_name}', '{street_address}', '{state}', '{zip_code}',
                '{zpid}', '{latitude}', '{longitude}', {valuation}, {purchase_price},
                {rent}, {images}, '{finished_sqft}', '{bedrooms}', '{bathrooms}'
            )
            """.format(
                dt=dtime,
                property_name=property_name,
                street_address=street_address,
                state=state,
                zip_code=zip_code,
                zpid=zpid,
                latitude=latitude,
                longitude=longitude,
                valuation=valuation,
                purchase_price=purchase_price,
                rent=rent,
                images=images,
                finished_sqft=finished_sqft,
                bedrooms=bedrooms,
                bathrooms=bathrooms
            )
            self.execute(query_set)
        except:# pylint: disable=W0702
            return

    def get_property_zillow(self, property_name):
        '''Get property data from zillow'''
        todaydate = datetime.today()
        if todaydate.day > 25:
            todaydate += timedelta(7)
        dtime = todaydate.replace(day=1).date()

        query_get = """
        SELECT *
        FROM public.fct_zillow
        WHERE property_name = '{property_name}' and dt='{dt}';
        """.format(property_name=property_name, dt=dtime)

        return self.fetchone(query_get)

    def save_housecanary_details(self, property_name, housecanary_details):
        '''Save housecanary details data from API'''
        try:
            hc_result = housecanary_details[0]['property/details']['result']\
                ['property']
            hc_assessment = housecanary_details[0]['property/details']\
                ['result']['assessment']

            property_name = property_name
            no_of_buildings = hc_result.get('no_of_buildings', 0)
            attic = hc_result['attic']
            total_bath_count = hc_result.get('total_bath_count', 0) or 0
            full_bath_count = hc_result.get('full_bath_count', None)
            partial_bath_count = hc_result.get('partial_bath_count', None)
            total_number_of_rooms = hc_result.get('total_number_of_rooms', 0)
            heating = hc_result.get('heating', None)
            heating_fuel_type = hc_result.get('heating_fuel_type', None)
            style = hc_result.get('style', None)
            garage_parking_of_cars = hc_result.get('garage_parking_of_cars', 0)
            site_area_acres = hc_result.get('site_area_acres', 0)
            number_of_units = hc_result.get('number_of_units', 0)
            building_area_sq_ft = hc_result.get('building_area_sq_ft', 0)
            water = hc_result.get('water', 0)
            basement = hc_result.get('basement', None)
            air_conditioning = hc_result.get('air_conditioning', None)
            fireplace = hc_result.get('fireplace', None)
            pool = hc_result.get('pool', None)
            no_of_stories = hc_result.get('no_of_stories', None)
            garage_type_parking = hc_result.get('garage_type_parking', None)
            property_type = hc_result.get('property_type', None)
            year_built = hc_result.get('year_built', 0)
            exterior_walls = hc_result.get('exterior_walls', None)
            number_of_bedrooms = hc_result.get('number_of_bedrooms', 0)
            sewer = hc_result.get('sewer', None)
            subdivision = hc_result.get('subdivision', None)
            building_quality_score = hc_result.get('building_quality_score',
                                                   None)
            building_condition_score = hc_result.get('building_condition_score',
                                                     None)

            assessment_year = hc_assessment.get('assessment_year', 0)
            tax_amount = hc_assessment.get('tax_amount', 0)
            total_assessed_value = hc_assessment.get('total_assessed_value', 0)
            tax_year = hc_assessment.get('tax_year', 0)

            todaydate = datetime.today()
            if todaydate.day > 25:
                todaydate += timedelta(7)
            dtime = todaydate.replace(day=1).date()

            query_set = """
            INSERT INTO public.fct_housecanary_details (
                dt, property_name, no_of_buildings, attic, total_number_of_rooms, heating,
                heating_fuel_type, property_type, style, garage_parking_of_cars,
                site_area_acres, number_of_units, building_area_sq_ft, total_bath_count,
                garage_type_parking, basement, year_built, air_conditioning, building_quality_score,
                fireplace, pool, no_of_stories, water, subdivision, exterior_walls, number_of_bedrooms,
                sewer, building_condition_score, full_bath_count, partial_bath_count, assessment_year,
                tax_amount, total_assessed_value, tax_year
            )
            VALUES (
                '{dt}', '{property_name}', {no_of_buildings}, '{attic}', {total_number_of_rooms},
                '{heating}', '{heating_fuel_type}', '{property_type}', '{style}', {garage_parking_of_cars},
                {site_area_acres}, {number_of_units}, {building_area_sq_ft}, {total_bath_count}, '{garage_type_parking}',
                '{basement}', {year_built}, '{air_conditioning}', '{building_quality_score}', '{fireplace}', '{pool}',
                '{no_of_stories}', '{water}', '{subdivision}', '{exterior_walls}', {number_of_bedrooms}, '{sewer}',
                '{building_condition_score}', '{full_bath_count}', '{partial_bath_count}', {assessment_year},
                {tax_amount}, {total_assessed_value}, {tax_year}
            )
            """.format(dt=dtime, property_name=property_name, \
            no_of_buildings=no_of_buildings, attic=attic, \
            total_bath_count=total_bath_count, full_bath_count=full_bath_count,\
            partial_bath_count=partial_bath_count, \
            total_number_of_rooms=total_number_of_rooms, heating=heating, \
            heating_fuel_type=heating_fuel_type, style=style,\
            garage_parking_of_cars=garage_parking_of_cars, \
            site_area_acres=site_area_acres, number_of_units=number_of_units, \
            building_area_sq_ft=building_area_sq_ft, water=water, \
            basement=basement, air_conditioning=air_conditioning,\
            fireplace=fireplace, pool=pool, no_of_stories=no_of_stories,\
            garage_type_parking=garage_type_parking, \
            property_type=property_type, year_built=year_built, \
            exterior_walls=exterior_walls, \
            number_of_bedrooms=number_of_bedrooms, \
            sewer=sewer, subdivision=subdivision,\
            building_quality_score=building_quality_score,\
            building_condition_score=building_condition_score, \
            assessment_year=assessment_year, tax_amount=tax_amount, \
            total_assessed_value=total_assessed_value, tax_year=tax_year)

            self.execute(query_set)
        except:# pylint: disable=W0702
            return

    def get_housecanary_details(self, property_name):
        '''Get housecanary details in PG'''
        todaydate = datetime.today()
        if todaydate.day > 25:
            todaydate += timedelta(7)
        dtime = todaydate.replace(day=1).date()

        query_get = """
        SELECT *
        FROM public.fct_housecanary_details
        WHERE property_name = '{property_name}' and dt='{dt}';
        """.format(property_name=property_name, dt=dtime)

        result = self.fetchone(query_get)
        return result

    def save_housecanary_census(self, property_name, housecanary_census):
        '''Save housecanary census'''
        try:
            hc_result = housecanary_census[0]['property/census']['result']

            msa_name = hc_result.get('msa_name', None)
            tribal_land = hc_result.get('tribal_land', None)
            block = hc_result.get('block', None)
            block_group = hc_result.get('block_group', None)
            tract = hc_result.get('tract', None)
            county_name = hc_result.get('county_name', None)
            fips = hc_result.get('fips', None)
            msa = hc_result.get('msa', None)

            query_set = """
            INSERT INTO public.fct_housecanary_census (
                property_name, msa_name, tribal_land, block, block_group,
                tract, county_name, fips, msa
            )
            VALUES (
                '{property_name}', '{msa_name}', '{tribal_land}', '{block}',
                '{block_group}', '{tract}', '{county_name}', '{fips}', '{msa}'
            )
            """.format(property_name=property_name,
                       msa_name=msa_name,
                       tribal_land=tribal_land,
                       block=block,
                       block_group=block_group,
                       tract=tract,
                       county_name=county_name,
                       fips=fips,
                       msa=msa)

            self.execute(query_set)
        except:# pylint: disable=W0702
            return

    def get_housecanary_census(self, property_name):
        '''Get housecanary census'''
        query_get = """
        SELECT *
        FROM public.fct_housecanary_census
        WHERE property_name = '{property_name}';
        """.format(property_name=property_name)

        result = self.fetchone(query_get)
        return result

    def save_housecanary_sales_history(self, property_name,
                                       housecanary_sales_history):
        '''Save housecanary sales'''
        try:
            hc_result = housecanary_sales_history[0]['property/sales_history']\
                ['result']
            todaydate = datetime.today()
            if todaydate.day > 25:
                todaydate += timedelta(7)
            dtime = todaydate.replace(day=1).date()

            query_set = ""
            for item in hc_result:
                record_date = item.get('record_date')
                record_doc = item.get('record_doc')
                fips = item.get('fips', None)
                event_type = item.get('event_type', None)
                grantee_1 = item.get('grantee_1', None)
                grantee_1_forenames = item.get('grantee_1_forenames', None)
                grantee_2 = item.get('grantee_2', None)
                grantee_2_forenames = item.get('grantee_2_forenames', None)

                record_page = item.get('record_page', 0)
                if record_page is None:
                    record_page = 0

                amount = item.get('amount', 0)
                if amount is None:
                    amount = 0

                grantor_1 = item.get('grantor_1', None)
                grantor_1_forenames = item.get('grantor_1_forenames', None)
                grantor_2 = item.get('grantor_2', None)
                grantor_2_forenames = item.get('grantor_2_forenames', None)
                apn = item.get('apn', None)

                record_book = item.get('record_book', 0)
                if record_book is None:
                    record_book = 0

                query_set += """
                    INSERT INTO public.fct_housecanary_sales_history (
                    dt, property_name, record_date, record_doc,
                    fips, event_type, grantee_1, grantee_1_forenames, grantee_2,
                    grantee_2_forenames, record_page, amount, grantor_1, grantor_1_forenames,
                    grantor_2, grantor_2_forenames, apn, record_book
                    )
                    VALUES (
                        '{dt}', '{property_name}', '{record_date}', '{record_doc}', '{fips}',
                        '{event_type}', '{grantee_1}', '{grantee_1_forenames}', '{grantee_2}',
                        '{grantee_2_forenames}', {record_page}, '{amount}', '{grantor_1}',
                        '{grantor_1_forenames}', '{grantor_2}', '{grantor_2_forenames}',
                        '{apn}', '{record_book}'
                    )
                    """.format(dt=dtime, property_name=property_name,
                               record_date=record_date, record_doc=record_doc,
                               fips=fips, event_type=event_type,
                               grantee_1=grantee_1,
                               grantee_1_forenames=grantee_1_forenames,
                               grantee_2=grantee_2,
                               grantee_2_forenames=grantee_2_forenames,
                               record_page=record_page, amount=amount,
                               grantor_1=grantor_1,
                               grantor_1_forenames=grantor_1_forenames,
                               grantor_2=grantor_2,
                               grantor_2_forenames=grantor_2_forenames,
                               apn=apn, record_book=record_book)+ " ; "

            #print(query_set)
            #sys.stdout.flush()
            self.execute(query_set)
        except:# pylint: disable=W0702
            return

    # Mavu - 20170517
    def get_housecanary_sales_history(self, property_name):
        """Get housecanary sale history data"""
        query_get = """
        SELECT *
        FROM public.fct_housecanary_sales_history
        WHERE property_name = '{property_name}' order by record_date desc, record_doc desc;
        """.format(property_name=property_name)
        return self.fetch(query_get)

    def save_housecanary_zip_details(self, property_name,
                                     housecanary_zip_details):
        """Save housecanary zipe details data"""
        try:
            multi_family = housecanary_zip_details[0]\
                ['property/zip_details']['result']['multi_family']
            single_family = housecanary_zip_details[0]\
                ['property/zip_details']['result']['single_family']

            mf_inventory_total = multi_family.get('inventory_total', 0)
            mf_price_median = multi_family.get('price_median', 0)
            mf_estimated_sales_total = multi_family.get(\
                'estimated_sales_total', 0)
            mf_market_action_median = multi_family.get(\
                'market_action_median', 0)
            mf_months_of_inventory_median = multi_family.get(\
                'months_of_inventory_median', 0)
            mf_days_on_market_median = multi_family.get(\
                'days_on_market_median', 0)

            sf_inventory_total = single_family.get('inventory_total', 0)
            sf_price_median = single_family.get('price_median', 0)
            sf_estimated_sales_total = single_family.get(\
                'estimated_sales_total', 0)
            sf_market_action_median = single_family.get(\
                'market_action_median', 0)
            sf_months_of_inventory_median = single_family.get(\
                'months_of_inventory_median', 0)
            sf_days_on_market_median = single_family.get(\
                'days_on_market_median', 0)

            todaydate = datetime.today()
            if todaydate.day > 25:
                todaydate += timedelta(7)
            dtime = todaydate.replace(day=1).date()

            query_set = """
            INSERT INTO public.fct_housecanary_zip_details (
                dt, property_name, mf_inventory_total, mf_price_median, mf_estimated_sales_total,
                mf_market_action_median, mf_months_of_inventory_median, mf_days_on_market_median,
                sf_inventory_total, sf_price_median, sf_estimated_sales_total, sf_market_action_median,
                sf_months_of_inventory_median, sf_days_on_market_median
            )
            VALUES (
                '{dt}', '{property_name}', {mf_inventory_total}, {mf_price_median}, {mf_estimated_sales_total},
                {mf_market_action_median}, {mf_months_of_inventory_median}, {mf_days_on_market_median},
                {sf_inventory_total}, {sf_price_median}, {sf_estimated_sales_total}, {sf_market_action_median},
                {sf_months_of_inventory_median}, {sf_days_on_market_median}
            )
            """.format(dt=dtime, property_name=property_name,
                       mf_inventory_total=mf_inventory_total,
                       mf_price_median=mf_price_median,
                       mf_estimated_sales_total=mf_estimated_sales_total,
                       mf_market_action_median=mf_market_action_median, \
           mf_months_of_inventory_median=mf_months_of_inventory_median,
                       mf_days_on_market_median=mf_days_on_market_median,
                       sf_inventory_total=sf_inventory_total,
                       sf_price_median=sf_price_median,
                       sf_estimated_sales_total=sf_estimated_sales_total,
                       sf_market_action_median=sf_market_action_median, \
           sf_months_of_inventory_median=sf_months_of_inventory_median,
                       sf_days_on_market_median=sf_days_on_market_median)

            self.execute(query_set)
        except:# pylint: disable=W0702
            return

    def get_housecanary_zip_details(self, property_name):
        """Get housecanary zipe details data"""
        todaydate = datetime.today()
        if todaydate.day > 25:
            todaydate += timedelta(7)
        dtime = todaydate.replace(day=1).date()

        query_get = """
        SELECT *
        FROM public.fct_housecanary_zip_details
        WHERE property_name = '{property_name}' and dt='{dt}';
        """.format(property_name=property_name, dt=dtime)

        result = self.fetchone(query_get)
        return result

    #save data into fct_housecanary_geocode - mavu
    def save_housecanary_geocode(self, data):
        """Get housecanary geocode"""
        try:
            hc_result = data[0]['address_info']
            address_full = hc_result.get('address_full', None)
            slug = hc_result.get('slug', None)
            address = hc_result.get('address', None)
            unit = hc_result.get('unit', None)
            city = hc_result.get('city', None)
            state = hc_result.get('state', None)
            zipcode = hc_result.get('zipcode', None)
            zipcode_plus4 = hc_result.get('zipcode_plus4', None)
            block_id = hc_result.get('block_id', None)
            county_fips = hc_result.get('county_fips', None)
            msa = hc_result.get('msa', None)
            metdiv = hc_result.get('metdiv', None)
            geo_precision = hc_result.get('geo_precision', None)
            lat = hc_result.get('lat', None)
            lng = hc_result.get('lng', None)

            query_set = """
            INSERT INTO public.fct_housecanary_geocode (
                address_full, slug, address, unit, city,
                state, zipcode, zipcode_plus4, block_id, county_fips,
                msa, metdiv, geo_precision, lat, lng
            )
            VALUES (
                '{address_full}', '{slug}', '{address}', '{unit}', '{city}',
                '{state}', '{zipcode}', '{zipcode_plus4}', '{block_id}', '{county_fips}',
                '{msa}', '{metdiv}', '{geo_precision}', '{lat}', '{lng}'
            )
            """.format(address_full=address_full, slug=slug, address=address,\
                unit=unit, city=city, state=state, zipcode=zipcode,\
                zipcode_plus4=zipcode_plus4, block_id=block_id,\
                county_fips=county_fips, msa=msa, metdiv=metdiv,\
                geo_precision=geo_precision, lat=lat, lng=lng)

            self.execute(query_set)
        except:# pylint: disable=W0702
            return

    # Mavu - 20170517
    def get_housecanary_geocode(self, zip_code):
        """Get housecanary school data"""
        query_get = """
        SELECT *
        FROM public.fct_housecanary_geocode
        WHERE zipcode = '{zip_code}';
        """.format(zip_code=zip_code)

        return self.fetchone(query_get)

    #save data into fct_housecanary_school - mavu
    def save_housecanary_school(self, data, property_name):
        """Save housecanary school"""
        try:
            hc_result = data[0]['property/school']['result']['school']

            elementary_city = hc_result['elementary'][0].get('city', None)
            el_verified_school_boundaries = hc_result['elementary'][0]\
                .get('verified_school_boundaries', False)
            elementary_distance_miles = hc_result['elementary'][0]\
                .get('distance_miles', None)
            elementary_name = hc_result['elementary'][0].get('name', None)
            elementary_zipcode = hc_result['elementary'][0].get('zipcode', None)
            elementary_phone = hc_result['elementary'][0].get('phone', None)
            elementary_state = hc_result['elementary'][0].get('state', None)
            elementary_score = hc_result['elementary'][0].get('score', '0')
            elementary_score = 0 if elementary_score is None else elementary_score
            elementary_education_level = 'elementary'
            elementary_address = hc_result['elementary'][0].get('address', None)
            elementary_assessment_year = hc_result['elementary'][0]\
                .get('assessment_year', None)

            middle_city = hc_result['middle'][0].get('city', None)
            middle_verified_school = hc_result['middle'][0]\
                .get('verified_school_boundaries', False)
            middle_distance_miles = hc_result['middle'][0]\
                .get('distance_miles', None)
            middle_name = hc_result['middle'][0].get('name', None)
            middle_zipcode = hc_result['middle'][0].get('zipcode', None)
            middle_phone = hc_result['middle'][0].get('phone', None)
            middle_state = hc_result['middle'][0].get('state', None)
            middle_score = hc_result['middle'][0].get('score', '0')
            middle_score = 0 if middle_score is None else middle_score
            middle_education_level = 'middle'
            middle_address = hc_result['middle'][0].get('address', None)
            middle_assessment_year = hc_result['middle'][0]\
                .get('assessment_year', None)

            high_city = hc_result['high'][0].get('city', None)
            high_verified_school_boundaries = hc_result['high'][0]\
                .get('verified_school_boundaries', False)
            high_distance_miles = hc_result['high'][0]\
                .get('distance_miles', None)
            high_name = hc_result['high'][0].get('name', None)
            high_zipcode = hc_result['high'][0].get('zipcode', None)
            high_phone = hc_result['high'][0].get('phone', None)
            high_state = hc_result['high'][0].get('state', None)
            high_score = hc_result['high'][0].get('score', '0')
            high_score = 0 if high_score is None else high_score
            high_education_level = 'high'
            high_address = hc_result['high'][0].get('address', None)
            high_assessment_year = hc_result['high'][0]\
                .get('assessment_year', None)

            query_set = """
            INSERT INTO public.fct_housecanary_school (
                elementary_city, elementary_verified_school_boundaries, elementary_distance_miles, elementary_name,
                elementary_zipcode, elementary_phone, elementary_state, elementary_score, elementary_education_level,
                elementary_address, elementary_assessment_year,
                middle_city, middle_verified_school_boundaries, middle_distance_miles, middle_name,
                middle_zipcode, middle_phone, middle_state, middle_score, middle_education_level,
                middle_address, middle_assessment_year,
                high_city, high_verified_school_boundaries, high_distance_miles, high_name,
                high_zipcode, high_phone, high_state, high_score, high_education_level,
                high_address, high_assessment_year, property_name
            )
            VALUES (
                '{elementary_city}', '{elementary_verified_school_boundaries}', '{elementary_distance_miles}', '{elementary_name}',
                '{elementary_zipcode}', '{elementary_phone}', '{elementary_state}', '{elementary_score}', '{elementary_education_level}',
                '{elementary_address}', '{elementary_assessment_year}',
                '{middle_city}', '{middle_verified_school_boundaries}', '{middle_distance_miles}', '{middle_name}',
                '{middle_zipcode}', '{middle_phone}', '{middle_state}', '{middle_score}', '{middle_education_level}',
                '{middle_address}', '{middle_assessment_year}',
                '{high_city}', '{high_verified_school_boundaries}', '{high_distance_miles}', '{high_name}',
                '{high_zipcode}', '{high_phone}', '{high_state}', '{high_score}', '{high_education_level}',
                '{high_address}', '{high_assessment_year}', '{property_name}'
            )
            """.format(elementary_city=elementary_city,\
        elementary_verified_school_boundaries=el_verified_school_boundaries,\
        elementary_distance_miles=elementary_distance_miles,\
        elementary_name=elementary_name, elementary_zipcode=elementary_zipcode,\
        elementary_phone=elementary_phone, elementary_state=elementary_state,\
        elementary_score=elementary_score,\
        elementary_education_level=elementary_education_level,\
        elementary_address=elementary_address,\
        elementary_assessment_year=elementary_assessment_year, \
        middle_city=middle_city, \
        middle_verified_school_boundaries=middle_verified_school,\
        middle_distance_miles=middle_distance_miles, middle_name=middle_name,\
        middle_zipcode=middle_zipcode, middle_phone=middle_phone,\
        middle_state=middle_state, middle_score=middle_score,\
        middle_education_level=middle_education_level, \
        middle_address=middle_address,\
        middle_assessment_year=middle_assessment_year, high_city=high_city,\
        high_verified_school_boundaries=high_verified_school_boundaries,\
        high_distance_miles=high_distance_miles, high_name=high_name,\
        high_zipcode=high_zipcode, high_phone=high_phone, \
        high_state=high_state, high_score=high_score, \
        high_education_level=high_education_level, high_address=high_address, \
        high_assessment_year=high_assessment_year, property_name=property_name)

            self.execute(query_set)
        # except IOError as (errno, strerror):
        #     print "I/O error({0}): {1}".format(errno, strerror)
        except:# pylint: disable=W0702
            return
            # print "Unexpected error:", sys.exc_info()[0]
            # raise

    # Mavu - 20170517
    def get_housecanary_school(self, property_name):
        """Get housecanary school data"""
        query_get = """
        SELECT *
        FROM public.fct_housecanary_school
        WHERE property_name = '{property_name}';
        """.format(property_name=property_name)

        return self.fetchone(query_get)

    #Phuc Do 20170609 for Unittest
    def delete_user(self, email):
        """delete user test"""
        query_set = """
        DELETE FROM public.user_details WHERE email = '{email}';
        """.format(email=email)
        self.execute(query_set)

    # Functionalities for remove data in unittest
    # Mavu - 20170608
    # ============================
    def remove_housecanary_details(self, prope):
        '''Delete a housecanary details'''
        query_set = """
        DELETE FROM public.fct_housecanary_details
        WHERE property_name='{property_name}'
        """.format(property_name=prope)
        return self.execute(query_set)

    def remove_housecanary_census(self, prope):
        '''Delete a housecanary census'''
        query_set = """
        DELETE FROM public.fct_housecanary_census
        WHERE property_name='{property_name}'
        """.format(property_name=prope)
        return self.execute(query_set)

    def remove_housecanary_zip_details(self, prope):
        '''Delete a housecanary zip details'''
        query_set = """
        DELETE FROM public.fct_housecanary_zip_details
        WHERE property_name='{property_name}'
        """.format(property_name=prope)
        return self.execute(query_set)

    def remove_housecanary_sales_history(self, prope):
        '''Delete a housecanary sales history'''
        query_set = """
        DELETE FROM public.fct_housecanary_sales_history
        WHERE property_name='{property_name}'
        """.format(property_name=prope)
        return self.execute(query_set)

    def remove_housecanary_school(self, prope):
        '''Delete a housecanary school'''
        query_set = """
        DELETE FROM public.fct_housecanary_school
        WHERE elementary_zipcode = '{zip_code}';
        """.format(zip_code=prope)
        return self.execute(query_set)

    def remove_housecanary_geocode(self, prope):
        '''Delete a housecanary geocode'''
        query_set = """
        DELETE FROM public.fct_housecanary_geocode
        WHERE zipcode = '{zip_code}';
        """.format(zip_code=prope)
        return self.execute(query_set)

    def remove_property_zillow(self, prope):
        '''Delete a housecanary geocode'''
        query_set = """
        DELETE FROM public.fct_zillow
        WHERE property_name = '{property_name}';
        """.format(property_name=prope)

        return self.execute(query_set)
