# Validation limits (business rules)
MAX_PHRASE_LENGTH = 500
MAX_CONTEXT_LENGTH = 1000
MAX_FEEDBACK_LENGTH = 2000
MAX_ERROR_PATTERN_LENGTH = 100
MIN_QUERY_LIMIT = 1
MAX_QUERY_LIMIT = 100


class ValidationError(Exception):
    """Raised when user input validation fails."""
    pass


def validate_phrase_input(english: str, japanese: str, context: str = "") -> None:
    """Validate phrase input from user.

    Args:
        english: English phrase
        japanese: Japanese translation
        context: Optional usage context

    Raises:
        ValidationError: If validation fails with user-friendly message
    """
    if not english or not english.strip():
        raise ValidationError("English phrase cannot be empty")

    if not japanese or not japanese.strip():
        raise ValidationError("Japanese translation cannot be empty")

    if len(english) > MAX_PHRASE_LENGTH:
        raise ValidationError(
            f"English phrase is too long (max {MAX_PHRASE_LENGTH} characters, got {len(english)})"
        )

    if len(japanese) > MAX_PHRASE_LENGTH:
        raise ValidationError(
            f"Japanese translation is too long (max {MAX_PHRASE_LENGTH} characters, got {len(japanese)})"
        )

    if context and len(context) > MAX_CONTEXT_LENGTH:
        raise ValidationError(
            f"Context is too long (max {MAX_CONTEXT_LENGTH} characters, got {len(context)})"
        )


def validate_correction_input(
    original_text: str,
    corrected_text: str,
    feedback: str,
    error_pattern: str = ""
) -> None:
    """Validate correction input from user.

    Args:
        original_text: Original (incorrect) text
        corrected_text: Corrected text
        feedback: Explanation of the correction
        error_pattern: Optional error type

    Raises:
        ValidationError: If validation fails with user-friendly message
    """
    if not original_text or not original_text.strip():
        raise ValidationError("Original text cannot be empty")

    if not corrected_text or not corrected_text.strip():
        raise ValidationError("Corrected text cannot be empty")

    if not feedback or not feedback.strip():
        raise ValidationError("Feedback cannot be empty")

    if len(original_text) > MAX_FEEDBACK_LENGTH:
        raise ValidationError(
            f"Original text is too long (max {MAX_FEEDBACK_LENGTH} characters, got {len(original_text)})"
        )

    if len(corrected_text) > MAX_FEEDBACK_LENGTH:
        raise ValidationError(
            f"Corrected text is too long (max {MAX_FEEDBACK_LENGTH} characters, got {len(corrected_text)})"
        )

    if len(feedback) > MAX_FEEDBACK_LENGTH:
        raise ValidationError(
            f"Feedback is too long (max {MAX_FEEDBACK_LENGTH} characters, got {len(feedback)})"
        )

    if error_pattern and len(error_pattern) > MAX_ERROR_PATTERN_LENGTH:
        raise ValidationError(
            f"Error pattern is too long (max {MAX_ERROR_PATTERN_LENGTH} characters, got {len(error_pattern)})"
        )


def validate_search_keyword(keyword: str) -> None:
    """Validate search keyword input.

    Args:
        keyword: Search keyword

    Raises:
        ValidationError: If validation fails with user-friendly message
    """
    if not keyword or not keyword.strip():
        raise ValidationError("Search keyword cannot be empty")

    if len(keyword) > 200:
        raise ValidationError(
            f"Search keyword is too long (max 200 characters, got {len(keyword)})"
        )


def validate_limit(limit: int) -> int:
    """Validate and clamp query limit.

    Args:
        limit: Requested limit

    Returns:
        Validated limit (clamped to MIN_QUERY_LIMIT and MAX_QUERY_LIMIT)

    Raises:
        ValidationError: If limit is not a positive integer
    """
    if not isinstance(limit, int):
        raise ValidationError("Limit must be an integer")

    if limit < 1:
        raise ValidationError("Limit must be at least 1")

    # Clamp to max (don't raise error, just limit)
    return min(limit, MAX_QUERY_LIMIT)


def validate_order(order: str) -> str:
    """Validate sort order parameter.

    Args:
        order: Sort order ('asc' or 'desc')

    Returns:
        Validated order (defaults to 'desc' if invalid)
    """
    if order not in ('asc', 'desc'):
        return 'desc'  # Safe default
    return order
