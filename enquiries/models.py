
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
