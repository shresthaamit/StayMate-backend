
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.utils.text import slugify


# ==========================================================
# ORGANISATION
# One hotel business or hotel group using StayMate
# ==========================================================

class Organisation(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    legal_name = models.CharField(max_length=200, blank=True)
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=20, blank=True)

    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_organisations"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "organisation"
            candidate = base_slug
            counter = 1

            while Organisation.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1

            self.slug = candidate

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ==========================================================
# ORGANISATION MEMBERSHIP
# Connects users to organisations with roles
# ==========================================================

class Membership(models.Model):

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Administrator"
        MANAGER = "manager", "Hotel Manager"
        RECEPTIONIST = "receptionist", "Receptionist"
        STAFF = "staff", "Staff"

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="memberships"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hotel_memberships"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF
    )

    is_active = models.BooleanField(default=True)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "user"],
                name="unique_organisation_membership"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.organisation.name} ({self.role})"


# ==========================================================
# HOTEL
# Each hotel belongs to an organisation
# ==========================================================

class Hotel(models.Model):

    class HotelType(models.TextChoices):
        HOTEL = "hotel", "Hotel"
        RESORT = "resort", "Resort"
        GUESTHOUSE = "guesthouse", "Guest House"
        HOSTEL = "hostel", "Hostel"
        HOMESTAY = "homestay", "Homestay"
        APARTMENT = "apartment", "Apartment"
        BOUTIQUE = "boutique", "Boutique Hotel"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        TEMPORARILY_CLOSED = "temporarily_closed", "Temporarily Closed"

    organisation = models.ForeignKey(
    Organisation,
    on_delete=models.CASCADE,
    related_name="hotels"
)

    # Basic information
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    hotel_type = models.CharField(
        max_length=30,
        choices=HotelType.choices,
        default=HotelType.HOTEL
    )

    star_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    website = models.URLField(blank=True)

    # Location
    country = models.CharField(max_length=100)
    province = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=150, blank=True)
    address = models.TextField()
    postal_code = models.CharField(max_length=20, blank=True)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90)
        ]
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180)
        ]
    )

    nearby_landmarks = models.TextField(blank=True)

    # Main contact information
    contact_phone = models.CharField(max_length=20)
    alternative_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    preferred_language = models.CharField(
        max_length=50,
        default="English"
    )

    preferred_contact_time = models.CharField(
        max_length=100,
        blank=True
    )

    # Hotel policies
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)

    cancellation_policy = models.TextField(blank=True)
    refund_policy = models.TextField(blank=True)
    child_policy = models.TextField(blank=True)
    extra_bed_policy = models.TextField(blank=True)
    pet_policy = models.TextField(blank=True)
    smoking_policy = models.TextField(blank=True)

    payment_methods = models.JSONField(default=list, blank=True)

    tax_information = models.TextField(blank=True)
    deposit_policy = models.TextField(blank=True)

    # Management and verification
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.organisation.name})"


# ==========================================================
# FACILITY
# Reusable facilities for hotels and rooms
# ==========================================================

class Facility(models.Model):

    class Category(models.TextChoices):
        GENERAL = "general", "General"
        ROOM = "room", "Room"
        SERVICE = "service", "Service"
        ACCESSIBILITY = "accessibility", "Accessibility"

    name = models.CharField(max_length=100, unique=True)

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL
    )

    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


# ==========================================================
# HOTEL FACILITY
# Many-to-many relationship between hotel and facility
# ==========================================================

class HotelFacility(models.Model):

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="hotel_facilities"
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="hotel_facilities"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "facility"],
                name="unique_hotel_facility"
            )
        ]

    def __str__(self):
        return f"{self.hotel.name} - {self.facility.name}"


# ==========================================================
# HOTEL CONTACT
# Additional hotel contacts
# ==========================================================

