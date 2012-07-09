# -*- coding: utf-8 -*-
import subprocess
import time
import struct
import os

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils import simplejson as json
from django.http import HttpResponseNotAllowed
from django.conf import settings

from ios_notifications.models import APNService, Device, Notification, NotificationPayloadSizeExceeded
from ios_notifications.http import JSONResponse
from ios_notifications.utils import generate_cert_and_pkey
from ios_notifications.forms import APNServiceForm

TOKEN = '0fd12510cfe6b0a4a89dc7369c96df956f991e66131dab63398734e8000d0029'
TEST_PEM = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test.pem'))

SSL_SERVER_COMMAND = ('openssl', 's_server', '-accept', '2195', '-cert', TEST_PEM)


class APNServiceTest(TestCase):
    def setUp(self):
        self.test_server_proc = subprocess.Popen(SSL_SERVER_COMMAND, stdout=subprocess.PIPE)
        time.sleep(0.5)  # Wait for test server to be started

        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='test-service', hostname='127.0.0.1',
                                                 certificate=cert, private_key=key)

        self.device = Device.objects.create(token=TOKEN, service=self.service)
        self.notification = Notification.objects.create(message='Test message', service=self.service)

    def test_connection_to_remote_apn_host(self):
        self.assertTrue(self.service.connect())
        self.service.disconnect()

    def test_invalid_payload_size(self):
        n = Notification(message='.' * 260)
        self.assertRaises(NotificationPayloadSizeExceeded, self.service.get_payload, n)

    def test_payload_packed_correctly(self):
        fmt = self.service.fmt
        payload = self.service.get_payload(self.notification)
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

    def tearDown(self):
        self.test_server_proc.kill()


class APITest(TestCase):

    def setUp(self):
        self.service = APNService.objects.create(name='sandbox', hostname='gateway.sandbox.push.apple.com')
        self.device_token = TOKEN
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.AUTH = getattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'NotSpecified')
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthNone')
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

    def tearDown(self):
        if self.AUTH == 'NotSpecified':
            del settings.IOS_NOTIFICATIONS_AUTHENTICATION
        else:
            setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', self.AUTH)


class AuthenticationDecoratorTestAuthBasic(TestCase):
    def setUp(self):
        self.service = APNService.objects.create(name='sandbox', hostname='gateway.sandbox.push.apple.com')
        self.device_token = TOKEN
        self.user_password = 'abc123'
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.user.set_password(self.user_password)
        self.user.is_staff = True
        self.user.save()

        self.AUTH = getattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'NotSpecified')
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        self.device = Device.objects.create(service=self.service, token='0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029')

    def test_basic_authorization_request(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        resp = self.client.get(url, {}, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 200)

    def test_basic_authorization_request_invalid_credentials(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        user_pass = '%s:%s' % (self.user.username, 'invalidpassword')
        auth_header = 'Basic %s' % user_pass.encode('base64')
        url = reverse('ios-notifications-device-create')
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('authentication error' in resp.content)

    def test_basic_authorization_missing_header(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasic')
        url = reverse('ios-notifications-device-create')
        resp = self.client.get(url)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('Authorization header not set' in resp.content)

    def test_invalid_authentication_type(self):
        from ios_notifications.decorators import InvalidAuthenticationType
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthDoesNotExist')
        url = reverse('ios-notifications-device-create')
        self.assertRaises(InvalidAuthenticationType, self.client.get, url)

    def test_basic_authorization_is_staff(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasicIsStaff')
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        self.user.is_staff = True
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 200)

    def test_basic_authorization_is_staff_with_non_staff_user(self):
        setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', 'AuthBasicIsStaff')
        kwargs = {'token': self.device.token, 'service__id': self.device.service.id}
        url = reverse('ios-notifications-device', kwargs=kwargs)
        user_pass = '%s:%s' % (self.user.username, self.user_password)
        auth_header = 'Basic %s' % user_pass.encode('base64')
        self.user.is_staff = False
        self.user.save()
        resp = self.client.get(url, HTTP_AUTHORIZATION=auth_header)
        self.assertEquals(resp.status_code, 401)
        self.assertTrue('authentication error' in resp.content)

    def tearDown(self):
        if self.AUTH == 'NotSpecified':
            del settings.IOS_NOTIFICATIONS_AUTHENTICATION
        else:
            setattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', self.AUTH)


class NotificationTest(TestCase):
    def setUp(self):
        self.test_server_proc = subprocess.Popen(SSL_SERVER_COMMAND, stdout=subprocess.PIPE)
        time.sleep(0.5)
        cert, key = generate_cert_and_pkey()
        self.service = APNService.objects.create(name='service', hostname='127.0.0.1',
                                                 private_key=key, certificate=cert)
        self.service.PORT = 2195  # For ease of use simply change port to default port in test_server

        self.notification = Notification.objects.create(service=self.service, message='Test message')

    def test_invalid_length(self):
        long_message = '.' * 260
        self.assertFalse(Notification.is_valid_length(long_message))

    def test_valid_length(self):
        self.assertTrue(Notification.is_valid_length(self.notification.message))

    def test_push_to_all_devices(self):
        self.assertIsNone(self.notification.last_sent_at)
        self.notification.push_to_all_devices()
        self.assertIsNotNone(self.notification.last_sent_at)

    def tearDown(self):
        self.test_server_proc.kill()
