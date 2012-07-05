# -*- coding: utf-8 -*-

from django.conf.urls.defaults import url, patterns
from ios_notifications.api import routes

urlpatterns = patterns('',
    url(r'^device/$', routes.device, name='ios-notifications-device-create'),
    url(r'^device/(?P<token>\w+)/(?P<service__id>\d+)/$', routes.device, name='ios-notifications-device'),
)