class HotelContact(models.Model):

    class ContactRole(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        RECEPTIONIST = "receptionist", "Receptionist"
        RESERVATION = "reservation", "Reservation Staff"
        OTHER = "other", "Other"

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="contacts"
    )

    name = models.CharField(max_length=150)

    role = models.CharField(
        max_length=30,
        choices=ContactRole.choices,
        default=ContactRole.OTHER
    )

    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    preferred_language = models.CharField(
        max_length=50,
        default="English"
    )

    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hotel"],
                condition=models.Q(is_primary=True),
                name="unique_primary_hotel_contact"
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.hotel.name}"


# ==========================================================
# ROOM TYPE
# Different room categories offered by a hotel
# ==========================================================

class RoomType(models.Model):

    class BedType(models.TextChoices):
        SINGLE = "single", "Single"
        DOUBLE = "double", "Double"
        QUEEN = "queen", "Queen"
        KING = "king", "King"
        TWIN = "twin", "Twin"
        BUNK = "bunk", "Bunk"
        OTHER = "other", "Other"

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="room_types"
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    # Guest capacity
    max_occupancy = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1)]
    )

    adult_capacity = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1)]
    )

    child_capacity = models.PositiveSmallIntegerField(
        default=0
    )

    # Room inventory
    total_rooms = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    # Bed configuration
    bed_type = models.CharField(
        max_length=20,
        choices=BedType.choices,
        default=BedType.DOUBLE
    )

    number_of_beds = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    # Pricing
    base_price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    min_price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    max_price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    currency = models.CharField(max_length=3, default="NPR")

    # Included services
    breakfast_included = models.BooleanField(default=False)
    included_services = models.JSONField(default=list, blank=True)

    facilities = models.ManyToManyField(
        Facility,
        blank=True,
        related_name="room_types"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_occupancy__gte=models.F("adult_capacity")),
                name="room_capacity_gte_adult_capacity"
            ),
            models.CheckConstraint(
                check=(
                    models.Q(min_price_per_night__isnull=True) |
                    models.Q(
                        min_price_per_night__lte=models.F("base_price_per_night")
                    )
                ),
                name="room_min_price_lte_base"
            ),
            models.CheckConstraint(
                check=(
                    models.Q(max_price_per_night__isnull=True) |
                    models.Q(
                        max_price_per_night__gte=models.F("base_price_per_night")
                    )
                ),
                name="room_max_price_gte_base"
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.hotel.name}"


# ==========================================================
# ROOM AVAILABILITY
# Daily availability and pricing
# ==========================================================

class RoomAvailability(models.Model):

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name="availability_records"
    )

    date = models.DateField()

    available_rooms = models.PositiveIntegerField(default=0)

    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    is_available = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room_type", "date"],
                name="unique_room_type_availability_date"
            ),
            models.CheckConstraint(
                check=models.Q(available_rooms__gte=0),
                name="available_rooms_non_negative"
            )
        ]

    def __str__(self):
        return f"{self.room_type.name} - {self.date}"


# ==========================================================
# HOTEL IMAGE
# Hotel logo, exterior, interior, rooms and facilities
# ==========================================================

class HotelImage(models.Model):

    class ImageType(models.TextChoices):
        LOGO = "logo", "Logo"
        EXTERIOR = "exterior", "Exterior"
        INTERIOR = "interior", "Interior"
        ROOM = "room", "Room"
        RESTAURANT = "restaurant", "Restaurant"
        FACILITY = "facility", "Facility"
        OTHER = "other", "Other"

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="hotels/images/"
    )

    image_type = models.CharField(
        max_length=20,
        choices=ImageType.choices,
        default=ImageType.OTHER
    )

    caption = models.CharField(max_length=200, blank=True)

    is_primary = models.BooleanField(default=False)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hotel"],
                condition=models.Q(is_primary=True),
                name="unique_primary_hotel_image"
            )
        ]

    def __str__(self):
        return f"{self.hotel.name} - {self.image_type}"
