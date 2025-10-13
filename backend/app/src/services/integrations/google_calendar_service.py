"""Google Calendar integration helpers for scheduling tools."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from src.logger_config import get_logger

import pytz
from google.oauth2.service_account import (
    Credentials as ServiceAccountCredentials,
)
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = get_logger(__name__)

__all__ = [
    "GoogleCalendarService",
    "GoogleCalendarError",
    "SlotUnavailableError",
    "get_google_calendar_service",
]


SCOPES: Sequence[str] = ("https://www.googleapis.com/auth/calendar",)


class GoogleCalendarError(RuntimeError):
    """Raised when there is a problem communicating with Google Calendar."""


class SlotUnavailableError(GoogleCalendarError):
    """Raised when trying to book a slot that is no longer free."""


@dataclass(frozen=True)
class WorkingHours:
    """Represents daily working hours for slot generation."""

    start: time
    end: time

    @classmethod
    def from_env(cls, start_str: str, end_str: str) -> "WorkingHours":
        """Build a `WorkingHours` instance from HH:MM strings found in the env."""
        return cls(_parse_hhmm(start_str), _parse_hhmm(end_str))


class GoogleCalendarService:
    """Thin wrapper around Google Calendar API for listing and booking slots."""

    def __init__(
        self,
        *,
        credentials: ServiceAccountCredentials,
        timezone: str,
        slot_minutes: int,
        working_hours: WorkingHours,
    ) -> None:
        """Instantiate the service with the components required for API access."""
        self.timezone = timezone
        self.slot_minutes = slot_minutes
        self.working_hours = working_hours
        scoped_credentials = credentials.with_scopes(SCOPES)
        self._service = build(
            "calendar", "v3", credentials=scoped_credentials, cache_discovery=False
        )

    @classmethod
    def from_env(cls) -> "GoogleCalendarService":
        """Factory using environment variables for credentials and defaults."""
        credentials = _load_service_account_credentials()
        timezone = os.getenv("GOOGLE_CALENDAR_DEFAULT_TIMEZONE", "America/Sao_Paulo")
        try:
            slot_minutes = int(os.getenv("GOOGLE_CALENDAR_SLOT_MINUTES", "30"))
        except ValueError as exc:  # pragma: no cover - defensive parsing
            raise GoogleCalendarError(
                "GOOGLE_CALENDAR_SLOT_MINUTES deve ser um número inteiro."
            ) from exc
        working_hours = WorkingHours.from_env(
            os.getenv("GOOGLE_CALENDAR_WORKDAY_START", "09:00"),
            os.getenv("GOOGLE_CALENDAR_WORKDAY_END", "18:00"),
        )
        return cls(
            credentials=credentials,
            timezone=timezone,
            slot_minutes=slot_minutes,
            working_hours=working_hours,
        )

    def list_available_slots(self, calendar_id: str, target_date: date) -> List[str]:
        """Return available slots (HH:MM) for `target_date` respecting business hours."""
        window_start, window_end = self._build_working_window(target_date)
        busy_periods = self._fetch_busy_periods(calendar_id, window_start, window_end)
        return self._generate_available_slots(window_start, window_end, busy_periods)

    def book_slot(
        self,
        *,
        calendar_id: str,
        slot_date: date,
        slot_time: time,
        patient_name: str,
        patient_phone: Optional[str],
        patient_email: Optional[str],
        patient_id: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        notes: Optional[str] = None,
        dentist_name: Optional[str] = None,
        dentist_id: Optional[str] = None,
        send_updates: str = "all",
    ) -> Dict[str, Any]:
        """Book a calendar event that covers the requested slot."""
        slot_duration = duration_minutes or self.slot_minutes
        start_dt, end_dt = self._resolve_slot_interval(
            slot_date, slot_time, slot_duration
        )
        self._ensure_slot_is_free(calendar_id, start_dt, end_dt)

        event_body = self._build_event_body(
            start_dt=start_dt,
            end_dt=end_dt,
            patient_name=patient_name,
            patient_phone=patient_phone,
            patient_email=patient_email,
            patient_id=patient_id,
            notes=notes,
            dentist_name=dentist_name,
            dentist_id=dentist_id,
        )

        event = self._create_event(
            calendar_id=calendar_id,
            body=event_body,
            send_updates=send_updates,
        )
        return self._serialize_event(event)

    def find_patient_event(
        self,
        *,
        calendar_id: str,
        slot_date: date,
        slot_time: time,
        patient_id: Optional[str],
        patient_name: Optional[str],
        patient_email: Optional[str],
        patient_phone: Optional[str],
        duration_minutes: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the calendar event that matches the patient's existing booking."""
        slot_duration = duration_minutes or self.slot_minutes
        start_dt, _ = self._resolve_slot_interval(slot_date, slot_time, slot_duration)
        tolerance = timedelta(minutes=15)
        events: List[Dict[str, Any]] = []
        private_filters: Dict[str, str] = {}

        if patient_id:
            patient_id_str = str(patient_id).strip()
            if patient_id_str:
                private_filters["patient_id"] = patient_id_str

        if private_filters:
            events = self._list_events(
                calendar_id=calendar_id,
                time_min=start_dt - tolerance,
                time_max=start_dt + tolerance,
                private_extended=private_filters,
            )

        if not events:
            events = self._list_events(
                calendar_id=calendar_id,
                time_min=start_dt - tolerance,
                time_max=start_dt + tolerance,
            )

        for event in events:
            event_start = self._event_start_datetime(event)
            if not event_start:
                continue
            if (
                abs((event_start - start_dt).total_seconds())
                > tolerance.total_seconds()
            ):
                continue
            if self._event_matches_patient(
                event,
                patient_name=patient_name,
                patient_email=patient_email,
                patient_phone=patient_phone,
            ):
                return event
        return None

    def list_user_appointments(
        self, *, user_id: str, calendar_id: str
    ) -> List[Dict[str, Any]]:
        """List all appointments for a given user ID."""
        private_filters: Dict[str, str] = {}
        private_filters["patient_id"] = user_id
        now = datetime.now(pytz.timezone(self.timezone))
        days_ahead = 14  # Look for appointments in the next 14 days
        time_min = now
        time_max = now + timedelta(days=days_ahead)
        events = self._list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            private_extended=private_filters,
        )
        return events

    def reschedule_event(
        self,
        *,
        calendar_id: str,
        event_id: str,
        new_slot_date: date,
        new_slot_time: time,
        duration_minutes: Optional[int] = None,
        send_updates: str = "all",
    ) -> Dict[str, Any]:
        """Move an existing event to a new slot, ensuring the new slot is free."""
        slot_duration = duration_minutes or self.slot_minutes
        new_start_dt, new_end_dt = self._resolve_slot_interval(
            new_slot_date, new_slot_time, slot_duration
        )
        self._ensure_slot_is_free(calendar_id, new_start_dt, new_end_dt)
        event = self._update_event_time(
            calendar_id=calendar_id,
            event_id=event_id,
            start_dt=new_start_dt,
            end_dt=new_end_dt,
            send_updates=send_updates,
        )
        return self._serialize_event(event)

    def _fetch_busy_periods(
        self, calendar_id: str, start: datetime, end: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """Retrieve busy periods from Google Calendar."""
        body = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "timeZone": self.timezone,
            "items": [{"id": calendar_id}],
        }
        try:
            response = self._service.freebusy().query(body=body).execute()
        except HttpError as exc:
            error = f"Não foi possível consultar horários do Google Calendar: {exc.error_details}"
            logger.error(error)
            raise GoogleCalendarError(error) from exc

        calendar_info = response.get("calendars", {}).get(calendar_id, {})
        busy_info: Iterable[Dict[str, str]] = calendar_info.get("busy", [])

        busy_periods: List[Tuple[datetime, datetime]] = []
        for period in busy_info:
            start_dt = _parse_google_datetime(period.get("start"))
            end_dt = _parse_google_datetime(period.get("end"))
            if start_dt and end_dt:
                busy_periods.append((start_dt, end_dt))
        return busy_periods

    def _list_events(
        self,
        *,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 50,
        private_extended: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve events within the given window."""
        params: Dict[str, Any] = {
            "calendarId": calendar_id,
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "timeZone": self.timezone,
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": max_results,
        }
        if private_extended:
            params["privateExtendedProperty"] = [
                f"{key}={value}" for key, value in private_extended.items() if value
            ]
        try:
            response = self._service.events().list(**params).execute()
        except HttpError as exc:
            error = f"Não foi possível listar eventos do Google Calendar: {exc.error_details}"
            logger.error(error)
            raise GoogleCalendarError(error) from exc
        items = response.get("items", [])
        return items if isinstance(items, list) else []

    def _build_working_window(self, target_date: date) -> Tuple[datetime, datetime]:
        """Return start/end datetimes for the dentist working hours on `target_date`."""
        tz = pytz.timezone(self.timezone)
        start_dt = tz.localize(datetime.combine(target_date, self.working_hours.start))
        end_dt = tz.localize(datetime.combine(target_date, self.working_hours.end))
        return start_dt, end_dt

    def _generate_available_slots(
        self,
        window_start: datetime,
        window_end: datetime,
        busy_periods: Sequence[Tuple[datetime, datetime]],
    ) -> List[str]:
        """Return chronologically ordered HH:MM slots that are free in the window."""
        available: List[str] = []
        slot_delta = timedelta(minutes=self.slot_minutes)
        current_start = window_start
        while current_start + slot_delta <= window_end:
            current_end = current_start + slot_delta
            if self._slot_is_free(current_start, current_end, busy_periods):
                available.append(current_start.strftime("%H:%M"))
            current_start += slot_delta
        return available

    def _resolve_slot_interval(
        self, slot_date: date, slot_time: time, slot_duration: int
    ) -> Tuple[datetime, datetime]:
        """Build timezone-aware datetimes for the requested slot interval."""
        tz = pytz.timezone(self.timezone)
        start_dt = tz.localize(datetime.combine(slot_date, slot_time))
        end_dt = start_dt + timedelta(minutes=slot_duration)
        return start_dt, end_dt

    def _ensure_slot_is_free(
        self, calendar_id: str, start_dt: datetime, end_dt: datetime
    ) -> None:
        """Raise `SlotUnavailableError` if the slot overlaps with a busy period."""
        busy_periods = self._fetch_busy_periods(calendar_id, start_dt, end_dt)
        if not self._slot_is_free(start_dt, end_dt, busy_periods):
            error = "Horário indisponível no Google Calendar."
            logger.error(error)
            raise SlotUnavailableError(error)

    def _build_event_body(
        self,
        *,
        start_dt: datetime,
        end_dt: datetime,
        patient_name: str,
        patient_phone: Optional[str],
        patient_email: Optional[str],
        patient_id: Optional[str],
        notes: Optional[str],
        dentist_name: Optional[str],
        dentist_id: Optional[str],
    ) -> Dict[str, Any]:
        """Construct the payload sent to Google Calendar when creating events."""
        event_body: Dict[str, Any] = {
            "summary": f"Consulta - {patient_name}",
            "description": self._build_event_description(
                patient_name=patient_name,
                patient_phone=patient_phone,
                patient_email=patient_email,
                notes=notes,
                dentist_name=dentist_name,
            ),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": self.timezone},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": self.timezone},
        }

        # if patient_email and self._should_include_attendees():
        #     event_body["attendees"] = [{"email": patient_email}]

        if dentist_name:
            event_body.setdefault("location", dentist_name)

        extended_private = self._build_extended_properties(
            patient_id=patient_id,
            patient_phone=patient_phone,
            patient_email=patient_email,
            dentist_id=dentist_id,
        )
        if extended_private:
            event_body["extendedProperties"] = {"private": extended_private}

        return event_body

    @staticmethod
    def _build_event_description(
        *,
        patient_name: str,
        patient_phone: Optional[str],
        patient_email: Optional[str],
        notes: Optional[str],
        dentist_name: Optional[str],
    ) -> str:
        """Return a readable description that stores contextual booking details."""
        description_parts = [
            f"Paciente: {patient_name}",
            f"Telefone: {patient_phone or 'não informado'}",
        ]
        if patient_email:
            description_parts.append(f"Email: {patient_email}")
        if notes:
            description_parts.append(notes)
        if dentist_name:
            description_parts.append(f"Dentista: {dentist_name}")
        return "\n".join(description_parts)

    @staticmethod
    def _build_extended_properties(
        *,
        patient_id: Optional[str],
        patient_phone: Optional[str],
        patient_email: Optional[str],
        dentist_id: Optional[str],
    ) -> Dict[str, str]:
        """Prepare private extended properties to persist structured metadata."""
        props: Dict[str, str] = {}

        if patient_id:
            patient_id_str = str(patient_id).strip()
            if patient_id_str:
                props["patient_id"] = patient_id_str

        if patient_phone:
            phone_digits = GoogleCalendarService._only_digits(patient_phone)
            if phone_digits:
                props["patient_phone"] = phone_digits

        if patient_email:
            email_norm = patient_email.strip().lower()
            if email_norm:
                props["patient_email"] = email_norm

        if dentist_id:
            dentist_id_str = str(dentist_id).strip()
            if dentist_id_str:
                props["dentist_id"] = dentist_id_str

        return props

    def _create_event(
        self,
        *,
        calendar_id: str,
        body: Dict[str, Any],
        send_updates: str,
    ) -> Dict[str, Any]:
        """Call the Google API to create an event and handle API-specific errors."""
        try:
            return (
                self._service.events()
                .insert(calendarId=calendar_id, body=body, sendUpdates=send_updates)
                .execute()
            )
        except HttpError as exc:
            error = f"Falha ao criar evento no Google Calendar: {exc.error_details}"
            logger.error(error)
            raise GoogleCalendarError(error) from exc

    def _update_event_time(
        self,
        *,
        calendar_id: str,
        event_id: str,
        start_dt: datetime,
        end_dt: datetime,
        send_updates: str,
    ) -> Dict[str, Any]:
        """Patch an existing event with new start/end datetimes."""
        body = {
            "start": {"dateTime": start_dt.isoformat(), "timeZone": self.timezone},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": self.timezone},
        }
        try:
            return (
                self._service.events()
                .patch(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=body,
                    sendUpdates=send_updates,
                )
                .execute()
            )
        except HttpError as exc:  # pragma: no cover - network failures hard to mock
            error = f"Falha ao atualizar evento no Google Calendar: {exc.error_details}"
            logger.error(error)
            raise GoogleCalendarError(error) from exc

    def delete_event(
        self, *, calendar_id: str, event_id: str, send_updates: str = "all"
    ) -> None:
        """Remove an event from the calendar, notifying attendees when requested."""
        try:
            (
                self._service.events()
                .delete(
                    calendarId=calendar_id,
                    eventId=event_id,
                    sendUpdates=send_updates,
                )
                .execute()
            )
        except HttpError as exc:
            error = f"Falha ao deletar evento no Google Calendar: {exc.error_details}"
            logger.error(error)
            raise GoogleCalendarError(error) from exc

    @staticmethod
    def _serialize_event(event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract essential fields from the Google Calendar event response."""
        return {
            "event_id": event.get("id"),
            "html_link": event.get("htmlLink"),
            "hangout_link": event.get("hangoutLink"),
            "start": event.get("start"),
            "end": event.get("end"),
        }

    @staticmethod
    def _slot_is_free(
        slot_start: datetime,
        slot_end: datetime,
        busy: Sequence[Tuple[datetime, datetime]],
    ) -> bool:
        """Return `True` when the slot is disjoint from every busy period."""
        for busy_start, busy_end in busy:
            if max(slot_start, busy_start) < min(slot_end, busy_end):
                return False
        return True

    @staticmethod
    def _should_include_attendees() -> bool:
        """Decide whether the integration should add attendees to the event."""
        flag = os.getenv("GOOGLE_CALENDAR_INCLUDE_ATTENDEES", "false")
        return flag.lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _event_start_datetime(event: Dict[str, Any]) -> Optional[datetime]:
        """Parse the event's start datetime, ignoring all-day events."""
        start_info = event.get("start")
        if not isinstance(start_info, dict):
            return None
        start_dt_raw = start_info.get("dateTime")
        if not isinstance(start_dt_raw, str):
            return None
        return _parse_google_datetime(start_dt_raw)

    @staticmethod
    def _event_matches_patient(
        event: Dict[str, Any],
        *,
        patient_name: Optional[str],
        patient_email: Optional[str],
        patient_phone: Optional[str],
    ) -> bool:
        """Return True if the event seems to belong to the informed patient."""
        normalized_description = (event.get("description") or "").lower()
        normalized_summary = (event.get("summary") or "").lower()
        attendees = event.get("attendees") or []

        if patient_email:
            target_email = patient_email.strip().lower()
            if target_email:
                if target_email in normalized_description:
                    return True
                for attendee in attendees:
                    email = attendee.get("email")
                    if isinstance(email, str) and email.strip().lower() == target_email:
                        return True

        if patient_phone:
            target_phone = GoogleCalendarService._only_digits(patient_phone)
            if target_phone:
                description_digits = GoogleCalendarService._only_digits(
                    normalized_description
                )
                if target_phone in description_digits:
                    return True

        if patient_name:
            target_name = patient_name.strip().lower()
            if target_name and (
                target_name in normalized_summary
                or target_name in normalized_description
            ):
                return True

        return False

    @staticmethod
    def _only_digits(raw: str) -> str:
        """Utility to strip non-digit characters for phone comparisons."""
        return re.sub(r"\D", "", raw)


def _parse_google_datetime(value: Optional[str]) -> Optional[datetime]:
    """Convert Google Calendar datetime strings into aware `datetime` objects."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _parse_hhmm(raw: str) -> time:
    """Parse HH:MM strings into `time` objects, raising `GoogleCalendarError` on failure."""
    try:
        hour, minute = raw.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, TypeError) as exc:  # pragma: no cover - validated input
        raise GoogleCalendarError(
            "Formato de horário inválido. Use HH:MM."  # noqa: TRY003
        ) from exc


def _load_service_account_credentials() -> ServiceAccountCredentials:
    """Load service-account credentials from the supported environment sources."""
    json_raw = os.getenv("GOOGLE_CALENDAR_CREDENTIALS")
    if json_raw:
        try:
            info = json.loads(json_raw)
            return ServiceAccountCredentials.from_service_account_info(
                info, scopes=SCOPES
            )
        except json.JSONDecodeError as exc:
            error = f"Falha ao carregar credenciais do Google Calendar: {exc}"
            logger.error(error)
            raise GoogleCalendarError(
                "JSON inválido em GOOGLE_CALENDAR_CREDENTIALS."
            ) from exc

    file_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH")
    if file_path:
        if not os.path.exists(file_path):
            raise GoogleCalendarError(
                "Caminho de credenciais do Google Calendar não encontrado."  # noqa: TRY003
            )
        return ServiceAccountCredentials.from_service_account_file(
            file_path, scopes=SCOPES
        )

    raise GoogleCalendarError(
        "Configure as credenciais do Google Calendar via GOOGLE_CALENDAR_CREDENTIALS_*."
    )


_cached_service: Optional[GoogleCalendarService] = None


def get_google_calendar_service(force_refresh: bool = False) -> GoogleCalendarService:
    """Return a cached `GoogleCalendarService`, refreshing credentials when asked."""
    global _cached_service
    if force_refresh or _cached_service is None:
        _cached_service = GoogleCalendarService.from_env()
    return _cached_service
