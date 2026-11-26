"""The three read-only and draft-only tools used by the deadline agent."""

import csv
from datetime import date
from pathlib import Path

from langchain_core.tools import tool

CSV_PATH = Path(__file__).resolve().parent / "data" / "deadlines.csv"
MAX_OUTPUT_CHARS = 1400


def clip(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Keep tool output short enough to be readable in chat."""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _read_rows() -> list[dict[str, str]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


@tool
def find_deadlines(subject: str = "", status: str = "", upcoming_days: int = 0) -> str:
    """Find assignments in the deadline CSV by subject, status, or upcoming date range."""
    try:
        if upcoming_days < 0:
            return "Error: upcoming_days must be zero or a positive number."
        rows = _read_rows()
        today = date.today()
        matches = []
        for row in rows:
            if subject.strip() and subject.casefold() not in row.get("subject", "").casefold():
                continue
            if status.strip() and status.casefold() != row.get("status", "").casefold():
                continue
            if upcoming_days:
                try:
                    due = date.fromisoformat(row.get("due_date", ""))
                except ValueError:
                    continue
                if not 0 <= (due - today).days <= upcoming_days:
                    continue
            matches.append(row)
        if not matches:
            return "No assignments matched those filters."
        lines = []
        for row in matches[:20]:
            lines.append(
                "{assignment_id} | {subject} | {assignment_title} | due {due_date} | "
                "{estimated_hours} hours | priority {priority} | {status}".format(
                    assignment_id=row.get("assignment_id", "unknown"),
                    subject=row.get("subject", "unknown"),
                    assignment_title=row.get("assignment_title", "untitled"),
                    due_date=row.get("due_date", "unknown"),
                    estimated_hours=row.get("estimated_hours", "unknown"),
                    priority=row.get("priority", "unknown"),
                    status=row.get("status", "unknown"),
                )
            )
        if len(matches) > 20:
            lines.append("Showing the first 20 matching assignments.")
        return clip("\n".join(lines))
    except (OSError, csv.Error) as error:
        return "Could not read the deadline CSV: {}.".format(error)
    except Exception:
        return "Could not search deadlines because the filter input or CSV data was invalid."


@tool
def calculate_study_time(due_date: str, estimated_hours: float) -> str:
    """Calculate the days remaining and a suggested daily study time for an assignment."""
    try:
        due = date.fromisoformat(due_date.strip())
    except (TypeError, ValueError, AttributeError):
        return "Error: enter the due date in YYYY-MM-DD format."
    try:
        hours = float(estimated_hours)
    except (TypeError, ValueError):
        return "Error: estimated_hours must be a number."
    if hours <= 0:
        return "Error: estimated_hours must be greater than zero."
    days_remaining = (due - date.today()).days
    if days_remaining < 0:
        return "This assignment is overdue by {} day(s); ask for a new deadline before planning.".format(
            abs(days_remaining)
        )
    study_days = max(days_remaining, 1)
    hours_per_day = hours / study_days
    return clip(
        "{} day(s) remain. Plan about {:.2f} study hour(s) per day across {} day(s) "
        "for an estimate of {:.2f} total hour(s).".format(
            days_remaining, hours_per_day, study_days, hours
        )
    )


@tool
def draft_study_plan(
    assignment_title: str,
    subject: str,
    remaining_days: int,
    estimated_hours: float,
) -> str:
    """Draft a personalized study schedule suggestion without sending or changing anything."""
    try:
        title = assignment_title.strip()
        course = subject.strip()
        days = int(remaining_days)
        hours = float(estimated_hours)
    except (TypeError, ValueError, AttributeError):
        return "Error: provide a title, subject, whole number of remaining days, and numeric hours."
    if not title or not course:
        return "Error: assignment title and subject cannot be blank."
    if days < 0 or hours <= 0:
        return "Error: remaining days cannot be negative and estimated hours must be greater than zero."
    sessions = max(days, 1)
    hours_per_day = hours / sessions
    if days == 0:
        suggestion = "Today: break the work into focused blocks and prioritize the most important parts."
    else:
        suggestion = (
            "First half: review the requirements and outline the work. "
            "Middle days: complete the main tasks in focused sessions. "
            "Final day: review, check instructions, and leave time for fixes."
        )
    return clip(
        "Draft plan for {title} ({subject}): {days} day(s) remain, with about {hours:.2f} "
        "hour(s) total ({daily:.2f} hour(s) per day). {suggestion} Add short breaks and "
        "adjust the sessions to your schedule. This is a suggestion only; nothing is sent "
        "or changed.".format(
            title=title,
            subject=course,
            days=days,
            hours=hours,
            daily=hours_per_day,
            suggestion=suggestion,
        )
    )


TOOLS = [find_deadlines, calculate_study_time, draft_study_plan]
