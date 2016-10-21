# -*- coding: utf-8 -*-

from django.conf.urls import url
from .api import routes

urlpatterns = [
    url(r'^device/$', routes.device, name='ios-notifications-device-create'),
    url(r'^device/(?P<token>\w+)/(?P<service__id>\d+)/$', routes.device, name='ios-notifications-device'),
]
