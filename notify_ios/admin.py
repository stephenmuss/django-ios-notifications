from django.contrib import admin
from notify_ios.models import Device, Notification, APNService


admin.site.register(Device)
admin.site.register(Notification)
admin.site.register(APNService)
