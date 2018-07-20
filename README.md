# Prerequisites

## Create API Key

You need an API Key which can be created here: <https://api.ovh.com/createToken/index.cgi?GET=/*&PUT=/*&POST=/*&DELETE=/*>

And it should have the following access rights:
* "GET", "/email/*"
* "POST". "/email/*"
* "DELETE". "/email/*"

## Python Dependencies

* pip install -r requirements.txt

or

* pip install ovh requests