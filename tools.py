"""Two safe, student-focused tools for study calculations and draft planning."""

from math import isfinite

from langchain_core.tools import tool

MAX_OUTPUT_CHARS = 700


def clip(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Limit tool responses to a readable length."""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _hours(value: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) and number > 0 else None


@tool
def calculate_study_time(estimated_hours: float, days_available: int) -> str:
    """Calculate suggested daily study hours from total work and the available number of days."""
    hours = _hours(estimated_hours)
    if hours is None:
        return clip("Error: estimated_hours must be a finite number greater than zero.")
    if isinstance(days_available, bool):
        return clip("Error: days_available must be a whole number greater than zero.")
    try:
        days = int(days_available)
        if str(days_available).strip() not in (str(days), "+{}".format(days)):
            return clip("Error: days_available must be a whole number greater than zero.")
    except (TypeError, ValueError, OverflowError):
        return clip("Error: days_available must be a whole number greater than zero.")
    if days <= 0:
        return clip("Error: days_available must be greater than zero.")
    return clip(
        "{:.2f} total study hours across {} days is about {:.2f} study hours per day.".format(
            hours, days, hours / days
        )
    )


@tool
def draft_study_plan(
    subject: str,
    assignment_title: str,
    days_available: int,
    estimated_hours: float,
) -> str:
    """Draft a short study schedule from a subject, assignment, available days, and estimated hours."""
    hours = _hours(estimated_hours)
    if (
        not isinstance(subject, str)
        or not isinstance(assignment_title, str)
        or not subject.strip()
        or not assignment_title.strip()
    ):
        return clip("Error: subject and assignment_title cannot be blank.")
    if hours is None:
        return clip("Error: estimated_hours must be a finite number greater than zero.")
    if isinstance(days_available, bool):
        return clip("Error: days_available must be a whole number greater than zero.")
    try:
        days = int(days_available)
        if str(days_available).strip() not in (str(days), "+{}".format(days)):
            return clip("Error: days_available must be a whole number greater than zero.")
    except (TypeError, ValueError, OverflowError):
        return clip("Error: days_available must be a whole number greater than zero.")
    if days <= 0:
        return clip("Error: days_available must be greater than zero.")

    daily_hours = hours / days
    plan = (
        "Draft plan for {title} ({subject}): aim for about {daily:.2f} hour(s) per day "
        "for {days} days. Start by checking the requirements and making a short outline; "
        "use the middle sessions to complete the main work; reserve the final session to "
        "review and correct it. Take short breaks and adjust the draft to your schedule. "
        "This is a suggestion only; nothing is sent or changed."
    ).format(
        title=assignment_title.strip(),
        subject=subject.strip(),
        daily=daily_hours,
        days=days,
    )
    return clip(plan)


TOOLS = [calculate_study_time, draft_study_plan]
