"""
Test Addresses:
[{"zipcode": "89128", "address": "7904 Verde Springs Dr"},
{"zipcode": "33473", "address": "8691 Flowersong Cv"},
{"zipcode": "78255", "address": "22905 Cielo Vis"},
{"zipcode": "03076", "address": "16 Thomas Ave"},
{"zipcode": "22314", "address": "1111 Oronoco St Unit 441"},
{"zipcode": "55407", "address": "2718 16th Ave S"},
{"zipcode": "95023", "address": "590 Foothill Rd"},
{"zipcode": "81211", "address": "30737 County Road 356-6"},
{"zipcode": "60606", "address": "333 N Canal St Apt 2901"},
{"zipcode": "48162", "address": "3466 Erie Shore Dr"}]
"""

import os
import requests
from src.py.pg import PGWriter
PG = PGWriter()

#test_api_key = "test_IM833EYJ7XGC4ZOGFXWU"
#test_api_secret = "VcQm0uRgVlMmcX2jGa7Lc1T0ygqFsXt9"
HOUSECANARY_KEY = os.environ.get('HOUSECANARY_KEY')
HOUSECANARY_SECRET = os.environ.get('HOUSECANARY_SECRET')
URL_BASE = "https://api.housecanary.com/v2/"

# Makes REST Request to HouseCanary
def do_hc_request(url, params=None):
    '''Request to HouseCanary API'''
    try:
        response = requests.get(url, params=params,
                                auth=(HOUSECANARY_KEY, HOUSECANARY_SECRET))
        return response.json()
    except:
        return None

# Mavu - 20170517
def get_housecanary_data(property_name, params):
    """Get housecanary data"""
    hc_data = {
        'detail' : None,
        'census' : None,
        'sales_history' : None,
        'zip_details' : None,
        'school' : None,
        'geocode' : None
    }

    hc_data['detail'] = PG.get_housecanary_details(property_name)
    if hc_data['detail'] is None:
        hc_details_result = do_hc_request(URL_BASE + 'property/details', params)
        PG.save_housecanary_details(property_name, hc_details_result)
        hc_data['detail'] = PG.get_housecanary_details(property_name)

    hc_data['census'] = PG.get_housecanary_census(property_name)
    if hc_data['census'] is None:
        hc_census_result = do_hc_request(URL_BASE + 'property/census', params)
        PG.save_housecanary_census(property_name, hc_census_result)
        hc_data['census'] = PG.get_housecanary_census(property_name)

    hc_data['zip_details'] = PG.get_housecanary_zip_details(property_name)
    if hc_data['zip_details'] is None:
        hc_zip_details_result = do_hc_request(URL_BASE + 'property/details',
                                              params)
        PG.save_housecanary_zip_details(property_name, hc_zip_details_result)
        hc_data['zip_details'] = PG.get_housecanary_zip_details(property_name)

    hc_data['sales_history'] = PG.get_housecanary_sales_history(property_name)
    if len(hc_data['sales_history']) == 0:
        hc_sales_history_result = do_hc_request(
            URL_BASE + 'property/sales_history',
            params)
        PG.save_housecanary_sales_history(property_name,
                                          hc_sales_history_result)
        hc_data['sales_history'] = PG.get_housecanary_sales_history(
            property_name)

    hc_data['school'] = PG.get_housecanary_school(property_name)
    if hc_data['school'] is None:
        hc_school_result = do_hc_request(URL_BASE + 'property/school', params)
        PG.save_housecanary_school(hc_school_result, property_name)
        hc_data['school'] = PG.get_housecanary_school(property_name)

    hc_data['geocode'] = PG.get_housecanary_geocode(params['zipcode'])
    if hc_data['geocode'] is None:
        hc_geocode_result = do_hc_request(URL_BASE + 'property/geocode', params)
        PG.save_housecanary_geocode(hc_geocode_result)
        hc_data['geocode'] = PG.get_housecanary_geocode(params['zipcode'])

    return hc_data
