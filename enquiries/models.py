
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class TravellerRequirement(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        MATCHING = "matching", "Matching"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    # Traveller account
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hotel_requirements"
    )

    # Original natural-language request
    original_request = models.TextField(blank=True)

    # Destination
    country = models.CharField(max_length=100)
    province = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=150, blank=True)

    # Stay dates
    check_in_date = models.DateField()
    check_out_date = models.DateField()

    # Guests and rooms
    adults = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    children = models.PositiveSmallIntegerField(default=0)
    rooms = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    # Budget per night
    min_budget_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))]
    )

    max_budget_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))]
    )

    currency = models.CharField(max_length=3, default="NPR")

    # Hotel preferences
    preferred_hotel_types = models.JSONField(
        default=list,
        blank=True
    )

    minimum_star_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    required_facilities = models.JSONField(
        default=list,
        blank=True
    )

    special_requests = models.TextField(blank=True)

    # Request status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.city} hotel request - {self.user}"

class HotelMatch(models.Model):

    class Status(models.TextChoices):
        SHORTLISTED = "shortlisted", "Shortlisted"
        CALL_PENDING = "call_pending", "Call Pending"
        CALLING = "calling", "Calling"
        RESPONDED = "responded", "Hotel Responded"
        UNAVAILABLE = "unavailable", "Unavailable"
        REJECTED = "rejected", "Rejected"

    # Which traveller request produced this match?
    requirement = models.ForeignKey(
        TravellerRequirement,
        on_delete=models.CASCADE,
        related_name="hotel_matches"
    )

    # Which hotel matched the request?
    hotel = models.ForeignKey(
        "hotels.Hotel",
        on_delete=models.CASCADE,
        related_name="traveller_matches"
    )

    # Best matching room type at this hotel
    matched_room_type = models.ForeignKey(
        "hotels.RoomType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hotel_matches"
    )

    # Matching engine score: 0 to 100
    match_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )

    # Why the hotel matched
    match_reasons = models.JSONField(
        default=list,
        blank=True
    )

    # Estimated price for the selected room
    estimated_price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    currency = models.CharField(max_length=3, default="NPR")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SHORTLISTED
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-match_score", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["requirement", "hotel"],
                name="unique_hotel_match_per_requirement"
            )
        ]

    def __str__(self):
        return (
            f"{self.hotel.name} - "
            f"{self.requirement.city} "
            f"({self.match_score}%)"
        )
