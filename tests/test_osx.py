# -*- coding: utf-8 -*-
# test_osx.py

# If on a Mac, launch with pgzrun, and check for correct process name:
# Without fix:
#   502 49953 21828   0 10:12pm ttys002    0:23.14 /Users/rcollin2/.virtualenvs/wasabi2d/bin/python /Users/rcollin2/.virtualenvs/pgzero/bin/pgzrun key_test.py
# With fix:
#
# $ ps -ef | grep -i wasabi2d | grep -i python
#   502 49953 21828   0 10:12pm ttys002    0:23.14 /Users/rcollin2/.virtualenvs/wasabi2d/bin/python /Users/rcollin2/.virtualenvs/pgzero/bin/pgzrun key_test.py
#
# $  ps -ef | grep -i wasabi2d | grep -i python
#   502 59772 21828   0 10:32pm ttys002    0:01.94 /Library/Frameworks/Python.framework/Versions/3.4/Resources/Python.app/Contents/MacOS/Python -m wasabi2d key_test.py

# ps -ef | grep -i python | grep -iE 'wasabi2d | pgzrun'
#   502 59772 21828   0 10:32pm ttys002    4:23.73 /Library/Frameworks/Python.framework/Versions/3.4/Resources/Python.app/Contents/MacOS/Python -m wasabi2d key_test.py

