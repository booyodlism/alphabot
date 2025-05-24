# helpers/permissions.py

def has_role(user, role_id: int) -> bool:
    """Check if user has a role by ID."""
    return any(role.id == role_id for role in user.roles)
