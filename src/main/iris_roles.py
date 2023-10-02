from main.open_api.decorators import imi_roles

ADMIN = 'admin'
PUBLIC = 'public'
EXTERNAL = 'external'
IRIS_API_ROLES = {
    ADMIN: 'Only admin user can access this operation',
    PUBLIC: 'Access from outside the VPN',
    EXTERNAL: 'Access from outside the VPN and only to External Processing endpoints',
}


def iris_roles(fn, roles):
    """
    Decorates the given view with a dict of roles.
    """
    if PUBLIC in roles:
        raise Exception(
            'This decorator does not allow to set the public role, '
            'you must use the iris public roles specifically.'
        )
    return imi_roles(fn, roles)


def backoffice_roles(fn):
    return imi_roles(fn, {PUBLIC: IRIS_API_ROLES[ADMIN]})


def public_iris_roles(fn):
    """
    Sets the public role to a given operation.
    """
    return imi_roles(fn, {PUBLIC: IRIS_API_ROLES[PUBLIC]})


def public_extern_iris_roles(fn):
    """
    Sets the public role to a given operation.
    """
    return imi_roles(fn, {EXTERNAL: IRIS_API_ROLES[EXTERNAL]})
