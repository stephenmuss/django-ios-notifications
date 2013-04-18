# -*- coding: utf-8 -*-

from optparse import make_option
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from ios_notifications.models import Notification, APNService


class Command(BaseCommand):
    help = 'Create and immediately send a push notification to iOS devices'
    option_list = BaseCommand.option_list + (
        make_option('--message',
                    help='The main message to be sent in the notification',
                    dest='message',
                    default=''),
        make_option('--badge',
                    help='The badge number of the notification',
                    dest='badge',
                    default=None),
        make_option('--sound',
                    help='The sound for the notification',
                    dest='sound',
                    default=''),
        make_option('--service',
                    help='The id of the APN Service to send this notification through',
                    dest='service',
                    default=None),
        make_option('--extra',
                    help='Custom notification payload values as a JSON dictionary',
                    dest='extra',
                    default=None),
        make_option('--persist',
                    help='Save the notification in the database after pushing it.',
                    action='store_true',
                    dest='persist',
                    default=None),
        make_option('--no-persist',
                    help='Prevent saving the notification in the database after pushing it.',
                    action='store_false',
                    dest='persist'),  # Note: same dest as --persist; they are mutually exclusive
        make_option('--batch-size',
                    help='Notifications are sent to devices in batches via the APN Service. This controls the batch size. Default is 100.',
                    dest='chunk_size',
                    default=100),
    )

    def handle(self, *args, **options):
        if options['service'] is None:
            raise CommandError('The --service option is required')
        try:
            service_id = int(options['service'])
        except ValueError:
            raise CommandError('The --service option should pass an id in integer format as its value')
        if options['badge'] is not None:
            try:
                options['badge'] = int(options['badge'])
            except ValueError:
                raise CommandError('The --badge option should pass an integer as its value')
        try:
            service = APNService.objects.get(pk=service_id)
        except APNService.DoesNotExist:
            raise CommandError('APNService with id %d does not exist' % service_id)

        message = options['message']
        extra = options['extra']

        if not message and not extra:
            raise CommandError('To send a notification you must provide either the --message or --extra option.')

        notification = Notification(message=options['message'],
                                    badge=options['badge'],
                                    service=service,
                                    sound=options['sound'])

        if options['persist'] is not None:
            notification.persist = options['persist']

        if extra is not None:
            notification.extra = json.loads(extra)

        try:
            chunk_size = int(options['chunk_size'])
        except ValueError:
            raise CommandError('The --batch-size option should be an integer value.')

        if not notification.is_valid_length():
            raise CommandError('Notification exceeds the maximum payload length. Try making your message shorter.')

        service.push_notification_to_devices(notification, chunk_size=chunk_size)
        if 'test' not in sys.argv:
            self.stdout.write('Notification pushed successfully\n')
