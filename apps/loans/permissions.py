from rest_framework.permissions import BasePermission

class LoanAccess(BasePermission):
    """Staff can inspect all loans; applicants only their own records."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        loan = getattr(obj, 'loan', obj)
        return bool(request.user.is_staff or loan.owner_id == request.user.pk)


def visible_loans(user):
    from .models import LoanApplication
    qs = LoanApplication.objects.all()
    return qs if user.is_staff else qs.filter(owner=user)
