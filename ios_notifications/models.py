# -*- coding: utf-8 -*-
import socket
import struct
import errno
from binascii import hexlify, unhexlify
import datetime
import json

from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


from django_fields.fields import EncryptedCharField
from django.conf import settings

import OpenSSL


class NotificationPayloadSizeExceeded(Exception):
    def __init__(self, message='The notification maximum payload size of 256 bytes was exceeded'):
        super(NotificationPayloadSizeExceeded, self).__init__(message)


class NotConnectedException(Exception):
    def __init__(self, message='You must open a socket connection before writing a message'):
        super(NotConnectedException, self).__init__(message)


class InvalidPassPhrase(Exception):
    def __init__(self, message='The passphrase for the private key appears to be invalid'):
        super(InvalidPassPhrase, self).__init__(message)


class BaseService(models.Model):
    """
    A base service class intended to be subclassed.
    """
    name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    PORT = 0  # Should be overriden by subclass
    connection = None

    def connect(self, certificate, private_key, passphrase=None):
        """
        Establishes an encrypted SSL socket connection to the service.
        After connecting the socket can be written to or read from.
        """
        # ssl in Python < 3.2 does not support certificates/keys as strings.
        # See http://bugs.python.org/issue3823
        # Therefore pyOpenSSL which lets us do this is a dependancy.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
        args = [OpenSSL.crypto.FILETYPE_PEM, private_key]
        if passphrase is not None:
            args.append(str(passphrase))
        try:
            pkey = OpenSSL.crypto.load_privatekey(*args)
        except OpenSSL.crypto.Error:
            raise InvalidPassPhrase
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
            if getattr(settings, 'DEBUG', False):
                print e, e.__class__
        return False

    def disconnect(self):
        """
        Closes the SSL socket connection.
        """
        if self.connection is not None:
            self.connection.shutdown()
            self.connection.close()

    class Meta:
        abstract = True


class APNService(BaseService):
    """
    Represents an Apple Notification Service either for live
    or sandbox notifications.

    `private_key` is optional if both the certificate and key are provided in
    `certificate`.
    """
    certificate = models.TextField()
    private_key = models.TextField()
    passphrase = EncryptedCharField(null=True, blank=True, help_text='Passphrase for the private key')

    PORT = 2195
    fmt = '!cH32sH%ds'

    def connect(self):
        """
        Establishes an encrypted SSL socket connection to the service.
        After connecting the socket can be written to or read from.
        """
        return super(APNService, self).connect(self.certificate, self.private_key, self.passphrase)

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

    def _write_message(self, notification, devices):
        """
        Writes the message for the supplied devices to
        the APN Service SSL socket.
        """
        if not isinstance(notification, Notification):
            raise TypeError('notification should be an instance of ios_notifications.models.Notification')

        if self.connection is None:
            if not self.connect():
                return

        payload = notification.payload

        for device in devices:
            if not device.is_active:
                continue
            try:
                self.connection.send(self.pack_message(payload, device))
            except (OpenSSL.SSL.WantWriteError, socket.error) as e:
                if isinstance(e, socket.error) and isinstance(e.args, tuple) and e.args[0] != errno.EPIPE:
                    raise  # Unexpected exception, raise it.
                self.disconnect()
                i = devices.index(device)
                self.set_devices_last_notified_at(devices[:i])
                # Start again from the next device.
                # We start from the next device since
                # if the device no longer accepts push notifications from your app
                # and you send one to it anyways, Apple immediately drops the connection to your APNS socket.
                # http://stackoverflow.com/a/13332486/1025116
                return self._write_message(notification, devices[i + 1:]) if self.connect() else None

        self.set_devices_last_notified_at(devices)

        if notification.pk or notification.persist:
            notification.last_sent_at = datetime.datetime.now()
            notification.save()

    def set_devices_last_notified_at(self, devices):
        if isinstance(devices, models.query.QuerySet):
            devices.update(last_notified_at=datetime.datetime.now())
        else:
            # Rather than do a save on every object
            # fetch another queryset and use it to update
            # the devices in a single query.
            Device.objects.filter(pk__in=[d.pk for d in devices]).update(last_notified_at=datetime.datetime.now())

    def pack_message(self, payload, device):
        """
        Converts a notification payload into binary form.
        """
        if len(payload) > 256:
            raise NotificationPayloadSizeExceeded
        if not isinstance(device, Device):
            raise TypeError('device must be an instance of ios_notifications.models.Device')

        msg = struct.pack(self.fmt % len(payload), chr(0), 32, unhexlify(device.token), len(payload), payload)
        return msg

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'hostname')


