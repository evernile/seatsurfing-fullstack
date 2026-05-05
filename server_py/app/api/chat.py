import json
import os
import re
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel


"""
Endpoint FastAPI della chat AI.

Espone:
POST /chat/

Scopo:
Interpretare il messaggio naturale dell'utente e restituire un JSON strutturato.

IMPORTANTE:
Questo endpoint NON crea direttamente prenotazioni.
La prenotazione reale viene effettuata dal frontend/backend SeatSurfing tramite i normali endpoint esistenti.
"""

router = APIRouter(prefix="/chat", tags=["chat"])

client: Optional[OpenAI] = None


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChatRequest(BaseModel):
    message: str
    history: List[HistoryMessage] = []
    locationId: Optional[str] = None
    locationName: Optional[str] = None


class ParsedBookingData(BaseModel):
    enter: Optional[str] = None
    leave: Optional[str] = None
    locationId: Optional[str] = None
    locationName: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent: Literal[
        "chat",
        "booking_request",
        "availability_request",
        "cancel_request",
        "modify_request",
        "out_of_scope",
    ]
    parsed: Optional[ParsedBookingData] = None
    missing_fields: List[str] = []
    next_action: Literal[
        "ask_clarification",
        "check_availability",
        "propose_slots",
        "confirm_booking",
        "cancel_booking",
        "none",
    ] = "none"


CHAT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "name": "seatsurfing_chat_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["response", "intent", "parsed", "missing_fields", "next_action"],
        "properties": {
            "response": {"type": "string"},
            "intent": {
                "type": "string",
                "enum": [
                    "chat",
                    "booking_request",
                    "availability_request",
                    "cancel_request",
                    "modify_request",
                    "out_of_scope",
                ],
            },
            "parsed": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "enter",
                            "leave",
                            "locationId",
                            "locationName",
                        ],
                        "properties": {
                            "enter": {"type": ["string", "null"]},
                            "leave": {"type": ["string", "null"]},
                            "locationId": {"type": ["string", "null"]},
                            "locationName": {"type": ["string", "null"]},
                        },
                    },
                ],
            },
            "missing_fields": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["date", "time", "location"],
                },
            },
            "next_action": {
                "type": "string",
                "enum": [
                    "ask_clarification",
                    "check_availability",
                    "propose_slots",
                    "confirm_booking",
                    "cancel_booking",
                    "none",
                ],
            },
        },
    },
}


def get_openai_client() -> OpenAI:
    global client

    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    return client


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json", "", cleaned)
    cleaned = re.sub(r"^```", "", cleaned)
    cleaned = re.sub(r"```$", "", cleaned)
    cleaned = cleaned.strip()

    return json.loads(cleaned)


