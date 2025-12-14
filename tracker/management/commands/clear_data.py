from django.core.management.base import BaseCommand
from tracker.models import DietaryEntry, ExerciseEntry, WeightEntry


class Command(BaseCommand):
    help = 'Delete all data from DietaryEntry, ExerciseEntry, and WeightEntry tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        if not options['force']:
            confirm = input('Are you sure you want to delete ALL fitness data? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Aborted.'))
                return

        dietary_count = DietaryEntry.objects.count()
        exercise_count = ExerciseEntry.objects.count()
        weight_count = WeightEntry.objects.count()

        DietaryEntry.objects.all().delete()
        ExerciseEntry.objects.all().delete()
        WeightEntry.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {dietary_count} dietary entries, '
            f'{exercise_count} exercise entries, '
            f'{weight_count} weight entries.'
        ))
