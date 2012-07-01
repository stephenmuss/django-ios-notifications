# -*- coding: utf-8 -*-
import socket
import OpenSSL
import struct
from binascii import unhexlify
import datetime

from django.db import models
from django.utils import simplejson as json


class NotificationPayloadSizeExceeded(Exception):
    message = 'The notification maximum payload size of 256 bytes was exceeded'


class NotConnectedException(Exception):
    message = 'You must open a socket connection before writing a message'


class APNService(models.Model):
    """
    Represents an Apple Notification Service either for live
    or sandbox notifications.

    `private_key` is optional if both the certificate and key are provided in
    `certificate`.
    """
    name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    certificate = models.TextField()
    private_key = models.TextField(null=True, blank=True)

    PORT = 2195
    connection = None
    fmt = '!cH32sH%ds'

    def push_notification_to_devices(self, notification, devices=None):
        """
        Sends the specific notification to devices.
        if `devices` is not supplied, all devices in the `APNService`'s device
        list will be sent the notification.
        """
        if devices is None:
            devices = self.device_set.filter(is_active=True)
        if self.connect():
            self._write_message(notification, devices)
            self.disconnect()

    def connect(self):
        # ssl in Python < 3.2 does not support certificates/keys as strings.
        # See http://bugs.python.org/issue3823
        # Therefore pyOpenSSL which lets us do this is a dependancy.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, self.certificate)
        pkey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, self.private_key)
        context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv3_METHOD)
        context.use_certificate(cert)
        context.use_privatekey(pkey)
        self.connection = OpenSSL.SSL.Connection(context, sock)
        self.connection.connect((self.hostname, self.PORT))
        self.connection.set_connect_state()
        try:
            self.connection.do_handshake()
            return True
        except Exception as e:
            print e, e.__class__
        return False

    def _write_message(self, notification, devices):
        if not isinstance(notification, Notification):
            raise TypeError('notification should be an instance of ios_notifications.models.Notification')

        if self.connection is None:
            if not self.connect():
                return

        aps = {'alert': notification.message}
        if notification.badge is not None:
            aps['badge'] = notification.badge
        if notification.sound is not None:
            aps['sound'] = notification.sound

        message = {'aps': aps}
        payload = json.dumps(message, separators=(',', ':'))

        if len(payload) > 256:
            raise NotificationPayloadSizeExceeded

        for device in devices:
            try:
                self.connection.send(self.pack_message(payload, device))
                device.last_notified_at = datetime.datetime.now()
            except OpenSSL.SSL.WantWriteError:
                self.disconnect()
                i = devices.index(device)
                if isinstance(devices, models.query.QuerySet):
                    devices.save()
                devices[:i].save()
                return self._write_message(notification, devices[i:]) if self.connect() else None
        if isinstance(devices, models.query.QuerySet):
            devices.save()
        notification.last_sent_at = datetime.datetime.now()
        notification.save()

    def pack_message(self, payload, device):
        if len(payload) > 256:
            raise NotificationPayloadSizeExceeded
        if not isinstance(device, Device):
            raise TypeError('device must be an instance of ios_notifications.models.Device')

        msg = struct.pack(self.fmt % len(payload), chr(0), 32, unhexlify(device.token), len(payload), payload)
        return msg

    def disconnect(self):
        if self.connection is not None:
            self.connection.shutdown()
            self.connection.close()

    def __unicode__(self):
        return u'APNService %s' % self.name


class Notification(models.Model):
    service = models.ForeignKey(APNService)
    message = models.CharField(max_length=200)
    badge = models.PositiveIntegerField(default=1, null=True)
    sound = models.CharField(max_length=30, null=True, default='default')
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    def push__all_devices(self):
        for device in Device.objects.filter(is_active=True):
            device.push_notification(self)

    def __unicode__(self):
        return u'Notification: %s' % self.message


class Device(models.Model):
    """
    Represents an iOS device with unique token.
    """
    token = models.CharField(max_length=64, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    def push_notification(self, notification):
        """
        Pushes a ios_notifications.models.Notification instance to an the device.
        For more details see http://developer.apple.com/library/mac/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/ApplePushService/ApplePushService.html
        """
        if not isinstance(notification, Notification):
            raise TypeError('notification should be an instance of ios_notifications.models.Notification')

        notification.service.push_notification_to_devices(notification, [self])
        self.save()

    def __unicode__(self):
        return u'Device %s' % self.token
