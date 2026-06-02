from django.core.management.base import BaseCommand
from apps.courts.models import Court


class Command(BaseCommand):
    help = 'Activate or deactivate all courts for a given state code'

    def add_arguments(self, parser):
        parser.add_argument('state', type=str, help='State code (e.g. FC, RI, LA)')
        parser.add_argument(
            '--action',
            choices=['unlock', 'lock'],
            required=True,
            help='unlock = set is_active=True, lock = set is_active=False',
        )

    def handle(self, *args, **options):
        state = options['state'].upper()
        activate = options['action'] == 'unlock'

        qs = Court.objects.filter(state=state)
        count = qs.count()

        if count == 0:
            self.stdout.write(self.style.WARNING(f'No courts found for state={state}'))
            return

        updated = qs.update(is_active=activate)
        status = 'unlocked (active)' if activate else 'locked (inactive)'
        self.stdout.write(
            self.style.SUCCESS(f'{updated} court(s) in state={state} {status}')
        )
