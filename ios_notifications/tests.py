# -*- coding: utf-8 -*-

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils import simplejson as json
from django.http import HttpResponseNotAllowed

from ios_notifications.models import APNService, Device
from ios_notifications.api import JSONResponse


class APITest(TestCase):
    fixtures = ['initial_test_data.json']

    def setUp(self):
        self.service = APNService.objects.get(name='sandbox')
        self.device_token = '0fd12510cfe6b0a4a89dc7369c96df956f991e66131dab63398734e8000d0029'
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.device = Device.objects.get(service=self.service)

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
