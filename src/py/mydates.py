'''Custom Datetime Functionality'''
import datetime
import sys
sys.path.append('')

ONEDAY = datetime.timedelta(days=1)
# This timedelta object can be added to the most recent quote to find
# the next day for fetching new quotes.

ONEYEAR = 365 * ONEDAY

def date_from_string(_str):
    '''Given a string such as "2011-11-02", convert it to a date object'''
    year, month, day = [int(i) for i in _str.split("-")]
    return datetime.date(year, month, day)

def date_from_timestamp(_str):
    '''Given a string such as "1520323200", convert it to a date object'''
    return datetime.datetime.fromtimestamp(_str)

def string_from_date(date):
    '''Given a datetime.date, convert it to a string such as "2011-11-02"'''
    year, month, day = (date.year, date.month, date.day)
    return "%04d-%02d-%02d" % (year, month, day)

def shortdate(date):
    '''Given a datetime.date, convert it to a short string
       representing string such as "12/14", "12/21", or "12/28".
    '''
    month, day = (date.month, date.day)
    return "%02d/%02d" % (month, day)

# Mavu - add not_day 20170526
# pylint: disable=unbalanced-tuple-unpacking
def tuple_from_date(date, not_day=False):
    '''Given a datetime.date, convert it to a (yyyy,mm,dd) tuple.
    If not_day is check return include day or not,
    Default return (Year, Month, Day)
    '''
    if not_day:
        return (date.year, date.month)
    return (date.year, date.month, date.day)

def date_from_tuple(ymd_tuple):
    '''Given a (y,m,d) tuple, return a datetime.date.'''
    year, month, day = ymd_tuple

    if month == 2 and day > 28:
        day = 28

    if day > 30:
        day = 30

    return datetime.date(year, month, day)


def today():
    '''Today'''
    return datetime.date.today()

def weekend(date):
    '''Return true if date is a Saturday or Sunday'''
    return date.isoweekday() > 5

def as_date(date):
    '''Convert string to date'''
    if isinstance(date, str):
        date = date_from_string(date)
    return date

def beginning_of_year(date):
    '''Given a date, return a new date with the same year but with
       01-01 for the month and day.
    '''
    date = as_date(date)
    newdate = datetime.date(date.year, 1, 1)
    return newdate

# earlier than any date I will ever need
EARLY = date_from_string("1947-01-14")
# later than any date I will ever need
LATE = date_from_string("2150-12-31")


def date_range_str(start_date, end_date):
    '''Return a string appropriately describing the date range. This is a helper
       method used by various account reports.
    '''
    start_date = as_date(start_date)
    end_date = as_date(end_date)
    if (start_date == EARLY) and (end_date == LATE):
        result = ""
    elif start_date == EARLY:
        result = "(through %s)" % end_date
    elif end_date == LATE:
        result = "(from %s)" % start_date
    else:
        result = "(%s through %s)" % (start_date, end_date)
    return result

def days_between(start_date, end_date):
    '''Return the datetime.timedelta, so
       dayBetween("2005-01-01", "2005-12-31") --> 364 days
    '''
    start_date = as_date(start_date)
    end_date = as_date(end_date)
    return (end_date - start_date).days

def days_between_inclusive(start_date, end_date):
    '''Return the inclusive datetime.timedelta, so
       dayBetween("2005-01-01", "2005-12-31") --> 365 days
    '''
    return days_between(start_date, end_date) + 1


# ##############################################################
# Functions to return a series of dates
# ##############################################################

def weekly_dates(from_date, to_date):
    '''Return a series of weekly ending dates inclusively from the
       given fromDate through the toDate.
    '''
    sevendays = 7 * ONEDAY
    #days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    result = []
    next_date = as_date(from_date)
    last_date = as_date(to_date)

    while next_date <= last_date:
        result.append(next_date)
        next_date = next_date + sevendays
    return result


