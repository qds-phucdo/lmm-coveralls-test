"""Amort Mondule"""
from math import ceil
import sys
#import datetime
import os
from os import path
sys.path.append(os.getcwd())
# pylint: disable=W0403
from mydates import (string_from_date,
                     tuple_from_date,
                     date_from_tuple,
                     as_date,
                     days_between,
                     subtract_one_year,
                     yesterday,
                     add_months,
                     is_leap_year)
from utils import money
sys.path.append('')

# pylint: disable=R0902
class Loan(object):
    """Hold the details of a loan and calculate an amortization schedule.

          origindate     : the date the loan was made
          loan_amount     : the amount loaned (initial principal)
          payment        : the total payment due each month (other than any
                irregular payments in firstpayments) or "unknown"
          interest       : annual interest rate as a percentage,
                such as 6 for 6% or 7.25 for 7.25%
          firstpayments  : a list of (date, amount) pairs for initial
                (possibly) irregular payments
          days           : how many days in a month. Should
                be "actual" or "30".  Ignored if period is not "monthly".
          basis          : how many days in a year.  Should be "actual"
                or "365" or "360".  Ignored if period is not "monthly".
          dueday         : the day of the month all subsequent payments
                are due.  If this is
                not specified, it is the taken as the day of the origindate.
          number_of_payments : either an integer or "unknown".
                Must be known if  payment is "unknown".
          period         : must be "monthly", "quarterly",
                "semi-annual", or "annual"
          years_method    : must be "civil" or "anniversary"
          # We might later use number_of_payments="unknown"
                and payment="unknown" to indicate an interest only loan.
    """
    # pylint: disable=R0913
    def __init__(self, origindate, loan_amount, interest,
                 payment="unknown", number_of_payments="unknown",
                 firstpayments=None, days="actual", basis="actual", dueday=None,
                 period="monthly", years_method="civil"):
        self.origindate = as_date(origindate)
        self.amount = loan_amount
         # so we can remember if payment was "unknown" to begin with
        self.originalpayment = payment
        self.payment = payment
        self.annualrate = interest / 100.0
        self.firstpayments = firstpayments
        self.days = days
        self.basis = basis
        self.dueday = dueday
        if self.dueday is None:
            self.dueday = self.origindate.day
        self.number_of_payments = number_of_payments
        self.period = period
        self.months_between_payments = {
            "monthly":1, "quarterly":3,
            "semi-annual":6, "annual":12
        }[self.period]
        self.payments_per_year = {
            "monthly":12, "quarterly":4,
            "semi-annual":2, "annual":1
        }[self.period]
        self.years_method = years_method

        self.principal = float(self.amount)
        self.last_payment = origindate  # a slight misnomer at first
        self.payments = None

        fraction_choices = {"monthly":"", "quarterly":"quarter year",
                            "semi-annual":"half year", "annual":"full year"}
        self.fraction = fraction_choices[self.period]

        if isinstance(payment, int):
            self.payment = float(payment)

        if not (payment == "unknown" or isinstance(payment, float)):
            raise ValueError('payment must be either "unknown" or an '\
                'integer (such as 100) or a float (such as 100.00)')

        if not ((number_of_payments == "unknown") \
                or isinstance(number_of_payments, int)):
            raise ValueError('number_of_payments must be either "unknown" '\
                'or an integer (such as 20 or 36")')

        if (payment == "unknown") and (number_of_payments == "unknown"):
            raise ValueError('payment and number_of_payments '\
                'cannot both be "unknown"')

        if payment == "unknown":
            # Calculate the payment based upon period, interest rate,
            # and number of payments.
            self.payment = self.calculate_payment()

        if not isinstance(self.days, str):
            raise ValueError('days must be in quotation marks')
        if self.days not in ["actual", "30"]:
            raise ValueError('days must be either "actual" or "30"')

        if not isinstance(self.basis, str):
            raise ValueError('basis must be in quotation marks')
        if self.basis not in ["actual", "365", "360"]:
            raise ValueError('basis must be either "actual" or "365" or "360"')

        self.schedule = []
        self.last_new_principal = 0.00

    def pro_next_payment(self):
        '''This is a generator function and returns a generator.
        Call it like this:
            np = pro_next_payment()
                while <whatever>:
                    next(np)
        '''
        yield (self.origindate, 0.00)
        last_date = self.origindate
        if self.firstpayments:
            for datet, amt in self.firstpayments:
                yield (as_date(datet), amt)
                last_date = as_date(datet)
        cnt = 0
        # while True and (cnt < 100):     # for testing
        while True:
            # What we want to do is find the month that follows the last date,
            #  and then plug the  dueday and the proper year into it.
            cnt += 1
            #print ("---- last_date is %s ----" % last_date)
            new_date = add_months(last_date, self.months_between_payments)
            # pylint: disable=W0632
            (y_year, m_month) = tuple_from_date(new_date, True)
            new_date = date_from_tuple((y_year, m_month, self.dueday))
            last_date = new_date
            yield (new_date, self.payment)
            if (self.number_of_payments == "unknown") and (cnt > (12 * 35)):
                # If we haven't finished after 35 years of monthly
                # payments (or even more years of quarterly etc.), then
                # probably the wrong payment amount has been entered.
                raise ValueError('Balance not declining due to'\
                    ' too small a payment?')

    def calculate_schedule(self):
        """ Create a list of payments where each item contains principal,
            date, payment amount, interest, new principal.  Terminate
            when the principal is zero or the number_of_payments has been
            reached.
        """

        nextp = self.pro_next_payment()
        items = []
        prev_dt, _ = next(nextp)
        principal = self.amount
        payment_number = 1
        new_principal = 0
        #while (principal > 0.00) and (paymentNumber < 15):    # for testing
        while (principal > 0.00) and ((self.number_of_payments == "unknown") \
                or (payment_number <= self.number_of_payments)):
            (datet, pmt) = next(nextp)

            fraction, interest = self.calculate_interest(prev_dt, datet,
                                                         principal)
            new_amount_owed = principal + interest
            pmt = min(pmt, new_amount_owed)
            toward_principal = max((pmt - interest), 0.00)
            new_principal = round(new_amount_owed - pmt, 2)
            new_item = [payment_number, datet, principal, pmt, fraction,
                        interest, toward_principal, new_principal]
            items.append(new_item)
            principal = new_principal
            prev_dt = datet
            payment_number += 1

        self.schedule = items
        self.last_new_principal = new_principal

    def print_schedule(self):
        '''Print schedule'''
        items = self.schedule
        print
        print "    #        date  prev balance        payment   "\
            "period             interest     principal   new balance"
        print " ----  ----------  ------------   ------------   "\
            "-------------  ------------  ------------  ------------"

        for i in items:
            num, datet, prev, pmt, fraction, interest, \
                toward_principal, new_principal = i
            formatted_items = (num, string_from_date(datet), money(prev, 12),
                               money(pmt, 12), fraction, money(interest, 8),
                               money(toward_principal, 10),
                               money(new_principal, 12))
            print " %4d  %10s  %12s   %12s   %-13s  %12s "\
                " %12s  %12s" % formatted_items

    def amort(self):
        '''amort'''
        finished = False
        while not finished:
            #print ("Calculate schedule with payment of %-.2f" % self.payment)
            self.calculate_schedule()
            if (self.originalpayment == "unknown") \
                    and (self.last_new_principal > 0.00):
                self.payment += 0.01  # bump it by a penny and try again
            else:
                finished = True
            if self.last_new_principal > 0.00:
                # We have a balloon payment, so add what would have
                #  been the last new principal to the last payment,
                #  thus wiping out the last new principal.
                # bump payment
                self.schedule[-1][3] += self.last_new_principal
                # pump towardPrincipal
                self.schedule[-1][6] += self.last_new_principal
                self.schedule[-1][-1] = 0.00

        #self.print_schedule()
        return self.schedule

    def days_elapsed(self, prev, cur):
        """ Calculate the number of days this period to use for determining
            the interest for this period.  This depends on whether we
            use actual or 30.
        """
        actual_days = days_between(prev, cur)
        if self.days == "actual":
            return actual_days
        elif self.days == "30":
            return min(actual_days, 30)
            # fixme: I'm not sure the elif above is exactly right?  For
            # example, might we have 30/actual where we have to split a
            # payment in January across two years?  Or, what if there
            # are irregular payments?
        else:
            raise RuntimeError("Unexpected else condition in days_elapsed()")

    def days_in_year(self, cur):
        """ Calculate the number of days in the year for the basis of the
            interest calculation.  This is actual or 365 or 360.  In
            the case of "actual", we consider leap year.  There are
            two common ways: (1) civil year or (2) anniversary.
        """

        if self.years_method == "civil":
           # Civil year method:

           #   cur represents the ending date of an interest period.
           #   E.g., for the period Dec 12, 2014 to Jan 12, 2015, cur
           #   would be Jan 12, 2015.  We want to know if the day
           #   before (i.e., Jan 11, 2015) falls in a leap year.  The
           #   tricky case is Dec x,YYYY to Jan 1, YYYY+1.  The day
           #   before is Dec 31, YYYY, and that's the date that
           #   matters for whether this period has 366 or 365 days.
           #   (Because the interest includes the "from" date but not
           #   the "to" date.)

            if is_leap_year(yesterday(cur)):
                return 366
            return 365

        # Anniversary method
        # In this case, we do not back cur up by a day, as the days_between
        # takes care of that for us.

        a_year_ago = subtract_one_year(cur)
        return days_between(a_year_ago, cur)

    def calculate_interest(self, prev_date, cur_date, principal):
        """Answer a (fraction,interest) tuple where fraction is a string
           representing the portion of the year over which the
           interest is calculated.

           In the case of monthly actual/actual, a period spanning
           January 1st would look something like "20/365,11/366".
           Otherwise, for monthly, it would look like "31/365".  For
           other periods, it would be "quarter year", "half year", or
           "full year".

           When period is not monthly, interest does not consider the
           actual number of days, just the fraction of the year.

        """
        if self.period == "monthly":
            if (self.days == "actual") and (prev_date.year != cur_date.year) \
                and ((cur_date.month > 2) or (cur_date.day > 1)):
                # Do we cross the end of the year?  That is are some
                # of the days in one year and some in the following
                # year?  Note, Dec x to Jan 1 does not cross, but Dec
                # x to Jan 2 or later does.  Thus, we must compute the
                # interest in two steps (one for the days in each of
                # the two years).
                # Jan 1st of cur_date.year
                jan1st = date_from_tuple((cur_date.year, 1, 1))
                ndays1 = self.days_elapsed(prev_date, jan1st)
                ydays1 = self.days_in_year(jan1st)
                # days from Jan 1st to cur_date
                ndays2 = self.days_elapsed(jan1st, cur_date)
                ydays2 = self.days_in_year(cur_date)
                fraction = "%s/%s,%s/%s" % (ndays1, ydays1, ndays2, ydays2)
                int1 = (principal * ndays1 * self.annualrate) / ydays1
                int2 = (principal * ndays2 * self.annualrate) / ydays2
                interest = round(int1 + int2, 2)
            else:
                # We do not need to split the days into to parts (even
                # if we cross a year boundary).
                ndays = self.days_elapsed(prev_date, cur_date)
                ydays = self.days_in_year(cur_date)
                fraction = "%s/%s" % (ndays, ydays)
                interest = round((principal * ndays * self.annualrate) / ydays,
                                 2)
        else:
            # since it is not monthly, it must be
            # "quarterly", "semi-annual", or "annual"
            fraction = self.fraction
            interest = principal * self.annualrate
            if self.period == "quarterly":
                interest = interest / 4.0
            elif self.period == "semi-annual":
                interest = interest / 2.0
            elif self.period == "annual":
                pass # i.e., divide by 1.0

        return (fraction, interest)

    def calculate_payment(self):
        """Calculate the periodic payment from the initial loan_amount, the
           annual interest rate, and the number of payments total and
           per year. Answer the monthly payment.
        """
        return calculate_payment(self.amount, self.number_of_payments,
                                 self.annualrate, self.payments_per_year)

