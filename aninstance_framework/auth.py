from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin


class Authenticate(UserPassesTestMixin):
    """
    My authentication class, that authenticates based on
    level param. Uses UserPassesTestMixin.
    """

    def __init__(self, request, level=None):
        self.user = request.user
        self.level = level

    def test_func(self):
        if self.level == USER_LEVEL.get('superuser'):
            return self.user.is_superuser
        elif self.level == USER_LEVEL.get('staff'):
            return self.user.is_staff
        else:
            return self.user.is_authenticated

    def auth(self):
        return self.test_func()


USER_LEVEL = {
    'staff': 'staff',
    'superuser': 'superuser',
    'user': 'user'
}