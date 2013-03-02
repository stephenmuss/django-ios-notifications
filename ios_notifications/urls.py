# -*- coding: utf-8 -*-

try:
    from django.conf.urls import patterns, url
except ImportError:  # deprecated since Django 1.4
    from django.conf.urls.defaults import patterns, url

from .api import routes

urlpatterns = patterns('',
    url(r'^device/$', routes.device, name='ios-notifications-device-create'),
    url(r'^device/(?P<token>\w+)/(?P<service__id>\d+)/$', routes.device, name='ios-notifications-device'),
)
