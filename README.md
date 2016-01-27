qm-python-tools
===============

This project contains some Python scripts that illustrate the use of
Questionmark's APIs.  For more information about the APIs themselves
go to [developer.questionmark.com](https://developer.questionmark.com/)


Getting Started
---------------

You should install the latest version of the
[Pyslet](http://www.pyslet.org/) package, available from github
(periodic builds are made available on PyPi but this code currently
relies features that are only in the master branch on GitHub.

Download https://github.com/swl10/pyslet/archive/master.zip

Unzip and run:

    python setup.py install

You will also need to install Django package (recommended from PyPi) as
this demo uses the templating language defined there.  You will need to
install pip first if you don't have it ([not sure? read
this](https://pip.pypa.io/en/latest/installing/):

    pip install Django
    
Once you have Pyslet and Django installed you are ready to run the demo
application. It takes the form of a web application that is launched
from the command line and used with a web browser.

To run the application simply pass the identifier of a Questionmark
OnDemand area using the -c option and tell the application where to find
images and css files.  It will prompt for the a password used to access
the area (the user id is assumed to be the same as the customer id):

    $ python dodata_demo.py -c 123456 --static=static
    Password: 
    WARNING:root:No certificate path set, SSL communication may be vulnerable to MITM attacks

Now go to your web browser and navigate to http://localhost:8080/

You should see the application log the web requests as they happen:

    1.0.0.127.in-addr.arpa - - [27/Jan/2016 17:40:31] "GET / HTTP/1.1" 200 1528
    192.168.1.118 - - [27/Jan/2016 17:40:31] "GET /css/base.css HTTP/1.1" 200 1118

For more information about options use -h to get help, including
information about how to ensure that SSL certificates are verified.  You
can also group settings together into a json file to make it easier to
switch between configurations.

A simple settings file might look like this:

    {
    "WSGIApp": {
        "port": 8080,
        "static": "static",
        "private": "private"
        },
    "DemoApp": {
        "customer_id": "123456",
        "password": "secret"
        }
    }

You can then run:

    $ python dodata_demo.py --settings=settings.json

Warning: paths in settings files are resolved relative to the settings
file itself.

    
