from rest_framework.authentication import TokenAuthentication


class IrisTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        """
        Set imi_data for backwards compatibility with OAM Authentication.
        """
        result = super().authenticate(request)
        if result:
            user, token = result
            setattr(user, 'imi_data', {})
        return result
