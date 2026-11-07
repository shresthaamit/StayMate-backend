
from rest_framework.permissions import BasePermission

from .models import Membership


class BaseOrganisationPermission(BasePermission):
    """
    Base permission for users belonging to active organisations.
    """

    allowed_roles = []

    def get_object_organisation(self, obj):
        """
        Identify the organisation associated with an object.
        Supports Hotel and related hotel models.
        """

        if hasattr(obj, "organisation"):
            return obj.organisation

        if hasattr(obj, "hotel"):
            return obj.hotel.organisation

        if hasattr(obj, "room_type"):
            return obj.room_type.hotel.organisation

        return None

    def has_permission(self, request, view):
        """
        Check whether the authenticated user has an active
        membership in at least one active organisation.
        """

        if not request.user or not request.user.is_authenticated:
            return False

        return Membership.objects.filter(
            user=request.user,
            is_active=True,
            organisation__status="active",
            role__in=self.allowed_roles,
        ).exists()

    def has_object_permission(self, request, view, obj):
        """
        Check membership in the specific organisation
        associated with the requested object.
        """

        organisation = self.get_object_organisation(obj)

        if organisation is None:
            return False

        return Membership.objects.filter(
            user=request.user,
            organisation=organisation,
            is_active=True,
            organisation__status="active",
            role__in=self.allowed_roles,
        ).exists()


class IsActiveOrganisationMember(BaseOrganisationPermission):
    allowed_roles = [
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
        Membership.Role.RECEPTIONIST,
        Membership.Role.STAFF,
    ]


class IsOrganisationOwnerOrAdmin(BaseOrganisationPermission):
    allowed_roles = [
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    ]


class IsHotelManagerOrAbove(BaseOrganisationPermission):
    allowed_roles = [
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
    ]


class IsHotelOperationalMember(BaseOrganisationPermission):
    allowed_roles = [
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
        Membership.Role.RECEPTIONIST,
        Membership.Role.STAFF,
    ]
