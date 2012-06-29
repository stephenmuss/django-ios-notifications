from django.contrib import admin
from ios_notifications.models import Device, Notification, APNService


admin.site.register(Device)
admin.site.register(Notification)
admin.site.register(APNService)
