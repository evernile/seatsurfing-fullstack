import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_chat_endpoint_missing_location():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "In quale sede vuoi prenotare?",
      "intent": "chat",
      "parsed": {
        "enter": "2026-04-29T09:00:00",
        "leave": "2026-04-29T13:00:00",
        "locationId": null,
        "locationName": null
      },
      "missing_fields": ["location"],
      "next_action": "ask_clarification"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Prenota una scrivania domani dalle 9 alle 13",
                    "history": [],
                },
            )

    assert response.status_code == 200

    data = response.json()

    assert data["intent"] == "chat"
    assert data["next_action"] == "ask_clarification"
    assert "location" in data["missing_fields"]
    assert data["parsed"]["locationId"] is None
    assert data["parsed"]["locationName"] is None


def test_chat_endpoint_availability_request():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "Controllo le disponibilità per domani dalle 9 alle 13.",
      "intent": "availability_request",
      "parsed": {
        "enter": "2026-04-29T09:00:00",
        "leave": "2026-04-29T13:00:00",
        "locationId": "loc-1",
        "locationName": "Taranto"
      },
      "missing_fields": [],
      "next_action": "check_availability"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Ci sono scrivanie disponibili a Taranto domani dalle 9 alle 13?",
                    "history": [],
                    "locationId": "loc-1",
                    "locationName": "Taranto",
                },
            )

    assert response.status_code == 200

    data = response.json()

    assert data["intent"] == "availability_request"
    assert data["next_action"] == "check_availability"
    assert data["missing_fields"] == []
    assert data["parsed"]["locationId"] == "loc-1"
    assert data["parsed"]["locationName"] == "Taranto"


def test_chat_endpoint_modify_request():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "Va bene, posso aiutarti a modificare la richiesta.",
      "intent": "modify_request",
      "parsed": {
        "enter": "2026-04-29T14:00:00",
        "leave": "2026-04-29T18:00:00",
        "locationId": "loc-1",
        "locationName": "Taranto"
      },
      "missing_fields": [],
      "next_action": "check_availability"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Vorrei spostare la prenotazione al pomeriggio",
                    "history": [
                        {
                            "role": "user",
                            "text": "Prenota una scrivania a Taranto domani dalle 9 alle 13",
                        },
                        {
                            "role": "assistant",
                            "text": "Controllo la disponibilità per domani dalle 9 alle 13.",
                        },
                    ],
                    "locationId": "loc-1",
                    "locationName": "Taranto",
                },
            )

    assert response.status_code == 200

    data = response.json()

    assert data["intent"] == "modify_request"
    assert data["next_action"] == "check_availability"
    assert data["parsed"]["enter"] == "2026-04-29T14:00:00"
    assert data["parsed"]["leave"] == "2026-04-29T18:00:00"


def test_chat_endpoint_uses_history():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "Perfetto, controllo la disponibilità per Taranto domani dalle 9 alle 13.",
      "intent": "booking_request",
      "parsed": {
        "enter": "2026-04-29T09:00:00",
        "leave": "2026-04-29T13:00:00",
        "locationId": "loc-1",
        "locationName": "Taranto"
      },
      "missing_fields": [],
      "next_action": "check_availability"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Sì, Taranto",
                    "history": [
                        {
                            "role": "user",
                            "text": "Prenota una scrivania domani dalle 9 alle 13",
                        },
                        {
                            "role": "assistant",
                            "text": "In quale sede vuoi prenotare?",
                        },
                    ],
                    "locationId": "loc-1",
                    "locationName": "Taranto",
                },
            )

    assert response.status_code == 200

    data = response.json()

    assert data["intent"] == "booking_request"
    assert data["next_action"] == "check_availability"
    assert data["missing_fields"] == []
    assert data["parsed"]["locationName"] == "Taranto"


