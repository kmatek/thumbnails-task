from rest_framework.permissions import BasePermission


class DoesUserHaveTier(BasePermission):
    """Object-level permission to only allow users with plan."""
    message = "User does not have selected plan."

    def has_permission(self, request, view):
        return bool(request.user.plan_id)


class CanCreateLink(BasePermission):
    """Object-level permission to only allow users with a plan to create expired links.""" # noqa
    message = "User'plan does not contain creating expired links."

    def has_permission(self, request, view):
        try:
            return request.user.plan.expired_link
        except AttributeError:
            return False
