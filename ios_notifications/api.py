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
    allowed_methods = ('GET', 'POST', 'PUT')

    def get(self, request, **kwargs):
        device = get_object_or_404(Device, **kwargs)
        return JSONResponse(device)

    def post(self, request, **kwargs):
        devices = Device.objects.filter(token=request.POST.get('token'), service__id=int(request.POST.get('service', 0)))
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
        device = get_object_or_404(Device, **kwargs)
        if 'users' in request.PUT:
            try:
                device.users.add(*request.PUT['users'])
            except ValueError:
                pass
            del request.PUT['users']
        for key, value in request.PUT.items():
            setattr(device, key, value)
        device.save()
        return JSONResponse(device)


class Router(object):
    def __init__(self):
        self.device = DeviceResource().route

routes = Router()
