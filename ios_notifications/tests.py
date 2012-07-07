# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import time
import struct

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils import simplejson as json
from django.http import HttpResponseNotAllowed

import OpenSSL

from ios_notifications.models import APNService, Device, Notification, NotificationPayloadSizeExceeded
from ios_notifications.api import JSONResponse
from ios_notifications.utils import generate_cert_and_pkey

TOKEN = '0fd12510cfe6b0a4a89dc7369c96df956f991e66131dab63398734e8000d0029'


class APNServiceTest(TestCase):
    def setUp(self):
        test_server_path = os.path.join(os.path.dirname(__file__), 'test_server.py')
        self.test_server_proc = subprocess.Popen((sys.executable, test_server_path), stdout=subprocess.PIPE)
        time.sleep(2)  # Wait for test server to be started

        cert, key = generate_cert_and_pkey()
        cert = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        key = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)
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

    def tearDown(self):
        self.test_server_proc.kill()


class APITest(TestCase):

    def setUp(self):
        self.service = APNService.objects.create(name='sandbox', hostname='gateway.sandbox.push.apple.com')
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


class NotificationTest(TestCase):
    def test_invalid_length(self):
        long_message = '.' * 260
        self.assertFalse(Notification.is_valid_length(long_message))

    def test_valid_length(self):
        msg = 'This is the message'
        self.assertTrue(Notification.is_valid_length(msg))
