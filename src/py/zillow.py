"""Get data from zillow API"""
import urllib
import urllib3
import xmltodict
import sys
import os
from os import path
sys.path.append(os.getcwd())
from src.py.helper import (clean_result)
from src.py.pg import PGWriter
PG = PGWriter()

#https://www.zillow.com/howto/api/APIOverview.htm
ZWSID = 'X1-ZWz1fbyj7cmwaz_agge7' # Zillow API Key
DEEPCOMPS_URL = "https://www.zillow.com/webservice/GetDeepComps.htm?"\
    "rentzestimate=true&zws-id={zwsid}&count=5".format(zwsid=ZWSID)
PROPERTYDETAILS_URL = "http://www.zillow.com/webservice/"\
    "GetUpdatedPropertyDetails.htm?zws-id={zwsid}".format(zwsid=ZWSID)

# return zpid or list
def ajax_search_zpid(address, zip_code):
    """Property search zpid by address and zip_code"""
    zpid = 0
    zillow_results = get_search_results(address, zip_code)
    if zillow_results != 0:
        # If got list zpid
        if isinstance(zillow_results['result'], list):
            zpid = zillow_results['result']
        else:
            zpid = zillow_results['result']['zpid']

    return zpid

# Return search results
def get_search_results(street_number, postal_code):
    """Get search result from API"""
    street_number = urllib.quote(street_number)
    search_url = "https://www.zillow.com/webservice/GetSearchResults.htm?"\
                 "zws-id={zwsid}&address={num}&citystatezip={citystatezip}"\
                 .format(zwsid=ZWSID,
                         num=street_number,
                         citystatezip=postal_code)

    # Get SearchResults data
    head = "SearchResults:searchresults"
    searchresults = do_zillow_request(search_url, head)
    if searchresults:
        searchresults = searchresults['results']
        return searchresults
    return 0

# Makes REST Request to Zillow
def do_zillow_request(url, head):
    """Make request for API"""
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    if resp.status == 200:
        try:
            dict_full = xmltodict.parse(resp.data)
            if dict_full[head]['message']['code'] != '0':
                return None
        except:# pylint: disable=W0702
            print "[URL]"
            print url
            print "[HEAD]"
            print head
            print "[RESULT]"
            print resp
            return None

        return dict_full[head]['response']
    return None

# do_zillow_deepcomp
def do_zillow_deepcomp(zpid):
    """Zillow Deepcomp API"""
    deepcomps_url = DEEPCOMPS_URL+'&zpid={zpid}'.format(zpid=zpid)
    deepcomp_details = do_zillow_request(deepcomps_url, "Comps:comps")

    if deepcomp_details:
        rent = 1
        deepcomp_results = deepcomp_details['properties']['principal']
        if deepcomp_results.get('rentzestimate', 1) != 1:
            rent = clean_result(deepcomp_results['rentzestimate']\
                ['amount']['#text'])

        hard_details = {
            'latitude': deepcomp_results['address']['latitude'],
            'longitude': deepcomp_results['address']['longitude'],
            'valuation': clean_result(deepcomp_results['zestimate']\
                ['amount']['#text']),
            'purchase_price': clean_result(deepcomp_results['zestimate']\
                ['amount']['#text']),
            'rent': rent,
            'properties': deepcomp_details['properties']
        }

        return hard_details
    return None

# do_zillow_property_details
def do_zillow_property_details(zpid):
    """Zillow Get Property API"""
    propertydetails_url = PROPERTYDETAILS_URL+'&zpid={zpid}'.format(zpid=zpid)
    property_details = do_zillow_request(propertydetails_url, \
        "UpdatedPropertyDetails:updatedPropertyDetails")

    if property_details:
        soft_details = {
            'images': property_details.get('images', None),
            'finished_sqft': property_details['editedFacts'].get('finishedSqFt',
                                                                 None),
            'bedrooms': property_details['editedFacts'].get('bedrooms', None),
            'bathrooms': property_details['editedFacts'].get('bathrooms', None)
        }

        return soft_details
    return None

# get_zillow_data - mavu 20170518
def get_zillow_data(property_name, address, zip_code, zpid):
    """Processing Zillow Data"""
    property_zillow = PG.get_property_zillow(property_name)
    if property_zillow is None:
        # find zpid
        # if zpid in [0, '0']:
        #     zpid = get_zpid(address, zip_code)
        deepcomp_details = do_zillow_deepcomp(zpid)
        property_details = do_zillow_property_details(zpid)
        address_list = property_name.split('_')
        PG.save_property_zillow(property_name, address_list[0],
                                deepcomp_details,
                                property_details)
        property_zillow = PG.get_property_zillow(property_name)

    return {'property_zillow' : property_zillow, 'zpid' : zpid}

# Get Zillow Info
def get_zpid(address, zip_code):
    """Get zpid from zillow"""
    zpid = 0
    zillow_results = get_search_results(address, zip_code)
    if zillow_results != 0:
        if isinstance(zillow_results['result'], list):
            for at_property in zillow_results['result']:
                zpid = at_property['zpid']
        else:
            zpid = zillow_results['result']['zpid']

    return zpid
