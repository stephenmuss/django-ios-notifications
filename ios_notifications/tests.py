# -*- coding: utf-8 -*-
import subprocess
import struct
import os
import json
import uuid
import StringIO

import django
from django.test import TestCase

try:
    from django.test.utils import override_settings
except ImportError:
    from override_settings import override_settings

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseNotAllowed
from django.core import management

try:
    from django.utils.timezone import now as dt_now
except ImportError:
    import datetime
    dt_now = datetime.datetime.now

from .models import APNService, Device, Notification, NotificationPayloadSizeExceeded
from .http import JSONResponse
from .utils import generate_cert_and_pkey
from .forms import APNServiceForm
from .settings import get_setting

TOKEN = '0fd12510cfe6b0a4a89dc7369c96df956f991e66131dab63398734e8000d0029'
TEST_PEM = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test.pem'))

SSL_SERVER_COMMAND = ('openssl', 's_server', '-accept', '2195', '-cert', TEST_PEM)


class UseMockSSLServerMixin(object):
    @classmethod
    def setUpClass(cls):
        super(UseMockSSLServerMixin, cls).setUpClass()
        cls.test_server_proc = subprocess.Popen(SSL_SERVER_COMMAND, stdout=subprocess.PIPE)

    @classmethod
    def tearDownClass(cls):
        cls.test_server_proc.kill()
        super(UseMockSSLServerMixin, cls).tearDownClass()


class APNServiceTest(UseMockSSLServerMixin, TestCase):
    def setUp(self):
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='test-service', hostname='127.0.0.1',
                                                 certificate=cert, private_key=key)

        self.device = Device.objects.create(token=TOKEN, service=self.service)
        self.notification = Notification.objects.create(message='Test message', service=self.service)

    def test_invalid_payload_size(self):
        n = Notification(message='.' * 250)
        self.assertRaises(NotificationPayloadSizeExceeded, self.service.pack_message, n.payload, self.device)

    def test_payload_packed_correctly(self):
        fmt = self.service.fmt
        payload = self.notification.payload
        msg = self.service.pack_message(payload, self.device)
        unpacked = struct.unpack(fmt % len(payload), msg)
        self.assertEqual(unpacked[-1], payload)

    def test_pack_message_with_invalid_device(self):
        self.assertRaises(TypeError, self.service.pack_message, None)

    def test_can_connect_and_push_notification(self):
        self.assertIsNone(self.notification.last_sent_at)
        self.assertIsNone(self.device.last_notified_at)
        self.service.push_notification_to_devices(self.notification, [self.device])
        self.assertIsNotNone(self.notification.last_sent_at)
        self.device = Device.objects.get(pk=self.device.pk)  # Refresh the object with values from db
        self.assertIsNotNone(self.device.last_notified_at)

    def test_create_with_passphrase(self):
        cert, key = generate_cert_and_pkey(as_string=True, passphrase='pass')
        form = APNServiceForm({'name': 'test', 'hostname': 'localhost', 'certificate': cert, 'private_key': key, 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())

    def test_create_with_invalid_passphrase(self):
        cert, key = generate_cert_and_pkey(as_string=True, passphrase='correct')
        form = APNServiceForm({'name': 'test', 'hostname': 'localhost', 'certificate': cert, 'private_key': key, 'passphrase': 'incorrect'})
        self.assertFalse(form.is_valid())
        self.assertTrue('passphrase' in form.errors)

    def test_pushing_notification_in_chunks(self):
        devices = []
        for i in xrange(10):
            token = uuid.uuid1().get_hex() * 2
            device = Device.objects.create(token=token, service=self.service)
            devices.append(device)

        started_at = dt_now()
        self.service.push_notification_to_devices(self.notification, devices, chunk_size=2)
        device_count = len(devices)
        self.assertEquals(device_count,
                          Device.objects.filter(last_notified_at__gte=started_at).count())


@override_settings(IOS_NOTIFICATIONS_AUTHENTICATION='AuthNone')
class APITest(UseMockSSLServerMixin, TestCase):
    urls = 'ios_notifications.urls'

    def setUp(self):
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='test-service', hostname='127.0.0.1',
                                                 certificate=cert, private_key=key)
        self.device_token = TOKEN
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.device = Device.objects.create(service=self.service, token='0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029')

    def test_register_device_invalid_params(self):
        """
        Test that sending a POST request to the device API
        without POST parameters `token` and `service` results
        in a 400 bad request response.
        """
        resp = self.client.post(reverse('ios-notifications-device-create'))
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(isinstance(resp, JSONResponse))
        content = json.loads(resp.content)
        keys = content.keys()
        self.assertTrue('token' in keys and 'service' in keys)

    def test_register_device(self):
        """
        Test a device is created when calling the API with the correct
        POST parameters.
        """
        resp = self.client.post(reverse('ios-notifications-device-create'),
                                {'token': self.device_token,
                                 'service': self.service.id})

        self.assertEqual(resp.status_code, 201)
        self.assertTrue(isinstance(resp, JSONResponse))
        content = resp.content
        device_json = json.loads(content)
        self.assertEqual(device_json.get('model'), 'ios_notifications.device')

    def test_disallowed_method(self):
        resp = self.client.delete(reverse('ios-notifications-device-create'))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(isinstance(resp, HttpResponseNotAllowed))

    def test_update_device(self):
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        resp = self.client.put(url, 'users=%d&platform=iPhone' % self.user.id,
                               content_type='application/x-www-form-urlencode')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(isinstance(resp, JSONResponse))
        device_json = json.loads(resp.content)
        self.assertEqual(device_json.get('pk'), self.device.id)
        self.assertTrue(self.user in self.device.users.all())

    def test_get_device_details(self):
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content
        device_json = json.loads(content)
        self.assertEqual(device_json.get('model'), 'ios_notifications.device')


