"""Projection Module"""
import time
import datetime
import sys
import os
from os import path
sys.path.append(os.getcwd())
# pylint: disable=W0403
from mydates import (date_from_timestamp,
                     string_from_date,
                     today,
                     add_one_year)
from src.py.helper import (format_one)
from src.py.amort import (Loan)
sys.path.append('')

# pylint: disable=R0902
class Projections(object):
    """Hold the details of a loan and calculate an amortization schedule.
          at_property              : property object after access function
                run_calculate
          number_of_years         : number year for projections schedule
          ren_growth             : Monthly Rent increases 2% a year
          appreciation_percent   : Appreciation 3% default
          tax_increase           : Property Taxes increases 2% a year
    """
    # pylint: disable=R0913
    def __init__(self, at_property, number_of_years=30, ren_growth=0.02,
                 appreciation_percent=0.03, tax_increase=0.02,
                 insurance_increase=0.02):
        self.at_property = at_property
        # number_of_years is int and > 0
        self.number_of_years = number_of_years \
            if isinstance(number_of_years, int) and number_of_years > 0 else 30
        self.purchase_price = self.at_property['hard']['purchase_price']
        self.property_taxes = self.at_property['cost']['property_taxes'] * -1
        self.property_insurance = self.at_property['cost']\
            ['property_insurance'] * -1
        self.property_management_percent = self.at_property['cost']\
            ['property_management_percent'] / 100
        self.yearly_rent = self.at_property['hard']['rent'] * 12
        self.yearly_pm = (self.property_management_percent * self.yearly_rent) \
            * -1
        self.yearly_mortgage_payment = (self.at_property['calc']\
            ['mortgage_payment'] * 12) * -1
        self.yearly_hoamisc = (self.at_property['cost']['hoa_misc'] * 12) * -1
        self.rent_increases_per_year = ren_growth
        # Property Value increases 3% a year
        self.property_increases_per_year = 0.03
        self.pr_taxes_increases_per_year = tax_increase
        # Property Insurance increases 2% a year
        self.pr_insurance_increases_per_year = insurance_increase
        self.schedule = []
        self.equity_schedule = []
        self.loan_schedule = []
        self.yearly_appreciation = appreciation_percent
        if self.at_property['mortgage']['down_payment_percent'] < 100:
            loan = Loan(
                origindate=datetime.datetime.now().strftime("%Y-%m-%d"),
                loan_amount=self.at_property['calc']['mortgage_principle'],
                interest=self.at_property['mortgage']['rate'],
                days="actual",
                basis="actual",
                number_of_payments=int(self.at_property['mortgage']\
                    ['term'] * 12))

            self.loan_schedule = loan.amort()

    # pylint: disable=R0914
    def calculate_schedule(self):
        """ Create a list of projects where each item contains date
            and property's infos in that date include:
            Rental Income, Mortgage Payment, Property Management,
            Property Taxes, Property Insurance,
            Net Cash Flow
        """
        date = today()
        yearly_rent = self.yearly_rent
        purchase_price = self.purchase_price
        property_taxes = self.property_taxes
        property_insurance = self.property_insurance
        yearly_pm = self.yearly_pm
        yearly_mortgage_payment = self.yearly_mortgage_payment
        appreciation_cumulative = purchase_price

        for i in range(1, self.number_of_years + 1):
            # Increase value yearly
            if i != 1:
                date = add_one_year(date)
                yearly_rent *= (1 + self.rent_increases_per_year)
                purchase_price *= (1 + self.property_increases_per_year)
                property_taxes *= (1 + self.pr_taxes_increases_per_year)
                property_insurance *= (1 + self.pr_insurance_increases_per_year)
                yearly_pm = (yearly_rent * self.property_management_percent) * \
                    -1 if yearly_pm != 0 else yearly_pm
                appreciation_cumulative = appreciation_cumulative + \
                    (appreciation_cumulative * self.yearly_appreciation)

            if i > self.at_property['mortgage']['term']:
                yearly_mortgage_payment = 0

            annual_cash_flow = self.calculate_annual_cash_flow(
                yearly_rent, property_taxes, property_insurance,
                yearly_pm, yearly_mortgage_payment)
            self.schedule.append({
                "index" : i,
                "date" : time.mktime(date.timetuple()),
                "rent" : yearly_rent,
                "mortgage_payment" : yearly_mortgage_payment,
                "property_management" : yearly_pm,
                "property_taxes" : property_taxes,
                "property_insurance" : property_insurance,
                "annual_cash_flow" : annual_cash_flow
            })

            equity_cash_flow = annual_cash_flow + self.equity_schedule[i - 2]\
                ['cashflow'] if i != 1 else annual_cash_flow
            equity_appreciation = self.equity_schedule[i - 2]['appreciation'] \
                + (appreciation_cumulative * self.yearly_appreciation) \
                    if i != 1 else purchase_price * self.yearly_appreciation
            equity_value = self.at_property['mortgage']['down_payment_dollar'] \
                + self.principle_to_year(add_one_year(date))
            medium_cash_flow_this_year = (((annual_cash_flow \
                - yearly_mortgage_payment) / 12) \
                - self.at_property['cost']['capex_dollar'] \
                - self.at_property['cost']['vacancy_rate_dollar'] \
                - self.at_property['calc']['mortgage_payment']) * 12
            medium_cash_flow = self.equity_schedule[i - 2]['medium_cashflow'] \
                + medium_cash_flow_this_year if i != 1 \
                else medium_cash_flow_this_year
            long_cash_flow_this_year = yearly_rent - (yearly_rent * 0.5) + \
                yearly_mortgage_payment + self.yearly_hoamisc
            long_cash_flow = self.equity_schedule[i - 2]['long_cashflow'] + \
                long_cash_flow_this_year if i != 1 else long_cash_flow_this_year

            self.equity_schedule.append({
                "index" : i,
                "date" : time.mktime(add_one_year(date).timetuple()),
                "equity" : equity_value,
                "cashflow" : equity_cash_flow,
                "medium_cashflow" : medium_cash_flow,
                "long_cashflow" : long_cash_flow,
                "appreciation" : equity_appreciation,
                "total_cashflow": equity_cash_flow + equity_appreciation + \
                    equity_value,
                "total_medium_cashflow" : medium_cash_flow + \
                    equity_appreciation + equity_value,
                "total_long_cashflow" : long_cash_flow + equity_appreciation + \
                    equity_value
            })

        return self.schedule

    def calculate_annual_cash_flow(self, yearly_rent, property_taxes,
                                   property_insurance, yearly_pm,
                                   yearly_mortgage_payment):
        '''Caculate annual'''
        noi = yearly_rent + property_insurance + yearly_pm + \
            property_taxes + self.yearly_hoamisc
        return noi + yearly_mortgage_payment

    def table_html(self):
        '''run calculate_schedule method if schedule list empty'''
        sche_len = len(self.schedule)
        if sche_len == 0:
            self.calculate_schedule()

        projection_table = ""
        columns = ""

        for item in list(self.schedule):
            date = date_from_timestamp(int(item['date']))
            columns += '''
               <div class="column">
                   <div class="cell head">{}</div>
                   <div class="cell body amount black {}">${}</div>
                   <div class="cell body amount black {}">${}</div>
                   <div class="cell body amount black {}">${}</div>
                   <div class="cell body amount black {}">${}</div>
                   <div class="cell body amount black {}">${}</div>
                   <div class="cell foot amount black {}">${}</div>
               </div>
            '''.format(date.year,
                       'positive-num' if item['rent'] > 0 else \
                            ('negative-num' if item['rent'] < 0 else ''),
                       format_one(item['rent']), 'negative-num' \
                            if item['mortgage_payment'] != 0 else '',
                       format_one(item['mortgage_payment']),
                       'negative-num' if item['property_management'] != 0 \
                            else '',
                       format_one(item['property_management']),
                       'negative-num' if item['property_taxes'] != 0 else '',
                       format_one(item['property_taxes']),
                       'negative-num' if item['property_insurance'] != 0 \
                            else '',
                       format_one(item['property_insurance']),
                       'positive-num' if item['annual_cash_flow'] > 0 \
                            else ('negative-num' if \
                                item['annual_cash_flow'] < 0 else ''),
                       format_one(item['annual_cash_flow']))

        projection_table += '''
            <div class="breakout hidden">
                <div class="column titles">
                    <div class="cell head">&nbsp;</div>
                    <div class="cell body">Rental Income</div>
                    <div class="cell body">Mortgage Payment</div>
                    <div class="cell body">Property Manangement</div>
                    <div class="cell body">Property Taxes</div>
                    <div class="cell body">Property Insurance</div>
                    <div class="cell foot">Net Cash Flow</div>
                </div>
                <div class="breakout-scroller">
                    <div class="breakout-table">
                        %s
                    </div>
                </div>
            </div>
        ''' % (columns)

        return projection_table

    def principle_to_year(self, date):
        '''Principle to year'''
        principle = 0
        for item in self.loan_schedule:
            if item[1] > date:
                break
            itm_len = len(item)
            principle += item[6] if itm_len > 6 else 0

        return principle

    def yearly_equity_table_html(self):
        '''run calculate_schedule method if schedule list empty'''
        sch_len = len(self.schedule)
        if sch_len == 0:
            self.calculate_schedule()

        equity_table = ""
        columns = ""

        for item in list(self.equity_schedule):
            date = date_from_timestamp(int(item['date']))
            columns += '''
               <div class="column">
                   <div class="cell head">{}</div>
                   <div class="cell body amount black cf {} {}">${}</div>
                   <div class="cell body amount black cf hidden {} {}">${}</div>
                   <div class="cell body amount black cf hidden {} {}">${}</div>
                   <div class="cell body amount black {}">${}</div>
                   <div class="cell body amount black {}">${}</div>
                   <div class="cell foot amount black total {} {}">${}</div>
                   <div class="cell foot amount black total hidden {} {}">${}</div>
                   <div class="cell foot amount black total hidden {} {}">${}</div>
               </div>
           '''.format(string_from_date(date),
                      'cashflow', 'positive-num' if item['cashflow'] > 0 else \
                            ('negative-num' if item['cashflow'] < 0 else ''),
                      format_one(item['cashflow']), 'medium_cashflow',
                      'positive-num' if item['medium_cashflow'] > 0 \
                            else ('negative-num' if \
                      item['medium_cashflow'] < 0 else ''),
                      format_one(item['medium_cashflow']), 'long_cashflow',
                      'positive-num' if item['long_cashflow'] > 0 \
                            else ('negative-num' if item['long_cashflow'] < 0 \
                            else ''), format_one(item['long_cashflow']),
                      'positive-num' if item['appreciation'] > 0 else \
                            ('negative-num' if item['appreciation'] < 0 \
                            else ''), format_one(item['appreciation']),
                      'positive-num' if item['equity'] > 0 else \
                            ('negative-num' if item['equity'] < 0 else ''),
                      format_one(item['equity']), 'total_cashflow',
                      'positive-num' if item['total_cashflow'] > 0 else \
                            ('negative-num' if item['total_cashflow'] < 0 \
                                else ''), format_one(item['total_cashflow']),
                      'total_medium_cashflow', 'positive-num' if \
                            item['total_medium_cashflow'] > 0 \
                                else ('negative-num' if \
                                    item['total_medium_cashflow'] < 0 else \
                                        ''),
                      format_one(item['total_medium_cashflow']),
                      'total_long_cashflow', 'positive-num' if \
                            item['total_long_cashflow'] > 0 else \
                                ('negative-num' if item['total_long_cashflow'] \
                                    < 0 else ''),
                      format_one(item['total_long_cashflow']))

        equity_table += '''
            <div class="breakout hidden">
                <div class="column titles">
                    <div class="cell head">&nbsp;</div>
                    <div class="cell body">Cash Flow</div>
                    <div class="cell body">Appreciation</div>
                    <div class="cell body">Equity</div>
                    <div class="cell foot">Total Value</div>
                </div>
                <div class="breakout-scroller">
                    <div class="breakout-table">
                        %s
                    </div>
                </div>
            </div>
        ''' % (columns)

        return equity_table
