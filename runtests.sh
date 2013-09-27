#!/bin/bash

pushd .
cd test/testapp
python manage.py test ios_notifications
STATUS=$?
popd
exit $STATUS
