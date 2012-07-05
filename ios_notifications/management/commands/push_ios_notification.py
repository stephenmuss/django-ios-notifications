# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from ios_notifications.models import Notification, APNService
from optparse import make_option

# TODO: argparse for Python 2.7


class Command(BaseCommand):
    help = 'Created and immediately send a push notification to iOS devices'
    option_list = BaseCommand.option_list + (
        make_option('--message',
            help='The main message to be sent in the notification',
            dest='message',
            default=None
        ),
        make_option('--badge',
            help='The badge number of the notification',
            dest='badge',
            default=None
        ),
        make_option('--sound',
            help='The sound for the notification',
            dest='sound',
            default=None
        ),
        make_option('--service',
            help='The id of the APN Service to send this notification through',
            dest='service',
            default=None
        )
    )

    def handle(self, *args, **options):
        if options['message'] is None:
            raise CommandError('The --message option is required')
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

        if not Notification.is_valid_length(options['message'], options['badge'], options['sound']):
            raise CommandError('Notification exceeds the maximum payload length. Try making your message shorter.')

        notification = Notification.objects.create(message=options['message'], badge=options['badge'], service=service, sound=options['sound'])
        service.push_notification_to_devices(notification)
        self.stdout.write('Notification pushed successfully\n')
