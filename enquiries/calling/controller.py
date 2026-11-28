
from django.db import transaction
from django.utils import timezone

from enquiries.models import HotelCall

from .conversation import HotelConversationEngine
from .workflow import process_and_store_hotel_response


class HotelConversationController:
    """
    Manages a structured text-based hotel conversation.

    Tracks questions, processes responses, requests clarification,
    and stores conversation progress in HotelCall.response_data.
    """

    QUESTION_ORDER = (
        "availability",
        "price",
        "breakfast",
        "airport_pickup",
        "check_in_out",
    )

    MAX_CLARIFICATIONS = 2

    def __init__(self, call):
        self.call = call
        self.engine = HotelConversationEngine(call)
        self.questions = {
            item["key"]: item
            for item in self.engine.build_questions()
        }

    def _append_message(self, transcript, role, message):
        transcript.append({
            "role": role,
            "message": message,
            "timestamp": timezone.now().isoformat(),
        })

    def _get_response_data(self, call):
        if isinstance(call.response_data, dict):
            return dict(call.response_data)
        return {}

    def _get_transcript(self, call):
        if isinstance(call.transcript, list):
            return list(call.transcript)
        return []

    @transaction.atomic
    def start_conversation(self):
        """Start a new conversation for a queued call."""

        call = HotelCall.objects.select_for_update().get(
            pk=self.call.pk
        )

        if call.status != HotelCall.Status.QUEUED:
            raise ValueError(
                "Only queued calls can start a conversation."
            )

        response_data = self._get_response_data(call)
        transcript = self._get_transcript(call)

        progress = {
            "current_question": "availability",
            "completed": False,
            "completed_questions": [],
            "unresolved_questions": [],
            "clarification_attempts": {},
        }

        # Introduction and dates are statements, not questions.
        for key in ("introduction", "dates_and_guests"):
            self._append_message(
                transcript,
                "assistant",
                self.questions[key]["message"],
            )

        first_question = self.questions["availability"]["message"]

        self._append_message(
            transcript,
            "assistant",
            first_question,
        )

        response_data["conversation"] = progress

        call.response_data = response_data
        call.transcript = transcript
        call.status = HotelCall.Status.IN_PROGRESS
        call.started_at = timezone.now()

        call.save(
            update_fields=[
                "response_data",
                "transcript",
                "status",
                "started_at",
                "updated_at",
            ]
        )

        self.call = call

        return {
            "status": call.status,
            "current_question": "availability",
            "message": first_question,
        }

    def _is_answer_complete(self, question_key, answer):
        """Check whether the extracted information is sufficient."""

        if question_key == "availability":
            available = answer.get("availability")

            if available is None:
                return False

            # If available, we also need the room count.
            if available is True:
                return answer.get("available_rooms") is not None

            return True

        if question_key == "price":
            return (
                answer.get("quoted_price_per_room_per_night")
                is not None
                and answer.get("currency") is not None
            )

        if question_key == "breakfast":
            return answer.get("breakfast_included") is not None

        if question_key == "airport_pickup":
            return answer.get("airport_pickup") is not None

        if question_key == "check_in_out":
            return (
                answer.get("check_in_time") is not None
                and answer.get("check_out_time") is not None
            )

        return False

    def _clarification_message(self, question_key, answer):
        """Generate a targeted clarification in the selected language."""

        nepali = self.engine.language == "ne"

        if question_key == "availability":
            if answer.get("availability") is True:
                if nepali:
                    return "कति वटा कोठा उपलब्ध छन्?"
                return "How many rooms are available?"

        if question_key == "price":
            if answer.get("quoted_price_per_room_per_night") is not None:
                if nepali:
                    return "कृपया मूल्य कुन मुद्रामा हो पुष्टि गरिदिनुहोस्।"
                return "Could you confirm the currency of that price?"

            if nepali:
                return "प्रति कोठा प्रति रातको मूल्य कति हो र कुन मुद्रामा?"
            return "What is the price per room per night, and in which currency?"

        if question_key == "check_in_out":
            if answer.get("check_in_time") and not answer.get("check_out_time"):
                if nepali:
                    return "चेक-आउट समय पनि बताइदिनुहोस्।"
                return "Could you also confirm the check-out time?"

            if answer.get("check_out_time") and not answer.get("check_in_time"):
                if nepali:
                    return "चेक-इन समय पनि बताइदिनुहोस्।"
                return "Could you also confirm the check-in time?"

        if nepali:
            return "माफ गर्नुहोस्, कृपया फेरि स्पष्ट रूपमा बताइदिनुहोस्।"

        return "Sorry, could you please clarify your answer?"

    def _advance(self, call, response_data, transcript, progress):
        """Move to the next question or finish the conversation."""

        current = progress["current_question"]
        current_index = self.QUESTION_ORDER.index(current)

        next_index = current_index + 1

        if next_index >= len(self.QUESTION_ORDER):
            progress["current_question"] = None
            progress["completed"] = True

            call.status = HotelCall.Status.COMPLETED
            call.completed_at = timezone.now()

            return {
                "status": call.status,
                "completed": True,
                "current_question": None,
                "message": "Hotel conversation completed.",
            }

        next_question = self.QUESTION_ORDER[next_index]
        progress["current_question"] = next_question

        message = self.questions[next_question]["message"]

        self._append_message(
            transcript,
            "assistant",
            message,
        )

        return {
            "status": call.status,
            "completed": False,
            "current_question": next_question,
            "message": message,
        }

    @transaction.atomic
    def handle_response(self, response_text):
        """Process a hotel response and decide the next action."""

        call = HotelCall.objects.select_for_update().get(
            pk=self.call.pk
        )

        if call.status != HotelCall.Status.IN_PROGRESS:
            raise ValueError(
                "The hotel conversation is not in progress."
            )

        response_data = self._get_response_data(call)
        progress = response_data.get("conversation")

        if not isinstance(progress, dict):
            raise ValueError(
                "Conversation has not been initialized."
            )

        question_key = progress.get("current_question")

        if question_key not in self.QUESTION_ORDER:
            raise ValueError(
                "There is no active question."
            )

        # Process and persist the hotel's answer.
        process_and_store_hotel_response(
            call,
            question_key,
            response_text,
        )

        call.refresh_from_db()

        response_data = self._get_response_data(call)
        progress = response_data["conversation"]

        answers = response_data.get("answers", {})
        answer = answers.get(question_key, {})

        transcript = self._get_transcript(call)

        if self._is_answer_complete(question_key, answer):
            progress["completed_questions"].append(question_key)

            progress["clarification_attempts"][question_key] = 0

            result = self._advance(
                call,
                response_data,
                transcript,
                progress,
            )

        else:
            attempts = progress["clarification_attempts"].get(
                question_key,
                0,
            ) + 1

            progress["clarification_attempts"][question_key] = attempts

            if attempts <= self.MAX_CLARIFICATIONS:
                message = self._clarification_message(
                    question_key,
                    answer,
                )

                self._append_message(
                    transcript,
                    "assistant",
                    message,
                )

                result = {
                    "status": call.status,
                    "completed": False,
                    "current_question": question_key,
                    "message": message,
                    "clarification_attempt": attempts,
                }

            else:
                progress["unresolved_questions"].append(question_key)

                answer_status = response_data.get(
                    "answer_status",
                    {},
                )

                answer_status[question_key] = "needs_review"
                response_data["answer_status"] = answer_status

                result = self._advance(
                    call,
                    response_data,
                    transcript,
                    progress,
                )

        response_data["conversation"] = progress

        call.response_data = response_data
        call.transcript = transcript

        call.save(
            update_fields=[
                "response_data",
                "transcript",
                "status",
                "completed_at",
                "updated_at",
            ]
        )

        self.call = call

        return result
