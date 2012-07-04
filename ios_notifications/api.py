from django.http import HttpResponse
from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from ios_notifications.models import Device, APNService
from ios_notifications.forms import DeviceForm


@csrf_exempt
def device(request, **kwargs):
    if request.method in ('POST', 'PUT'):
        if APNService.objects.filter(pk=kwargs['service__id']).exists():
            device, created = Device.objects.get_or_create(**kwargs)
            if not created:
                device.is_active = True
                device.save()
            response = {'token': device.token, 'service': device.service.id,
                        'success': True, 'is_new': created}
            if request.method == 'PUT':
                try:
                    # FIXME: More elegant solution to updating and creating response
                    data = json.loads(request.raw_post_data)
                    data['token'] = kwargs['token']
                    data['service'] = kwargs['service__id']
                    form = DeviceForm(data, instance=device)
                    if form.is_valid():
                        form.save()
                        data = form.cleaned_data
                        data['users'] = [user.id for user in data['users']]
                        data['service'] = kwargs['service__id']
                        response = dict(response.items() + data.items())
                    else:
                        response = form.errors
                except ValueError:
                    response = {'error': 'Invalid request body. Must be in valid JSON format.'}
        else:
            response = {'error': 'Service with id %d does not exist' % int(kwargs['service__id'])}
    else:
        response = {'error': 'invalid request method'}

    return HttpResponse(json.dumps(response), mimetype='application/json')