class AuthenticationDecoratorTestAuthBasic(UseMockSSLServerMixin, TestCase):
    urls = 'ios_notifications.urls'

    def setUp(self):
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='test-service', hostname='127.0.0.1',
                                                 certificate=cert, private_key=key)
        self.device_token = TOKEN
        self.user_password = 'abc123'
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.user.set_password(self.user_password)
        self.user.is_staff = True
        self.user.save()
        self.device = Device.objects.create(service=self.service, token='0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029')

    @override_settings(IOS_NOTIFICATIONS_AUTHENTICATION='AuthBasic')
    def test_basic_authorization_request(self):
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        resp = self.client.get(url, {}, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 200)

    @override_settings(IOS_NOTIFICATIONS_AUTHENTICATION='AuthBasic')
    def test_basic_authorization_request_invalid_credentials(self):
        user_pass = '%s:%s' % (self.user.username, 'invalidpassword')
        auth_header = 'Basic %s' % user_pass.encode('base64')
        url = reverse('ios-notifications-device-create')
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('authentication error' in resp.content)

    @override_settings(IOS_NOTIFICATIONS_AUTHENTICATION='AuthBasic')
    def test_basic_authorization_missing_header(self):
        url = reverse('ios-notifications-device-create')
        resp = self.client.get(url)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('Authorization header not set' in resp.content)

    @override_settings(IOS_NOTIFICATIONS_AUTHENTICATION='AuthDoesNotExist')
    def test_invalid_authentication_type(self):
        from ios_notifications.decorators import InvalidAuthenticationType
        url = reverse('ios-notifications-device-create')
        self.assertRaises(InvalidAuthenticationType, self.client.get, url)

    @override_settings(IOS_NOTIFICATIONS_AUTHENTICATION=None)
    def test_no_authentication_type(self):
        from ios_notifications.decorators import InvalidAuthenticationType
        url = reverse('ios-notifications-device-create')
        self.assertRaises(InvalidAuthenticationType, self.client.get, url)

    @override_settings(IOS_NOTIFICATIONS_AUTHENTICATION='AuthBasicIsStaff')
    def test_basic_authorization_is_staff(self):
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        self.user.is_staff = True
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 200)

    @override_settings(IOS_NOTIFICATIONS_AUTHENTICATION='AuthBasicIsStaff')
    def test_basic_authorization_is_staff_with_non_staff_user(self):
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        self.user.is_staff = False
        self.user.save()
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('authentication error' in resp.content)


