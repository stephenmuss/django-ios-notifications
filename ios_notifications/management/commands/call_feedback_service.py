# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from ios_notifications.models import FeedbackService
from optparse import make_option

# TODO: argparse for Python 2.7


class Command(BaseCommand):
    help = 'Calls the Apple Feedback Service to determine which devices are no longer active and deactivates them in the database.'

    option_list = BaseCommand.option_list + (
        make_option('--feedback-service',
            help='The id of the Feedback Service to call',
            dest='service',
            default=None),)

    def handle(self, *args, **options):
        if options['service'] is None:
            raise CommandError('The --feedback-service option is required')
        try:
            service_id = int(options['service'])
        except ValueError:
            raise CommandError('The --feedback-service option should pass an id in integer format as its value')
        try:
            service = FeedbackService.objects.get(pk=service_id)
        except FeedbackService.DoesNotExist:
            raise CommandError('FeedbackService with id %d does not exist' % service_id)

        num_deactivated = service.call()
        output = '%d device%s deactivated.\n' % (num_deactivated, ' was' if num_deactivated == 1 else 's were')
        self.stdout.write(output)
