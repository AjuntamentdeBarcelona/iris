from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from social_core.exceptions import AuthException


def associate_by_username(backend, details, user=None, *args, **kwargs):
    """
    Since we set the username for the user, we add this rule for merging them by username
    """
    if user:
        return None
    User = get_user_model()
    try:
        user = User.objects.get(username=details['username'])
        if not user.email or user.email != details.get('email'):
            user.email = details.get('email')
            user.save(update_fields=['email'])
        return {
            'user': user,
            'is_new': False
        }
    except MultipleObjectsReturned:
        raise AuthException(
            backend,
            'The given username address is associated with another account'
        )
    except User.DoesNotExist:
        return None