def monthly_dates(from_date, to_date):
    '''Return a series of month ending dates inclusively from the
       given fromDate through the toDate.  For example, if the
       fromDate is "1995-04-30" and the toDate is "1995-09-30" then
       the series would be ["1995-04-30", "1995-05-31", "1995-06-30",
       "1995-08-31", "1995-09-30"].  The beginning and ending dates
       must be month-end dates.
    '''
    #              Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec
    max_month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    result = []
    next_date = as_date(from_date)
    last_date = as_date(to_date)
    year = next_date.year
    month = next_date.month

    while next_date <= last_date:
        #print ("(nextDate, lastDate) = (%s, %s)" % (nextDate, lastDate))
        result.append(next_date)
        month = month + 1
        if month == 13:
            month = 1
        if month == 1:
            year = year + 1
        try:
            next_date = datetime.date(year, month, max_month_days[month - 1])
        except:# pylint: disable=W0702
            # this happens whenever month is Feb and year is not a leap year
            next_date = datetime.date(year, month, 28)
    #weekday = start.weekday()
    # gives the index of the week where 0=Monday, 1=Tuesday, ..., 6=Sunday
    #weekday2 = start.isoweekday()
    # Sunday is 7 and Monday is 1

    return result

def quarterly_dates(from_date, to_date):
    '''Return a series of quarterly ending dates inclusively from the
       given fromDate through the toDate.  For example, if the
       fromDate is "1995-03-31" and the toDate is "1995-09-30" then
       the series would be ["1995-03-31", "1995-06-30", "1995-09-30"].
       The beginning and ending dates must be month-end dates.
    '''
    #              Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec
    max_month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    result = []
    next_date = as_date(from_date)
    last_date = as_date(to_date)
    year = next_date.year
    month = next_date.month
    #day   = nextDate.day

    while next_date <= last_date:
        #print ("(nextDate, lastDate) = (%s, %s)" % (nextDate, lastDate))
        result.append(next_date)
        month = month + 3
        if month > 12:
            month = 3
        if month == 3:
            year = year + 1
        try:
            next_date = datetime.date(year, month, max_month_days[month - 1])
        except:# pylint: disable=W0702
            # this happens whenever month is Feb and year is not a leap year,
            # which cannot happen for quarters, but leave it here anyway for now
            next_date = datetime.date(year, month, 28)
    return result

def yearly_dates(from_year, to_year):
    '''Return a series of year ending dates inclusively from the
       given fromYear through the toYear.  E.g.,
          yearly_dates (1998, 2011)
    '''
    next_year = from_year

    result = []
    while next_year <= to_year:
        result.append(datetime.date(next_year, 12, 31))
        next_year += 1
    return result

def add_one_year(datet):
    '''Add One year'''
    (year, month, day) = tuple_from_date(datet)
    return date_from_tuple((year + 1, month, day))

def subtract_one_year(datet):
    '''Subtract One year'''
    (year, month, day) = tuple_from_date(datet)
    return date_from_tuple((year - 1, month, day))

def subtract_days(datet, numb):
    """Subtract numb days"""
    # back up numb days from datet
    datetime.timedelta(days=numb)
    return datet - datetime.timedelta(days=numb)

def yesterday(datet=None):
    """Answer the day before the datet (if given) else answer
    the day before today"""
    if datet is None:
        datet = today()
    return subtract_days(datet, 1)

def add_one_month(datet):
    """Add 1 month"""
    (year, month, day) = tuple_from_date(datet)
    month += 1
    if month > 12:
        month = 1
        year += 1
    return date_from_tuple((year, month, day))

def add_months(datet, numb):
    """Add numb months"""
    (year, month, day) = tuple_from_date(datet)
    while numb > 12:
        year += 1
        numb -= 12
    month += numb
    if month > 12:
        month = 1
        year += 1

    return date_from_tuple((year, month, day))


def is_leap_year(datet):
    """Check LeapYear"""
    year, _, _ = tuple_from_date(datet)
    div_by4 = (year % 4) == 0
    if not div_by4:
        return False
    div_by100 = (year % 100) == 0
    div_by400 = (year % 400) == 0

    if div_by100 and not div_by400:
        return False
    return True

def test_leap_year(datet):
    '''Test leap year'''
    if is_leap_year(datet):
        print "%s is a leap year" % datet
    else:
        print "%s is not a leap year" % datet

def test_leap_years():
    '''Test leap years'''
    for datet in ["1996-03-10", "1998-06-30", "2000-01-01", "2001-02-02",
                  "2002-03-03", "2003-04-04", "2004-05-05", "2014-01-14",
                  "2015-01-14", "2016-01-14", "2100-01-14", "2104-01-14",
                  "2200-09-11", "2400-10-12"]:

        test_leap_year(date_from_string(datet))


               # example
               # monthly_datesFrom ("2011-01-31")
               # monthly_datesFrom ("2010-01-31", "2011-12-31")
