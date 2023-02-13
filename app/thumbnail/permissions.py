from rest_framework.permissions import BasePermission


class DoesUserHaveTier(BasePermission):
    """Object-level permission to only allow users with plan."""
    message = "User does not have selected plan."

    def has_permission(self, request, view):
        return bool(request.user.plan_id)