class NotificationTest(UseMockSSLServerMixin, TestCase):
    def setUp(self):
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='service', hostname='127.0.0.1',
                                                 private_key=key, certificate=cert)
        self.service.PORT = 2195  # For ease of use simply change port to default port in test_server
        self.custom_payload = json.dumps({"." * 10: "." * 50})
        self.notification = Notification.objects.create(service=self.service, message='Test message', custom_payload=self.custom_payload)

    def test_valid_length(self):
        self.notification.message = 'test message'
        self.assertTrue(self.notification.is_valid_length())

    def test_invalid_length(self):
        self.notification.message = '.' * 250
        self.assertFalse(self.notification.is_valid_length())

    def test_invalid_length_with_custom_payload(self):
        self.notification.message = '.' * 100
        self.notification.custom_payload = '{"%s":"%s"}' % ("." * 20, "." * 120)
        self.assertFalse(self.notification.is_valid_length())

    def test_extra_property_with_custom_payload(self):
        custom_payload = {"." * 10: "." * 50, "nested": {"+" * 10: "+" * 50}}
        self.notification.extra = custom_payload
        self.assertEqual(self.notification.custom_payload, json.dumps(custom_payload))
        self.assertEqual(self.notification.extra, custom_payload)
        self.assertTrue(self.notification.is_valid_length())

    def test_loc_data_payload(self):
        self.notification.set_loc_data('TEST_1', [1, 'ab', 1.2, 'CD'])
        self.notification.message = 'test message'
        loc_data = {'loc-key': 'TEST_1', 'loc-args': ['1', 'ab', '1.2', 'CD']}
        self.assertEqual(self.notification.loc_data, loc_data)
        self.assertTrue(self.notification.is_valid_length())
        p = self.notification.payload
        self.assertEqual(json.loads(p)['aps']['alert'], loc_data)

    def test_extra_property_not_dict(self):
        with self.assertRaises(TypeError):
            self.notification.extra = 111

    def test_extra_property_none(self):
        self.notification.extra = None
        self.assertEqual(self.notification.extra, None)
        self.assertEqual(self.notification.custom_payload, '')
        self.assertTrue(self.notification.is_valid_length())

    def test_push_to_all_devices_persist_existing(self):
        self.assertIsNone(self.notification.last_sent_at)
        self.notification.persist = False
        self.notification.push_to_all_devices()
        self.assertIsNotNone(self.notification.last_sent_at)

    def test_push_to_all_devices_persist_new(self):
        notification = Notification(service=self.service, message='Test message (new)')
        notification.persist = True
        notification.push_to_all_devices()
        self.assertIsNotNone(notification.last_sent_at)
        self.assertIsNotNone(notification.pk)

    def test_push_to_all_devices_no_persist(self):
        notification = Notification(service=self.service, message='Test message (new)')
        notification.persist = False
        notification.push_to_all_devices()
        self.assertIsNone(notification.last_sent_at)
        self.assertIsNone(notification.pk)


class ManagementCommandPushNotificationTest(UseMockSSLServerMixin, TestCase):
    def setUp(self):
        self.started_at = dt_now()
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='service', hostname='127.0.0.1',
                                                 private_key=key, certificate=cert)
        self.service.PORT = 2195
        self.device = Device.objects.create(token=TOKEN, service=self.service)

    def test_call_push_ios_notification_command_explicit_persist(self):
        msg = 'some message'
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0, 'persist': True})
        self.assertTrue(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    def test_call_push_ios_notification_command_explicit_no_persist(self):
        msg = 'some message'
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0, 'persist': False})
        self.assertFalse(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    @override_settings(IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS=True)
    def test_call_push_ios_notification_command_default_persist(self):
        msg = 'some message'
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0})
        self.assertTrue(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    @override_settings(IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS=False)
    def test_call_push_ios_notification_command_default_no_persist(self):
        msg = 'some message'
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0})
        self.assertFalse(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    @override_settings()
    def test_call_push_ios_notification_command_default_persist_not_specified(self):
        try:
            # making sure that IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS is not specified in app settings, otherwise this test means nothing
            del settings.IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS
        except AttributeError:
            pass
        msg = 'some message'
        management.call_command('push_ios_notification', **{'message': msg, 'service': self.service.id, 'verbosity': 0})
        self.assertTrue(Notification.objects.filter(message=msg, last_sent_at__gt=self.started_at).exists())
        self.assertTrue(self.device in Device.objects.filter(last_notified_at__gt=self.started_at))

    def test_either_message_or_extra_option_required(self):
        # In Django < 1.5 django.core.management.base.BaseCommand.execute
        # catches CommandError and raises SystemExit instead.
        exception = SystemExit if django.VERSION < (1, 5) else management.base.CommandError

        with self.assertRaises(exception):
            management.call_command('push_ios_notification', service=self.service.pk,
                                    verbosity=0, stderr=StringIO.StringIO())


class ManagementCommandCallFeedbackService(TestCase):
    pass


class DefaultSettings(TestCase):
    def test_persist_notifications_setting(self):
        self.assertEqual(True, get_setting('IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS'))

    def test_authentication_setting(self):
        self.assertEqual(None, get_setting('IOS_NOTIFICATIONS_AUTHENTICATION'))

    def test_auth_user_model(self):
        self.assertEqual('auth.User', get_setting('AUTH_USER_MODEL'))

    def test_invalid_setting(self):
        setting_name = '_THIS_SETTING_SHOULD_NOT_EXIST__________'
        with self.assertRaises(KeyError):
            get_setting(setting_name)
