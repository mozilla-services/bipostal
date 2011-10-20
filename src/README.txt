bipostmap.py

    name mapping service for message addressees.

    RUN:
        $ python bipostmap.py --config=bipostal.ini

    postfix config:
        $ $EDITOR /etc/postfix/main.cf
        canonical_maps = tcp:localhost:9998

    requires:
        Redis

bipostal.py

    message reformatter

    RUN:
        $ python bipostal.py --config=bipostal.ini

    postfix config:
        $ $EDITOR /etc/postfix.main.cf

        