def test_chat_endpoint_selected_location_is_added_if_missing_from_openai():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "Controllo la disponibilità per domani dalle 9 alle 13.",
      "intent": "booking_request",
      "parsed": {
        "enter": "2026-04-29T09:00:00",
        "leave": "2026-04-29T13:00:00",
        "locationId": null,
        "locationName": null
      },
      "missing_fields": [],
      "next_action": "check_availability"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Prenota una scrivania domani dalle 9 alle 13",
                    "history": [],
                    "locationId": "loc-1",
                    "locationName": "Taranto",
                },
            )

    assert response.status_code == 200

    data = response.json()

    assert data["parsed"]["locationId"] == "loc-1"
    assert data["parsed"]["locationName"] == "Taranto"


def test_chat_endpoint_missing_openai_key():
    with patch.dict(os.environ, {}, clear=True):
        response = client.post(
            "/chat/",
            json={
                "message": "Prenota una scrivania domani dalle 9 alle 13",
                "history": [],
            },
        )

    assert response.status_code == 500
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_chat_endpoint_booking_request():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "Controllo la disponibilità per domani dalle 9 alle 13.",
      "intent": "booking_request",
      "parsed": {
        "enter": "2026-04-29T09:00:00",
        "leave": "2026-04-29T13:00:00",
        "locationId": "loc-1",
        "locationName": "Taranto"
      },
      "missing_fields": [],
      "next_action": "check_availability"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Prenota una scrivania a Taranto domani dalle 9 alle 13",
                    "history": [],
                    "locationId": "loc-1",
                    "locationName": "Taranto",
                },
            )

    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "booking_request"
    assert data["next_action"] == "check_availability"
    assert data["missing_fields"] == []


def test_chat_endpoint_missing_time():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "A che ora vuoi prenotare?",
      "intent": "chat",
      "parsed": {
        "enter": null,
        "leave": null,
        "locationId": "loc-1",
        "locationName": "Taranto"
      },
      "missing_fields": ["time"],
      "next_action": "ask_clarification"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Prenota una scrivania domani a Taranto",
                    "history": [],
                    "locationId": "loc-1",
                    "locationName": "Taranto",
                },
            )

    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "chat"
    assert data["next_action"] == "ask_clarification"
    assert "time" in data["missing_fields"]


def test_chat_endpoint_invalid_json_from_openai_uses_fallback():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = "Risposta non JSON"

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Prenota una scrivania",
                    "history": [],
                },
            )

    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "chat"
    assert data["next_action"] == "ask_clarification"
    assert "date" in data["missing_fields"]
    assert "time" in data["missing_fields"]


def test_chat_endpoint_cancel_request():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "Posso aiutarti ad annullare la prenotazione.",
      "intent": "cancel_request",
      "parsed": null,
      "missing_fields": [],
      "next_action": "cancel_booking"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Voglio annullare la mia prenotazione",
                    "history": [],
                },
            )

    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "cancel_request"
    assert data["next_action"] == "cancel_booking"


def test_chat_endpoint_out_of_scope_weather_question():
    fake_openai_response = MagicMock()
    fake_openai_response.output_text = """
    {
      "response": "Posso aiutarti solo con prenotazioni, disponibilità o gestione delle postazioni in SeatSurfing.",
      "intent": "out_of_scope",
      "parsed": null,
      "missing_fields": [],
      "next_action": "none"
    }
    """

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.api.chat.get_openai_client") as get_openai_client:
            get_openai_client.return_value.responses.create.return_value = fake_openai_response
            response = client.post(
                "/chat/",
                json={
                    "message": "Com'è il tempo oggi?",
                    "history": [],
                },
            )

    assert response.status_code == 200

    data = response.json()

    assert data["intent"] == "out_of_scope"
    assert data["next_action"] == "none"
    assert data["missing_fields"] == []
    assert data["parsed"]["enter"] is None
    assert data["parsed"]["leave"] is None
    assert data["parsed"]["locationId"] is None
    assert data["parsed"]["locationName"] is None


