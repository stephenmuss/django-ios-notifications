# -*- coding: utf-8 -*-
import socket
import struct
import errno
import json
from binascii import hexlify, unhexlify

from django.db import models

try:
    from django.utils.timezone import now as dt_now
except ImportError:
    import datetime
    dt_now = datetime.datetime.now

from django_fields.fields import EncryptedCharField
import OpenSSL

try:
    import gevent_openssl
    GEVENT_OPEN_SSL=True
except:
    GEVENT_OPEN_SSL=False

from .exceptions import NotificationPayloadSizeExceeded, InvalidPassPhrase
from .settings import get_setting


class BaseService(models.Model):
    """
    A base service class intended to be subclassed.
    """
    name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    PORT = 0  # Should be overriden by subclass
    connection = None

    def _connect(self, certificate, private_key, passphrase=None):
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
        context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
        context.use_certificate(cert)
        context.use_privatekey(pkey)
        if GEVENT_OPEN_SSL:
            self.connection = gevent_openssl.SSL.Connection(context, sock)
        else:
            self.connection = OpenSSL.SSL.Connection(context, sock)
        self.connection.connect((self.hostname, self.PORT))
        self.connection.set_connect_state()
        self.connection.do_handshake()

    def _disconnect(self):
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
    passphrase = EncryptedCharField(
        null=True, blank=True, help_text='Passphrase for the private key',
        block_type='MODE_CBC')

    PORT = 2195
    fmt = '!cH32sH%ds'

    def _connect(self):
        """
        Establishes an encrypted SSL socket connection to the service.
        After connecting the socket can be written to or read from.
        """
        return super(APNService, self)._connect(self.certificate, self.private_key, self.passphrase)

    def push_notification_to_devices(self, notification, devices=None, chunk_size=100):
        """
        Sends the specific notification to devices.
        if `devices` is not supplied, all devices in the `APNService`'s device
        list will be sent the notification.
        """
        if devices is None:
            devices = self.device_set.filter(is_active=True)
        self._write_message(notification, devices, chunk_size)

    def _write_message(self, notification, devices, chunk_size):
        """
        Writes the message for the supplied devices to
        the APN Service SSL socket.
        """
        if not isinstance(notification, Notification):
            raise TypeError('notification should be an instance of ios_notifications.models.Notification')

        if not isinstance(chunk_size, int) or chunk_size < 1:
            raise ValueError('chunk_size must be an integer greater than zero.')

        payload = notification.payload

        # Split the devices into manageable chunks.
        # Chunk sizes being determined by the `chunk_size` arg.
        device_length = devices.count() if isinstance(devices, models.query.QuerySet) else len(devices)
        chunks = [devices[i:i + chunk_size] for i in xrange(0, device_length, chunk_size)]

        for index in xrange(len(chunks)):
            chunk = chunks[index]
            self._connect()

            for device in chunk:
                if not device.is_active:
                    continue
                try:
                    self.connection.send(self.pack_message(payload, device))
                except (OpenSSL.SSL.WantWriteError, socket.error) as e:
                    if isinstance(e, socket.error) and isinstance(e.args, tuple) and e.args[0] != errno.EPIPE:
                        raise e  # Unexpected exception, raise it.
                    self._disconnect()
                    i = chunk.index(device)
                    self.set_devices_last_notified_at(chunk[:i])
                    # Start again from the next device.
                    # We start from the next device since
                    # if the device no longer accepts push notifications from your app
                    # and you send one to it anyways, Apple immediately drops the connection to your APNS socket.
                    # http://stackoverflow.com/a/13332486/1025116
                    self._write_message(notification, chunk[i + 1:], chunk_size)

            self._disconnect()

            self.set_devices_last_notified_at(chunk)

        if notification.pk or notification.persist:
            notification.last_sent_at = dt_now()
            notification.save()

    def set_devices_last_notified_at(self, devices):
        # Rather than do a save on every object,
        # fetch another queryset and use it to update
        # the devices in a single query.
        # Since the devices argument could be a sliced queryset
        # we can't rely on devices.update() even if devices is
        # a queryset object.
        Device.objects.filter(pk__in=[d.pk for d in devices]).update(last_notified_at=dt_now())

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
    message = models.CharField(max_length=2048, blank=True, help_text='Alert message to display to the user. Leave empty if no alert should be displayed to the user.')
    badge = models.PositiveIntegerField(null=True, blank=True, help_text='New application icon badge number. Set to None if the badge number must not be changed.')
    silent = models.NullBooleanField(null=True, blank=True, help_text='set True to send a silent notification')
    sound = models.CharField(max_length=30, blank=True, help_text='Name of the sound to play. Leave empty if no sound should be played.')
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    custom_payload = models.CharField(max_length=240, blank=True, help_text='JSON representation of an object containing custom payload.')
    loc_payload = models.CharField(max_length=240, blank=True, help_text="JSON representation of an object containing the localization payload.")

    def __init__(self, *args, **kwargs):
        self.persist = get_setting('IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS')
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

    @property
    def loc_data(self):
        """
        The loc_data property is used to specify localization paramaters within the 'alert' aps key.
        https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/ApplePushService.html
        """
        return json.loads(self.loc_payload) if self.loc_payload else None

    def set_loc_data(self, loc_key, loc_args, action_loc_key=None):
        if not isinstance(loc_args, (list, tuple)):
            raise TypeError("loc_args must be a list or tuple.")

        loc_data = {
            "loc-key": unicode(loc_key),
            "loc-args": [unicode(a) for a in loc_args],
        }

        if action_loc_key:
            loc_data['action-loc-key'] = unicode(action_loc_key)

        self.loc_payload = json.dumps(loc_data)

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

        loc_data = self.loc_data
        if loc_data:
            aps['alert'] = loc_data
        elif self.message:
            aps['alert'] = self.message

        if self.badge is not None:
            aps['badge'] = self.badge
        if self.sound:
            aps['sound'] = self.sound
        if self.silent:
            aps['content-available'] = 1
        message = {'aps': aps}
        extra = self.extra
        if extra is not None:
            message.update(extra)
        payload = json.dumps(message, separators=(',', ':'), ensure_ascii=False).encode('utf8')
        return payload


class Device(models.Model):
    """
    Represents an iOS device with unique token.
    """
    token = models.CharField(max_length=64, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    service = models.ForeignKey(APNService)
    users = models.ManyToManyField(get_setting('AUTH_USER_MODEL'), blank=True, related_name='ios_devices')
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

        self.service.push_notification_to_devices(notification, [self])

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

    def _connect(self):
        """
        Establishes an encrypted socket connection to the feedback service.
        """
        return super(FeedbackService, self)._connect(self.apn_service.certificate, self.apn_service.private_key, self.apn_service.passphrase)

    def call(self):
        """
        Calls the feedback service and deactivates any devices the feedback service mentions.
        """
        self._connect()
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
        finally:
            self._disconnect()
        devices = Device.objects.filter(token__in=device_tokens, service=self.apn_service)
        devices.update(is_active=False, deactivated_at=dt_now())
        return devices.count()

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'hostname')
