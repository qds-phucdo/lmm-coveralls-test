"""Process for get property"""
import pickle
# pylint: disable=W0403
from zillow import (get_zillow_data)
from housecanary import (get_housecanary_data)
from src.py.pg import PGWriter

PG = PGWriter()

# pylint: disable=R0914,R0915
def get_property_info(session, address, zpid=0, save_history=True):
    """Get property"""
    # Setup key fields for querying
    address_list = address.split('_')
    pretty_address = [a.replace("-", " ") for a in address_list]
    get_pretty_address = address
    zip_code = 0
    user_data = None
    portfolio_id = None
    # Default values
    hard_details = {
        'latitude': None,
        'longitude': None,
        'valuation': 1,
        'purchase_price': 1,
        'rent': 1
    }
    soft_details = {
        'images': None,
        'finished_sqft': None,
        'bedrooms': None,
        'bathrooms': None
    }

    if len(address_list) > 2:
        zip_code = address_list[2]
        get_pretty_address = "{}, {}, {}".format(pretty_address[0],
                                                 pretty_address[1],
                                                 pretty_address[2])

    # Get Zillow data
    zillow_data = get_zillow_data(address, pretty_address[0], zip_code, zpid)
    if zpid in [0, '0'] and zillow_data['zpid']:
        zpid = zillow_data['zpid']

    # Insert history
    if save_history and address != "compare":
        action_text = "|".join([address, zpid])
        PG.log_action(session['profile']['user_id'],
                      'property view',
                      action_text)

    # Get HouseCanary Info
    params = {'address': pretty_address[0], 'zipcode': zip_code}
    
    hc_data = get_housecanary_data(address, params)

    # Get saved property info for registered users
    if session['profile'].get('user_id', 0) > 0:
        user_data = PG.get_property(address, session['profile']['user_id'])

    # Logic to select the best data possible
    if zillow_data['property_zillow']:
        soft_details['bathrooms'] = zillow_data['property_zillow']['bathrooms']
        soft_details['bedrooms'] = zillow_data['property_zillow']['bedrooms']
        soft_details['finished_sqft'] = zillow_data['property_zillow']\
            ['finished_sqft']
        hard_details['latitude'] = zillow_data['property_zillow']['latitude']
        hard_details['longitude'] = zillow_data['property_zillow']['longitude']
        hard_details['valuation'] = zillow_data['property_zillow']['valuation']
        hard_details['purchase_price'] = zillow_data['property_zillow']\
            ['purchase_price']
        hard_details['rent'] = zillow_data['property_zillow']['rent']
        if zillow_data['property_zillow']['images']:
            soft_details['images'] = pickle.loads(str(zillow_data\
                ['property_zillow']['images']))
            zillow_data['property_zillow']['images'] = soft_details['images']

    if hc_data['detail']:
        soft_details['bathrooms'] = hc_data['detail']\
            .get('total_bath_count', None)
        soft_details['bedrooms'] = hc_data['detail']\
            .get('number_of_bedrooms', None)
        soft_details['finished_sqft'] = hc_data['detail']\
            .get('building_area_sq_ft', None)

    if hc_data['geocode']:
        hard_details['latitude'] = hc_data['geocode'].get('lat', None)
        hard_details['longitude'] = hc_data['geocode'].get('lng', None)

    if session.get(address, None) and session[address]:
        hard_details['valuation'] = session[address]['hard']['valuation']
        hard_details['purchase_price'] = session[address]['hard']\
            ['purchase_price']
        hard_details['rent'] = session[address]['hard']['rent']

    if user_data:
        portfolio_id = user_data['portfolio_id']
        hard_details['latitude'] = user_data['hard']['latitude']
        hard_details['longitude'] = user_data['hard']['longitude']
        hard_details['valuation'] = user_data['hard']['valuation']
        hard_details['purchase_price'] = user_data['hard']['purchase_price']
        hard_details['rent'] = user_data['hard']['rent']

    # Build dict based on priority: PG, Redis, HouseCanary, Zillow, Hard Coded
    at_property = {
        'address': address,
        'portfolio_id': portfolio_id,
        'street_address': address_list[0],
        'zip_code': zip_code,
        'pretty_address': get_pretty_address,
        'zillow': zillow_data['property_zillow'] \
            if zillow_data['property_zillow'] else None,
        'zpid': zpid,
        'housecanary': hc_data,
        'user_data': user_data,
        'tax_amount': hc_data['detail'].get('tax_amount', 0) \
            if hc_data['detail'] else 0,
        'hard': hard_details,
        'soft': soft_details,
        'mortgage': {},
        'cost': {},
        'calc': {},
        'refresh': 1 if user_data != None else '',
        # set attribute is_manual = 1 for property not found on zillow
        'is_manual': 0 if zpid not in [0, '0'] or hc_data['detail'] else 1,
        'property_id': user_data['property_id'] if user_data else None,
        'sales_history': hc_data['sales_history'] if len(hc_data['sales_history']) != 0 else []
    }

    return at_property

def clean_result(value):
    """Replace special chars"""
    return float(value.replace('$', '').replace(',', ''))
