from django.conf import settings

defaults = {
            # Default user model if no custom user model is specified
            'AUTH_USER_MODEL': 'auth.User',

            # Whether Notification model instances are automatically saved when they are pushed.
            # Expected values: True, False.
            'IOS_NOTIFICATIONS_PERSIST_NOTIFICATIONS': True,

            # Indicates the type of authentication required by an API endpoint.
            # Expected values: one of 'AuthNone', 'AuthBasic', 'AuthBasicIsStaff'.
            # This setting MUST be set for the API to be usable.
            'IOS_NOTIFICATIONS_AUTHENTICATION': None,
            }

def get_setting(name):
    # try to get the user setting by the given name, providing an ios_notifications default otherwise
    # by design, this will crash if 'name' is neither a user setting nor a vlaid ios_notifications setting
    return getattr(settings, name, defaults[name])
