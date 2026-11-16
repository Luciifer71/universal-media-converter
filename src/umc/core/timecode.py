"""Read and display times such as 90, 1:30 or 1:02:03.5."""

import math


def parse_time(value: str) -> float:
    """Convert '90', '90.5', '1:30' or '1:02:03' into seconds.

    Raises ValueError with a friendly message for anything else.
    """
    text = value.strip()
    parts = text.split(":")

    if not text or len(parts) > 3:
        raise ValueError(f"Invalid time: {value!r}. Use seconds (90) or minutes:seconds (1:30).")

    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        raise ValueError(
            f"Invalid time: {value!r}. Use seconds (90) or minutes:seconds (1:30)."
        ) from None

    if not all(math.isfinite(number) for number in numbers):
        raise ValueError(f"Invalid time: {value!r}. Use seconds (90) or minutes:seconds (1:30).")

    if any(number < 0 for number in numbers):
        raise ValueError(f"Invalid time: {value!r}. Times cannot be negative.")

    # In "1:30" or "1:02:03", every part after the first must be below 60.
    if any(number >= 60 for number in numbers[1:]):
        raise ValueError(f"Invalid time: {value!r}. Minutes and seconds must be below 60.")

    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number

    return seconds


def format_duration(seconds: float) -> str:
    """Return a duration like 1:02:03 or 4:05."""
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"
