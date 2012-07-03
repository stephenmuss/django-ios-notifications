from django.conf.urls.defaults import url, patterns

urlpatterns = patterns('ios_notifications',
    url(r'^register-device/(?P<token>\w+)/(?P<service__id>\d+)/$', 'api.register_device', name='ios-notifications-register-device'),
)
