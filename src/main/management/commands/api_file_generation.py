import requests
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Command to save the OpenAPI files for deploying.

    :todo: Config appiconnect path in settings
    """
    help = "Command to save the OpenAPI files for deploying."

    def add_arguments(self, parser):
        parser.add_argument('--url', action='store', dest='url', default='http://127.0.0.1:8000',
                            help='Running server url.')

    def handle(self, *args, **options):
        self.stdout.write('Starting to generate OpenAPI files')

        self.save_open_api_file(options['url'] + '/services/iris/api-public/swagger.yaml',
                                '../apimanager/iris-public-api.yaml')
        self.save_open_api_file(options['url'] + '/services/iris/api-public/swagger.json',
                                '../apiconnect/iris-api/apis/iris-public-api.json')

        self.save_open_api_file(options['url'] + '/services/iris/api-internet/swagger.yaml',
                                '../apimanager/iris-internet-api.yaml')
        self.save_open_api_file(options['url'] + '/services/iris/api-internet/swagger.json',
                                '../apiconnect/iris-api/apis/iris-internet-api.json')

        self.save_open_api_file(options['url'] + '/services/iris/api/swagger.yaml', '../apimanager/iris-api.yaml')
        self.save_open_api_file(options['url'] + '/services/iris/api/swagger.json',
                                '../apiconnect/iris-api/apis/iris-api.json')

        self.save_open_api_file(options['url'] + '/services/iris/api-public/xml-proxy/swagger.yaml',
                                '../apimanager/iris-xml-proxy.yaml')
        self.save_open_api_file(options['url'] + '/services/iris/api-public/xml-proxy/swagger.json',
                                '../apiconnect/iris-api/apis/iris-xml-proxy.json')

    def save_open_api_file(self, path, destination):
        self.stdout.write('Get file from {}'.format(path))
        open_api_resp = requests.get(path)
        if open_api_resp.status_code == 200:
            self.stdout.write('OpenAPI loaded')
            open_api = open_api_resp.text
            with open(destination, 'w') as f:
                body = self.make_imi_api_manager_workaround(open_api)
                f.seek(0)
                f.write(body)
                f.truncate()
                f.close()
                self.stdout.write('OpenAPI file generated for {}'.format(path))

    @staticmethod
    def make_imi_api_manager_workaround(open_api):
        """
        Workaround for avoiding imi transformation script error with minimums.
        :param open_api: The OpenAPI file as string
        :return: Adjusted OpenAPI file
        """
        return open_api.replace('minimum: -9223372036854775808', 'minimum: -9223372036854775807')
