# -*- coding: utf-8 -*-

from django.http import HttpResponse, HttpResponseNotAllowed, QueryDict
from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.core import serializers
from django.db.models.query import QuerySet

from ios_notifications.models import Device
from ios_notifications.forms import DeviceForm


class HttpResponseNotImplemented(HttpResponse):
    status_code = 501


class JSONResponse(HttpResponse):
    """
    A subclass of django.http.HttpResponse which serializes its content
    and returns a response with an application/json mimetype.
    """
    def __init__(self, content=None, content_type=None, status=None, mimetype='application/json'):
        content = self.serialize(content) if content is not None else ''
        super(JSONResponse, self).__init__(content, content_type, status, mimetype)

    def serialize(self, obj):
        json_s = serializers.get_serializer('json')()
        if isinstance(obj, QuerySet):
            return json_s.serialize(obj)
        elif isinstance(obj, dict):
            return json.dumps(obj)

        serialized_list = json_s.serialize([obj])
        m = json.loads(serialized_list)[0]
        return json.dumps(m)


class BaseResource(object):
    """
    The base class for any API Resources.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    @csrf_exempt
    def route(self, request, **kwargs):
        method = request.method
        if method in self.allowed_methods:
            if hasattr(self, method.lower()):
                if method == 'PUT':
                    request.PUT = QueryDict(request.raw_post_data)
                return getattr(self, method.lower())(request, **kwargs)

            return HttpResponseNotImplemented()

        return HttpResponseNotAllowed(self.allowed_methods)


class DeviceResource(BaseResource):
    """
    The API resource for ios_notifications.models.Device.

    Allowed HTTP methods are GET, POST and PUT.
    """
    allowed_methods = ('GET', 'POST', 'PUT')

    def get(self, request, **kwargs):
        """
        Returns an HTTP response with the device in serialized JSON format.
        The device token and device service are expected as the keyword arguments
        supplied by the URL.

        If the device does not exist a 404 will be raised.
        """
        device = get_object_or_404(Device, **kwargs)
        return JSONResponse(device)

    def post(self, request, **kwargs):
        """
        Creates a new device or updates an existing one to `is_active=True`.
        Expects two non-options POST parameters: `token` and `service`.
        """
        devices = Device.objects.filter(token=request.POST.get('token'),
                                        service__id=int(request.POST.get('service', 0)))
        if devices.exists():
            device = devices.get()
            device.is_active = True
            device.save()
            return JSONResponse(device)
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save()
            return JSONResponse(device, status=201)
        return JSONResponse(form.errors, status=400)

    def put(self, request, **kwargs):
        """
        Updates an existing device.

        If the device does not exist a 404 will be raised.

        The device token and device service are expected as the keyword arguments
        supplied by the URL.

        Any attributes to be updated should be supplied as parameters in the request
        body of any HTTP PUT request.
        """
        device = get_object_or_404(Device, **kwargs)
        # TODO: Transaction
        if 'users' in request.PUT:
            try:
                device.users.add(*request.PUT['users'])
                device.users.remove(*[u.id for u in device.users.exclude(id__in=request.PUT['users'])])
            except ValueError:
                pass
            del request.PUT['users']
        for key, value in request.PUT.items():
            setattr(device, key, value)
        device.save()
        return JSONResponse(device)


class Router(object):
    """
    A simple class for handling URL routes.
    """
    def __init__(self):
        self.device = DeviceResource().route

routes = Router()
