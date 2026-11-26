
import re


class HotelResponseProcessor:
    """
    Interprets text responses from hotel conversations.

    Supports basic English and Nepali rule-based extraction.
    This processor does not process audio or use an external AI model.
    """

    NEPALI_DIGITS = str.maketrans(
        "०१२३४५६७८९",
        "0123456789",
    )

    UNKNOWN_TERMS = (
        "not sure",
        "don't know",
        "do not know",
        "unknown",
        "uncertain",
        "cannot confirm",
        "can't confirm",
        "पक्का छैन",
        "थाहा छैन",
        "निश्चित छैन",
        "पुष्टि गर्न सक्दैन",
    )

    NEGATIVE_TERMS = (
        "not available",
        "unavailable",
        "no rooms",
        "don't have",
        "do not have",
        "not included",
        "not provide",
        "don't provide",
        "do not provide",
        "छैन",
        "हुँदैन",
        "उपलब्ध छैन",
        "समावेश छैन",
        "दिँदैन",
        "गर्दैन",
    )

    POSITIVE_TERMS = (
        "available",
        "we have",
        "included",
        "provide",
        "provided",
        "उपलब्ध छ",
        "समावेश छ",
        "दिन्छ",
        "गर्छ",
        "हुन्छ",
    )

    def normalize(self, text):
        """Normalize text and convert Nepali digits."""

        if not isinstance(text, str):
            return ""

        return " ".join(
            text.translate(self.NEPALI_DIGITS)
            .strip()
            .casefold()
            .split()
        )

    def detect_answer(self, text):
        """Detect a clear positive or negative answer."""

        normalized = self.normalize(text)

        if not normalized:
            return None

        if any(term in normalized for term in self.UNKNOWN_TERMS):
            return None

        # Negative phrases take priority.
        if any(term in normalized for term in self.NEGATIVE_TERMS):
            return False

        if re.search(r"\bno\b", normalized):
            return False

        if any(term in normalized for term in self.POSITIVE_TERMS):
            return True

        if re.search(r"\byes\b", normalized):
            return True

        # Match standalone Nepali "छ", not arbitrary substrings.
        if re.search(r"(?<!\w)छ(?!\w)", normalized):
            return True

        return None

    def extract_price(self, text):
        """Extract a numeric price and recognized currency."""

        normalized = self.normalize(text)

        match = re.search(
            r"(?<!\d)(\d[\d,]*(?:\.\d+)?)",
            normalized,
        )

        if not match:
            return {
                "quoted_price_per_room_per_night": None,
                "currency": None,
            }

        amount = match.group(1).replace(",", "")

        currency = None

        if re.search(
            r"\bnpr\b|\brs\.?(?=\s|$)|रु|रुपैयाँ|रूपैयाँ",
            normalized,
        ):
            currency = "NPR"

        elif re.search(r"\busd\b|\$|\bdollars?\b", normalized):
            currency = "USD"

        elif re.search(r"\binr\b|₹", normalized):
            currency = "INR"

        return {
            "quoted_price_per_room_per_night": amount,
            "currency": currency,
        }

    def extract_available_rooms(self, text):
        """Extract a room count from English or Nepali text."""

        normalized = self.normalize(text)

        match = re.search(
            r"(?<!\w)(\d+)\s*(?:(?:वटा)\s*)?(?:rooms?|कोठा)",
            normalized,
        )

        if match:
            return int(match.group(1))

        return None

    def _parse_time(self, match):
        """Convert a matched time to HH:MM format."""

        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        period = (match.group(3) or "").replace(".", "")

        if period:
            if not 1 <= hour <= 12:
                return None

            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0

        elif not 0 <= hour <= 23:
            return None

        return f"{hour:02d}:{minute:02d}"

    def extract_times(self, text):
        """
        Extract times associated with check-in and check-out labels.

        Returns times in HH:MM format.
        Avoids treating unrelated numbers as times.
        """

        normalized = self.normalize(text)

        time_pattern = (
            r"(?<!\d)(\d{1,2})"
            r"(?::([0-5]\d))?\s*"
            r"(a\.?m\.?|p\.?m\.?)?"
            r"(?!\d)"
        )

        labels = {
            "check_in_time": r"check[\s-]*in|चेक[\s-]*इन",
            "check_out_time": r"check[\s-]*out|चेक[\s-]*आउट",
        }

        result = {
            "check_in_time": None,
            "check_out_time": None,
        }

        for field, label_pattern in labels.items():
            label_match = re.search(label_pattern, normalized)

            if not label_match:
                continue

            # Only inspect the text shortly after the relevant label.
            following_text = normalized[
                label_match.end():label_match.end() + 45
            ]

            time_match = re.search(time_pattern, following_text)

            if time_match:
                result[field] = self._parse_time(time_match)

        return result

    def process_response(self, question_key, text):
        """
        Interpret a hotel response based on the question asked.

        Supported keys:
        availability, price, breakfast, airport_pickup,
        check_in_out.
        """

        normalized = self.normalize(text)

        result = {
            "question_key": question_key,
            "raw_response": text if isinstance(text, str) else "",
            "response_status": "unclear",
        }

        if not normalized:
            result["response_status"] = "unknown"
            return result

        if any(term in normalized for term in self.UNKNOWN_TERMS):
            result["response_status"] = "unknown"
            return result

        if question_key == "availability":
            availability = self.detect_answer(text)

            result["availability"] = availability
            result["available_rooms"] = self.extract_available_rooms(text)

            if availability is not None:
                result["response_status"] = "complete"

        elif question_key == "price":
            price_data = self.extract_price(text)
            result.update(price_data)

            if price_data["quoted_price_per_room_per_night"] is not None:
                result["response_status"] = (
                    "complete"
                    if price_data["currency"] is not None
                    else "partial"
                )

        elif question_key == "breakfast":
            result["breakfast_included"] = self.detect_answer(text)

            if result["breakfast_included"] is not None:
                result["response_status"] = "complete"

        elif question_key == "airport_pickup":
            result["airport_pickup"] = self.detect_answer(text)

            if result["airport_pickup"] is not None:
                result["response_status"] = "complete"

        elif question_key == "check_in_out":
            result.update(self.extract_times(text))

            if result["check_in_time"] and result["check_out_time"]:
                result["response_status"] = "complete"

            elif result["check_in_time"] or result["check_out_time"]:
                result["response_status"] = "partial"

        else:
            result["response_status"] = "unknown"

        return result
