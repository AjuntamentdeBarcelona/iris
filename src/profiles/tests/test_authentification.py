import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from model_mommy import mommy

from profiles.authentication import OAMAuthentication
from profiles.models import UserGroup
from profiles.tests.utils import create_groups


@pytest.mark.django_db
class TestOAMAuthentication:

    @pytest.mark.parametrize("create_user", (True, False))
    def test_get_user(self, create_user):
        dair, _, _, _, _, _ = create_groups()
        username = "test"
        if create_user:
            user = mommy.make(User, username=username)
            UserGroup.objects.create(user=user, group=dair)
        request = HttpRequest()
        data = {'email': 'testmail@test.com'}
        user = OAMAuthentication.get_user(username, data)

        assert user.username == username
        if not create_user:
            assert user.email == data.get('email')
