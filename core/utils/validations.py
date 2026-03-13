from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_date_range(start_date, end_date):
    today = timezone.now().date()
    errors = {}

    if start_date and start_date < today:
        errors["start_date"] = "start_date debe ser posterior al día actual."

    if end_date and end_date <= today:
        errors["end_date"] = "end_date debe ser posterior al día actual."

    if start_date and end_date and start_date >= end_date:
        errors["end_date"] = "end_date debe ser mayor a start_date."

    if errors:
        raise ValidationError(errors)