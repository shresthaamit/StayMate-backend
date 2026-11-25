
class HotelConversationEngine:
    """
    Builds a structured hotel enquiry conversation
    in English or Nepali.

    This is a rule-based engine. It does not process live audio.
    """

    SUPPORTED_LANGUAGES = ("en", "ne")

    def __init__(self, call):
        self.call = call
        self.language = (
            call.target_language
            if call.target_language in self.SUPPORTED_LANGUAGES
            else "en"
        )

    def build_questions(self):
        requirement = self.call.hotel_match.requirement
        room = self.call.hotel_match.matched_room_type
        hotel = self.call.hotel_match.hotel

        # Handle cases where no matched room is available.
        room_name = (
            room.name
            if room is not None
            else (
                "कोठा"
                if self.language == "ne"
                else "requested room"
            )
        )

        if self.language == "ne":
            return [
                {
                    "key": "introduction",
                    "message": (
                        "नमस्कार! म StayMate बाट बोलिरहेको AI सहायक हुँ। "
                        f"{hotel.name} मा कोठाको उपलब्धता बुझ्न फोन गरेको हुँ।"
                    ),
                },
                {
                    "key": "dates_and_guests",
                    "message": (
                        f"हामीलाई {requirement.check_in_date} देखि "
                        f"{requirement.check_out_date} सम्म "
                        f"{requirement.adults} जना वयस्क र "
                        f"{requirement.children} जना बालबालिकाका लागि "
                        "कोठा चाहिएको छ।"
                    ),
                },
                {
                    "key": "availability",
                    "message": (
                        f"{room_name} का {requirement.rooms} वटा कोठा "
                        "उपलब्ध छन्?"
                    ),
                },
                {
                    "key": "price",
                    "message": "प्रति रात प्रति कोठाको मूल्य कति हो?",
                },
                {
                    "key": "breakfast",
                    "message": "कोठाको मूल्यमा बिहानको खाना समावेश छ?",
                },
                {
                    "key": "airport_pickup",
                    "message": "के तपाईंहरूले विमानस्थलबाट पिकअप सेवा दिनुहुन्छ?",
                },
                {
                    "key": "check_in_out",
                    "message": "चेक-इन र चेक-आउट समय कति बजे हो?",
                },
            ]

        return [
            {
                "key": "introduction",
                "message": (
                    "Hello! I'm an AI assistant from StayMate. "
                    f"I'm calling to enquire about accommodation at {hotel.name}."
                ),
            },
            {
                "key": "dates_and_guests",
                "message": (
                    f"We are enquiring about a stay from "
                    f"{requirement.check_in_date} to "
                    f"{requirement.check_out_date} for "
                    f"{requirement.adults} adults and "
                    f"{requirement.children} children."
                ),
            },
            {
                "key": "availability",
                "message": (
                    f"Do you have {requirement.rooms} "
                    f"{room_name} room(s) available?"
                ),
            },
            {
                "key": "price",
                "message": "What is your price per room per night?",
            },
            {
                "key": "breakfast",
                "message": "Is breakfast included in the room price?",
            },
            {
                "key": "airport_pickup",
                "message": "Do you provide airport pickup?",
            },
            {
                "key": "check_in_out",
                "message": "What are your check-in and check-out times?",
            },
        ]