def calculate_payment(loan_amount, n_payments,
                      annualrate, n_payments_per_year=12):
    """Calculate the periodic payment from the initial loan_amount, the
       annual interest rate, and the number of payments total and
       per year. Answer the monthly payment. E.g., $1000.00 at 7% repaid
       monthly over 15 payments:

           calculate_payment (1000.00, 15, 0.07, 12)

    """

    if n_payments_per_year is 0:
        n_payments_per_year = 12

    foo_pv = loan_amount
    foo_r = annualrate  /  n_payments_per_year
    foo_n = n_payments
    numerator = foo_r * foo_pv
    denominator = 1 - pow(1 + foo_r, -foo_n)
    pmt = numerator / denominator
    #print ("(pv,r,n,numerator,denominator,pmt) = (%s,%s,%s,%s,%s,%s)"
    #% (pv, r, n, numerator, denominator, pmt))
    #print ("100 * pmt = %s" % (100 * pmt))
    #print ("ceil(100 * pmt) = %s" % (ceil(100 * pmt)))
    #print ("round (ceil(100 * pmt) / 100, 2) = %s"
    #% (round (ceil(100 * pmt) / 100, 2)))
    return round(ceil(100 * pmt) / 100, 2)


if __name__ == '__main__':

    # When called directly, do an example amortization

    INIT_LOAN = Loan(
        # In the following,
        #   the loan is made on March 10, 2014 in the amount of $2,000.00,
        #   with a monthly payment due of $100.00,
        #   the interest rate is 7% per annum, two first payments are specified,
        #   interest will be calculated
        #   on an actual/actual basis, and the due date (after any first
        #   payments) will be the 10th of the month.
        origindate="2014-03-10",
        loan_amount=2000.00,
        payment=100.00,
        interest=7,
        firstpayments=(("2014-04-15", 100.00),
                       ("2014-05-10", 100.00)),
        days="actual",
        basis="actual",
        dueday=10,
        number_of_payments="unknown")

    INIT_LOAN.amort()
