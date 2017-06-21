"""Zillow Unittest"""
import os
import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import unittest
from src.py.pg import PGWriter
from src.py.zillow import (get_zillow_data,
                           ajax_search_zpid,
                           get_zpid,
                           do_zillow_deepcomp,
                           do_zillow_property_details)
PG = PGWriter()

MULTI_UNIT = {"address": "1024 Park Avenue", "zip_code": "07030"}

DEEPCOMPS = {"address": "1345 Gardner Road Northwest",
             "zip_code": "30012", "zpid": "15012675",
             "property_name": "1345-Gardner-Road-Northwest_Conyers-GA-US_30012"}

PROPERTY_DETAILS = {"address": "1345 Gardner Road Northwest",
                    "zip_code": "30012", "zpid": "15012675",
                    "property_name": \
                        "1345-Gardner-Road-Northwest_Conyers-GA-US_30012"}

ZILLOW_DATA = {"address": "6552 Whitetail Ln",
               "zip_code": "38115", "zpid": "2098357337",
               "property_name": "6552-Whitetail-Lane_Memphis-TN-US_38115"}

GET_ZPID = {"address": "815 Park Avenue",
               "zip_code": "07030", "zpid": "2126967105",
               "property_name": "815-Park-Avenue_Hoboken-NJ-US_07030"}

# pylint: disable=R0904
class TestZillow(unittest.TestCase):
    """Test Zillow Functions"""

    # preparing to test
    def setUp(self):
        """ Setting up for the test """
        self.remove_flg = 0
        self.result = ''

    # ending the test
    def tearDown(self):
        """Cleaning up after the test"""
        PG.remove_property_zillow(ZILLOW_DATA['property_name'])
        print 'Zillow ' + self.result

    def test_multi_unit(self):
        '''Test multi unit by ajax_search_zpid function'''
        self.result = 'Multi Unit tested: ' + MULTI_UNIT['address']
        data = ajax_search_zpid(MULTI_UNIT['address'], MULTI_UNIT['zip_code'])
        self.assertIsInstance(data, list, 'This is not multi unit: ' + \
            MULTI_UNIT['address'])

    def test_do_zillow_deepcomp(self):
        '''Test do_zillow_deepcomp function'''
        self.result = 'Deepcomp tested: ' + DEEPCOMPS['address']
        data = do_zillow_deepcomp(DEEPCOMPS['zpid'])
        self.assertIsNotNone(data, 'Did not see Deepcomp data for: ' + \
            DEEPCOMPS['address'])

    def test_do_zillow_property_details(self):
        '''Test do_zillow_property_details function'''
        self.result = 'Property Details tested: ' + PROPERTY_DETAILS['address']
        data = do_zillow_property_details(PROPERTY_DETAILS['zpid'])
        self.assertIsNotNone(data, 'Did not see Property Details data for: ' \
            + PROPERTY_DETAILS['address'])

    def test_get_zillow_data(self):
        '''Test get_zillow_data function'''
        self.result = 'Data tested: ' + ZILLOW_DATA['address']
        data = get_zillow_data(ZILLOW_DATA['property_name'],
                               ZILLOW_DATA['address'],
                               ZILLOW_DATA['zip_code'],
                               ZILLOW_DATA['zpid'])
        self.assertIsNotNone(data['property_zillow'], \
                'Did not see data for: ' + ZILLOW_DATA['address'])

    def test_get_zpid(self):
        '''Test get_zpid function'''
        self.result = 'Get Zpid tested: ' + GET_ZPID['address']
        data = get_zpid(GET_ZPID['address'], GET_ZPID['zip_code'])
        self.assertEqual(data, GET_ZPID['zpid'], \
            'Zpid not match: ' + GET_ZPID['address'])

if __name__ == '__main__':
    # run all TestCase's in this module
    unittest.main()