class Notification(models.Model):
    """
    Represents a notification which can be pushed to an iOS device.
    """
    service = models.ForeignKey(APNService)
    message = models.CharField(max_length=200, blank=True, help_text='Alert message to display to the user. Leave empty if no alert should be displayed to the user.')
    badge = models.PositiveIntegerField(null=True, blank=True, help_text='New application icon badge number. Set to None if the badge number must not be changed.')
    sound = models.CharField(max_length=30, blank=True, help_text='Name of the sound to play. Leave empty if no sound should be played.')
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    custom_payload = models.CharField(max_length=240, blank=True, help_text='JSON representation of an object containing custom payload.')

    def __init__(self, *args, **kwargs):
        self.persist = getattr(settings, 'IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS', True)
        super(Notification, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'%s%s%s' % (self.message, ' ' if self.message and self.custom_payload else '', self.custom_payload)

    @property
    def extra(self):
        """
        The extra property is used to specify custom payload values
        outside the Apple-reserved aps namespace
        http://developer.apple.com/library/mac/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/ApplePushService/ApplePushService.html#//apple_ref/doc/uid/TP40008194-CH100-SW1
        """
        return json.loads(self.custom_payload) if self.custom_payload else None

    @extra.setter
    def extra(self, value):
        if value is None:
            self.custom_payload = ''
        else:
            if not isinstance(value, dict):
                raise TypeError('must be a valid Python dictionary')
            self.custom_payload = json.dumps(value)  # Raises a TypeError if can't be serialized

    def push_to_all_devices(self):
        """
        Pushes this notification to all active devices using the
        notification's related APN service.
        """
        self.service.push_notification_to_devices(self)

    def is_valid_length(self):
        """
        Determines if a notification payload is a valid length.

        returns bool
        """
        return len(self.payload) <= 256

    @property
    def payload(self):
        aps = {}
        if self.message:
            aps['alert'] = self.message
        if self.badge is not None:
            aps['badge'] = self.badge
        if self.sound:
            aps['sound'] = self.sound
        message = {'aps': aps}
        extra = self.extra
        if extra is not None:
            message.update(extra)
        payload = json.dumps(message, separators=(',', ':'))
        return payload


class Device(models.Model):
    """
    Represents an iOS device with unique token.
    """
    token = models.CharField(max_length=64, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    service = models.ForeignKey(APNService)
    users = models.ManyToManyField(User, null=True, blank=True, related_name='ios_devices')
    added_at = models.DateTimeField(auto_now_add=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    platform = models.CharField(max_length=30, blank=True, null=True)
    display = models.CharField(max_length=30, blank=True, null=True)
    os_version = models.CharField(max_length=20, blank=True, null=True)

    def push_notification(self, notification):
        """
        Pushes a ios_notifications.models.Notification instance to an the device.
        For more details see http://developer.apple.com/library/mac/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/ApplePushService/ApplePushService.html
        """
        if not isinstance(notification, Notification):
            raise TypeError('notification should be an instance of ios_notifications.models.Notification')

        notification.service.push_notification_to_devices(notification, [self])

    def __unicode__(self):
        return self.token

    class Meta:
        unique_together = ('token', 'service')


class FeedbackService(BaseService):
    """
    The service provided by Apple to inform you of devices which no longer have your app installed
    and to which notifications have failed a number of times. Use this class to check the feedback
    service and deactivate any devices it informs you about.

    https://developer.apple.com/library/ios/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/CommunicatingWIthAPS/CommunicatingWIthAPS.html#//apple_ref/doc/uid/TP40008194-CH101-SW3
    """
    apn_service = models.ForeignKey(APNService)

    PORT = 2196

    fmt = '!lh32s'

    def connect(self):
        """
        Establishes an encrypted socket connection to the feedback service.
        """
        return super(FeedbackService, self).connect(self.apn_service.certificate, self.apn_service.private_key)

    def call(self):
        """
        Calls the feedback service and deactivates any devices the feedback service mentions.
        """
        if self.connect():
            device_tokens = []
            try:
                while True:
                    data = self.connection.recv(38)  # 38 being the length in bytes of the binary format feedback tuple.
                    timestamp, token_length, token = struct.unpack(self.fmt, data)
                    device_token = hexlify(token)
                    device_tokens.append(device_token)
            except OpenSSL.SSL.ZeroReturnError:
                # Nothing to receive
                pass
            devices = Device.objects.filter(token__in=device_tokens, service=self.apn_service)
            devices.update(is_active=False, deactivated_at=datetime.datetime.now())
            self.disconnect()
            return devices.count()

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'hostname')
