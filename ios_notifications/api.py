from django.http import HttpResponse
from django.utils import simplejson as json
from ios_notifications.models import Device, APNService


def register_device(request, **kwargs):
    if request.method == 'POST':
        if APNService.objects.filter(pk=kwargs['service__id']).exists():
            device, created = Device.objects.get_or_create(**kwargs)
            if not created:
                device.is_active = True
                device.save()
            response = {'token': device.token, 'service': device.service.id,
                        'success': True, 'is_new': created}
        else:
            response = {'error': 'Service with id %d does not exist' % int(kwargs['service__id'])}
    else:
        response = {'error': 'request method should be POST'}
    return HttpResponse(json.dumps(response), mimetype='application/json')
