from django.contrib.auth import authenticate
from ios_notifications.http import JSONResponse
from django.conf import settings
import binascii


class InvalidAuthenticationType(Exception):
    pass


# TODO: OAuth
VALID_AUTH_TYPES = ('AuthBasic', 'AuthBasicIsStaff', 'AuthNone')


def api_authentication_required(func):
    """
    Check the value of IOS_NOTIFICATIONS_AUTHENTICATION in settings
    and authenticate the request user appropriately.
    """
    def wrapper(request, *args, **kwargs):
        AUTH_TYPE = getattr(settings, 'IOS_NOTIFICATIONS_AUTHENTICATION', None)
        if AUTH_TYPE is None or AUTH_TYPE not in VALID_AUTH_TYPES:
            raise InvalidAuthenticationType('IOS_NOTIFICATIONS_AUTHENTICATION must be specified in your settings.py file.\
                    Valid options are "AuthBasic", "AuthBasicIsStaff" or "AuthNone"')
        # Basic Authorization
        elif AUTH_TYPE == 'AuthBasic' or AUTH_TYPE == 'AuthBasicIsStaff':
            if 'HTTP_AUTHORIZATION' in request.META:
                auth_type, encoded_user_password = request.META['HTTP_AUTHORIZATION'].split(' ')
                try:
                    userpass = encoded_user_password.decode('base64')
                except binascii.Error:
                    return JSONResponse({'error': 'invalid base64 encoded header'}, status=401)
                try:
                    username, password = userpass.split(':')
                except ValueError:
                    return JSONResponse({'error': 'malformed Authorization header'}, status=401)
                user = authenticate(username=username, password=password)
                if user is not None:
                    if AUTH_TYPE == 'AuthBasic' or user.is_staff:
                        return func(request, *args, **kwargs)
                return JSONResponse({'error': 'authentication error'}, status=401)
            return JSONResponse({'error': 'Authorization header not set'}, status=401)

        # AuthNone: No authorization.
        return func(request, *args, **kwargs)
    return wrapper
