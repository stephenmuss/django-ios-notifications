from django.conf.urls.defaults import url, patterns

urlpatterns = patterns('ios_notifications',
    url(r'^device/(?P<token>\w+)/(?P<service__id>\d+)/$', 'api.device', name='ios-notifications-device'),)
