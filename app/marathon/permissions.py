MANAGE_NOMINATIONS = 'marathon.manage_nominations'


def can_manage_nominations(user):
    return user.is_authenticated and user.has_perm(MANAGE_NOMINATIONS)
