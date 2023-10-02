import os

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Command to save the OpenAPI files for deploying.

    :todo: Config appiconnect path in settings
    """
    help = "Command to save the OpenAPI files for deploying."

    def add_arguments(self, parser):
        parser.add_argument("--url", action="store", dest="url", default="http://127.0.0.1:8000",
                            help="Running server url.")

    def handle(self, *args, **options):
        self.stdout.write("DEPLOY TASK | Starting tasks for deploying with IMI Pipeline")

        self.stdout.write("DEPLOY TASK | Converting Pipfile to requirements.txt")
        os.system("pip freeze > ../requirements/dev.txt")
        os.system("pipenv lock --requirements > ../requirements/production.txt")
        os.system("cp ../system-requirements.txt ../requirements/system-production.txt")
        self.stdout.write("DEPLOY TASK | OK | Converted Pipfile to requirements.txt")

        self.stdout.write("DEPLOY TASK | Generating API Manager files")
        call_command("api_file_generation", *args, **options)
        self.stdout.write("DEPLOY TASK | OK | Generated API Manager files")
        self.stdout.write("DEPLOY TASK | Compile translations")
        call_command("compilemessages")
        self.stdout.write("DEPLOY TASK | OK | Compiled translations")
        self.stdout.write("DEPLOY TASK | OK | Ready for deploy")
