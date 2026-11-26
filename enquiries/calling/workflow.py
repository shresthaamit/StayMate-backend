
from django.db import transaction
from django.utils import timezone

from enquiries.models import HotelCall

from .providers import get_call_provider
from .response_processor import HotelResponseProcessor


def execute_hotel_call(call):
    """
    Execute a hotel call through its configured provider.
    """
    provider = get_call_provider(call.mode)
    return provider.execute(call)


def process_hotel_response(question_key, response_text):
    """
    Convert a hotel's text response into structured data.
    """
    processor = HotelResponseProcessor()

    return processor.process_response(
        question_key=question_key,
        text=response_text,
    )


@transaction.atomic
def process_and_store_hotel_response(
    call,
    question_key,
    response_text,
):
    """
    Process a hotel's text response and persist the result.

    Existing response data and transcript entries are preserved.
    """
    locked_call = HotelCall.objects.select_for_update().get(
        pk=call.pk
    )

    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Hotel response cannot be empty.")

    processed_result = process_hotel_response(
        question_key=question_key,
        response_text=response_text,
    )

    response_data = (
        locked_call.response_data.copy()
        if isinstance(locked_call.response_data, dict)
        else {}
    )

    answers = response_data.get("answers", {})
    if not isinstance(answers, dict):
        answers = {}

    answer_status = response_data.get("answer_status", {})
    if not isinstance(answer_status, dict):
        answer_status = {}

    response_status = processed_result.get(
        "response_status",
        "unknown"
    )

    answer_record = {
        **processed_result,
        "raw_response": response_text.strip(),
    }

    answers[question_key] = answer_record
    answer_status[question_key] = response_status

    response_data["answers"] = answers
    response_data["answer_status"] = answer_status

    # Also expose extracted answers at the top level for
    # compatibility with existing result consumers.
    metadata_keys = {
        "question_key",
        "response_status",
        "raw_response",
    }

    for key, value in processed_result.items():
        if key not in metadata_keys:
            response_data[key] = value

    transcript = (
        list(locked_call.transcript)
        if isinstance(locked_call.transcript, list)
        else []
    )

    transcript.append({
        "role": "hotel",
        "message": response_text.strip(),
        "timestamp": timezone.now().isoformat(),
    })

    locked_call.transcript = transcript
    locked_call.response_data = response_data

    locked_call.save(
        update_fields=[
            "transcript",
            "response_data",
            "updated_at",
        ]
    )

    return locked_call
