"""Housecanary Unittest"""
import os
import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import unittest
from src.py.housecanary import (get_housecanary_data)
from src.py.pg import PGWriter
PG = PGWriter()

ADDRESSES = [
    {'zipcode': '89128',
     'address': '7904 Verde Springs Dr',
     'property_name': '7904-Verde-Springs-Drive_Las-Vegas-NV-US_89128'},
    {'zipcode': '33473',
     'address': '8691 Flowersong Cv',
     'property_name': '8691-Flowersong-Cove_Boynton-Beach-FL-US_33473'},
    {'zipcode': '78255',
     'address': '22905 Cielo Vis',
     'property_name': '22905-Cielo-Vista-Drive_San-Antonio-TX-US_78255'},
    {'zipcode': '03076',
     'address': '16 Thomas Ave',
     'property_name': '16-Thomas-Avenue_Pelham-NH-US_03076'},
    {'zipcode': '55407',
     'address': '2718 16th Ave S',
     'property_name': '2718-16th-Avenue-South_Minneapolis-MN-US_55407'},
    {'zipcode': '95023',
     'address': '590 Foothill Rd',
     'property_name': '590-Foothill-Road_Hollister-CA-US_95023'},
    {'zipcode': '81211',
     'address': '30737 County Road 356-6',
     'property_name': '30737-County-Road-356-6_Buena-Vista-CO-US_81211'},
    {'zipcode': '48162',
     'address': '3466 Erie Shore Dr',
     'property_name': '3466-Erie-Shore-Drive_Monroe-MI-US_48162'}
]

# pylint: disable=R0904
class TestHouseCanary(unittest.TestCase):
    """Test Housecanary Functions"""

    # preparing to test
    def setUp(self):
        """ Setting up for the test """
        self.result = ''

    # ending the test
    def tearDown(self):
        """Cleaning up after the test"""
        for item in list(ADDRESSES):
            PG.remove_housecanary_details(item['property_name'])
            PG.remove_housecanary_census(item['property_name'])
            PG.remove_housecanary_zip_details(item['property_name'])
            PG.remove_housecanary_sales_history(item['property_name'])
            PG.remove_housecanary_school(item['zipcode'])
            PG.remove_housecanary_geocode(item['zipcode'])
        print 'HouseCanary ' + self.result

    def test_get_housecanary_data(self):
        '''Test get_housecanary_data function'''
        self.result = 'Data tested: '
        for item in list(ADDRESSES):
            flag = False
            self.result += ", " + item['address'] \
                if self.result != 'Data tested: ' \
                else item['address']
            params = {'address': item['address'], 'zipcode': item['zipcode']}
            data = get_housecanary_data(item['property_name'], params)
            for result in list(data):
                if result:
                    flag = True
                    break
            self.assertTrue(flag, 'Did not see data for: ' + item['address'])

if __name__ == '__main__':
    # run all TestCase's in this module
    unittest.main()
