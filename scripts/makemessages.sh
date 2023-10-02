#!/bin/sh

# Run this scrpit from "src" directory with `../scripts/makemessages.sh`.

# To generate compiled files just run `python manage.py compilemessages` from
# "src" directory.

# Space separeted list of django apps to translate.
APPS="main"

for app in $APPS;do
    cd $app && echo $app
    python ../manage.py makemessages -a
    cd ..
done
