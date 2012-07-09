from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.core import serializers
from django.utils import simplejson as json


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
