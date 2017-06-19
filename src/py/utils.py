"""utils.py by fcs"""

# Miscellaneous utilities used by the other files.

# following allows printing commas to separate thousands with something like
#     locale.format('%13.2f', 12345.92, True)
# or
# locale.setlocale(locale.LC_ALL, "en_US")

# For getting commas to separate thousands
# Here is Tim Keating's comment at
# http://code.activestate.com/recipes
# /498181-add-thousands-separator-commas-to-formatted-number/
# >>> locale.setlocale(locale.LC_ALL, "")    -->  'English_United States.1252'
# >>> locale.format('%d', 12345, True)       -->  '12,345'
# and following is my test with a float
# >>> locale.format('%13.2f', 12345.92, True)

import locale
locale.setlocale(locale.LC_ALL, "")

# This is from PPW32
ROUNDING_THRESHOLD = 0.0001    #100 times smaller than cents or pennies

def is_zero(numb):
    '''Is Zero'''
    return abs(numb) < ROUNDING_THRESHOLD

def rounded(numb):
    '''Format the number'''
    if is_zero(numb):
        return 0.0
    return numb

def money(num, width=10, decimals=2):
    '''Format a number with commas.  E.g.,
       money(13250) --> ' 13,250.00'
    '''
    fmt = "%%%d.%df" % (width, decimals)
    return locale.format(fmt, num, True)

def money12(numb):
    '''Format number money 12'''
    return money(numb, 12)

def money14(numb):
    '''Format number money 14'''
    return money(numb, 14)

def money_3(num):
    '''Format number money'''
    return money(num, decimals=3)

def money14_3(num):
    '''Format number money'''
    return money(num, 14, 3)


def first(seq):
    '''Fisrt'''
    return seq[0]

if __name__ == '__main__':
    print "hello utils.py"