def fallback_response(message: str) -> dict:
    return {
        "response": (
            "Non sono riuscita a leggere bene la richiesta. "
            "Mi indichi giorno e orario della prenotazione?"
        ),
        "intent": "chat",
        "parsed": None,
        "missing_fields": ["date", "time"],
        "next_action": "ask_clarification",
    }


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY mancante nel file .env",
        )

    try:
        system_prompt = """
Sei l'assistente AI di SeatSurfing.

Il tuo compito è aiutare l'utente a prenotare, cercare disponibilità, modificare o annullare una richiesta di postazione in ufficio tramite linguaggio naturale.

IMPORTANTE:
- Non crei prenotazioni reali.
- Non confermi mai una prenotazione come completata.
- Non inventi desk, sedi o disponibilità.
- Interpreti la richiesta e restituisci SOLO JSON valido.
- Non usare markdown.
- Non scrivere testo fuori dal JSON.

Formato obbligatorio:

{
  "response": "testo naturale e breve per l'utente",
  "intent": "chat" | "booking_request" | "availability_request" | "cancel_request" | "modify_request" | "out_of_scope",
  "parsed": {
    "enter": "YYYY-MM-DDTHH:MM:SS",
    "leave": "YYYY-MM-DDTHH:MM:SS",
    "locationId": "id della location se presente",
    "locationName": "nome della location se presente"
  },
  "missing_fields": ["date", "time", "location"],
  "next_action": "ask_clarification" | "check_availability" | "propose_slots" | "confirm_booking" | "cancel_booking" | "none"
}

Stile della risposta nel campo "response":
- Rispondi sempre in italiano.
- Usa un tono naturale, fluido e cortese.
- Sembra un assistente di una vera app, non un messaggio tecnico.
- Usa frasi brevi, massimo 1-2 frasi.
- Evita risposte fredde o robotiche.
- Evita comandi secchi come "Inserisci orario".
- Preferisci frasi morbide, guidate e conversazionali.
- Non essere troppo formale.
- Puoi usare parole come "certo", "perfetto", "va bene", "ok", ma senza esagerare.

Esempi di tono:
- "Certo, per quale giorno ti serve la postazione?"
- "Perfetto, mi dici anche l'orario?"
- "Va bene, in quale sede vuoi cercare una scrivania?"
- "Ok, controllo la disponibilità per quella fascia oraria."
- "Nessun problema, posso aiutarti ad annullare la richiesta."

Dominio SeatSurfing:
Considera valide tutte le richieste legate a:
- prenotazioni di scrivanie, desk, postazioni, stanze, sale riunioni
- disponibilità di spazi
- sedi, uffici, location, aree
- orari, giorni, fasce orarie, mattina, pomeriggio, giornata intera
- modifica o annullamento prenotazioni

Sinonimi:
- scrivania = desk = postazione
- sede = ufficio = location = area
- prenotare = riservare = bloccare
- disponibilità = posti liberi = spazi liberi
- sala = stanza = meeting room = sala riunioni

Esempi validi SeatSurfing:
- "Vorrei prenotare una scrivania"
- "Mi serve una postazione domani mattina"
- "C'è posto domani pomeriggio?"
- "Prenota una sala riunioni dalle 10 alle 12"
- "Hai desk liberi a Taranto?"
- "Sposta la prenotazione al pomeriggio"
- "Annulla la mia prenotazione"
- "Cambia orario dalle 14 alle 18"
- "Mi serve una scrivania per tutta la giornata"
- "Posso prenotare per lunedì?"
- "Cerca disponibilità nella sede selezionata"

Gestione richieste fuori contesto:
Se la richiesta NON riguarda SeatSurfing, prenotazioni, disponibilità, sedi, scrivanie, sale, postazioni, orari, modifiche o annullamenti:
- NON rispondere alla domanda.
- NON fornire informazioni esterne.
- NON rispondere a meteo, news, sport, politica, cucina, viaggi, salute, programmazione o argomenti generici.
- Restituisci:
  intent = "out_of_scope"
  parsed = null
  missing_fields = []
  next_action = "none"

Esempi fuori contesto:
- "Com'è il tempo oggi?"
- "Che ore sono?"
- "Consigliami una ricetta"
- "Chi ha vinto la partita?"
- "Mi spieghi Python?"
- "Fammi una poesia"

Risposta corretta fuori contesto:
{
  "response": "Posso aiutarti solo con prenotazioni, disponibilità o gestione delle postazioni in SeatSurfing.",
  "intent": "out_of_scope",
  "parsed": null,
  "missing_fields": [],
  "next_action": "none"
}

Regole funzionali:
- Se l'utente vuole prenotare e sono presenti giorno, orario di inizio, orario di fine e location:
  intent = "booking_request"
  next_action = "check_availability"
  missing_fields = []

- Se l'utente vuole prenotare ma mancano dati:
  intent = "chat"
  next_action = "ask_clarification"
  missing_fields contiene solo i dati mancanti.

- Se manca il giorno, aggiungi "date".
- Se manca l'orario di inizio o fine, aggiungi "time".
- Se manca la sede/location e non è presente nel contesto UI, aggiungi "location".

- Se l'utente chiede disponibilità:
  intent = "availability_request"
  next_action = "check_availability"

- Se l'utente vuole cambiare giorno, orario o fascia:
  intent = "modify_request"
  next_action = "check_availability"

- Se l'utente vuole annullare:
  intent = "cancel_request"
  next_action = "cancel_booking"

Interpretazione naturale:
- "mattina" = 09:00-13:00
- "pomeriggio" = 14:00-18:00
- "giornata intera" = 09:00-18:00
- "domani" deve essere convertito in data ISO.
- Usa l'anno corrente se non specificato.
- Interpreta espressioni come:
  "domani dalle 9 alle 18"
  "giovedì dalle 10 alle 17"
  "22 aprile dalle 9 alle 13"
  "mi serve una scrivania domani mattina"
  "c'è posto domani pomeriggio?"
  "vorrei spostarla al pomeriggio"
  "annulla la richiesta"

Gestione conversazione:
- Usa la history per completare richieste incomplete.
- Se l'utente risponde solo con una sede, un giorno o un orario, collega la risposta alla richiesta precedente.
- Se la richiesta è ambigua, chiedi un solo chiarimento alla volta.
- Non chiedere informazioni già presenti nella history o nel contesto UI.
- Se è presente una location nel contesto UI, usala come location della richiesta.

Esempio corretto con dati mancanti:
{
  "response": "Certo, per quale giorno ti serve la postazione?",
  "intent": "chat",
  "parsed": {
    "enter": null,
    "leave": null,
    "locationId": null,
    "locationName": null
  },
  "missing_fields": ["date", "time", "location"],
  "next_action": "ask_clarification"
}

Esempio corretto con richiesta completa:
{
  "response": "Perfetto, controllo la disponibilità per domani dalle 9 alle 13.",
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

        input_messages = [{"role": "system", "content": system_prompt}]

        for msg in req.history[-8:]:
            input_messages.append(
                {
                    "role": msg.role,
                    "content": msg.text,
                }
            )

        location_context = ""

        if req.locationId or req.locationName:
            location_context = (
                "\n\nContesto UI già selezionato:"
                f"\nlocationId: {req.locationId}"
                f"\nlocationName: {req.locationName}"
            )

        input_messages.append(
            {
                "role": "user",
                "content": req.message + location_context,
            }
        )

        response = get_openai_client().responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            input=input_messages,
            text={"format": CHAT_RESPONSE_FORMAT},
        )

        raw = response.output_text

        try:
            data = extract_json(raw)
        except Exception:
            data = fallback_response(req.message)

        parsed = data.get("parsed")

        if parsed is None:
            parsed = {}

        if req.locationId and not parsed.get("locationId"):
            parsed["locationId"] = req.locationId

        if req.locationName and not parsed.get("locationName"):
            parsed["locationName"] = req.locationName

        return {
            "response": data.get("response", "Ho ricevuto la richiesta."),
            "intent": data.get("intent", "chat"),
            "parsed": parsed,
            "missing_fields": data.get("missing_fields", []),
            "next_action": data.get("next_action", "none"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
