# AI Assistant Flow - SeatSurfing Chat

## Obiettivo

L’assistente AI di SeatSurfing consente all’utente di interagire con il sistema tramite linguaggio naturale per:

- cercare disponibilità di postazioni, desk o sale;
- richiedere una prenotazione;
- modificare una richiesta;
- annullare una richiesta;
- ricevere chiarimenti quando mancano dati.

L’assistente non esegue direttamente azioni reali sul sistema.  
Il suo compito è interpretare il messaggio dell’utente e restituire un JSON strutturato che il frontend/backend può usare per proseguire il flusso.

---

## Architettura logica

Utente  
→ Chat UI  
→ Endpoint FastAPI `/chat/`  
→ OpenAI  
→ JSON strutturato  
→ Frontend/backend SeatSurfing  
→ Azione reale tramite endpoint esistenti

---

## Principio fondamentale

La chat AI è un livello di interpretazione.

Non deve:

- creare direttamente prenotazioni;
- confermare prenotazioni non ancora salvate;
- inventare disponibilità;
- inventare desk, sedi o orari;
- rispondere a richieste fuori dal dominio SeatSurfing.

---

## Intent supportati

L’assistente può restituire i seguenti intent:

| Intent | Significato |
|---|---|
| `chat` | Conversazione di supporto o richiesta incompleta |
| `booking_request` | L’utente vuole prenotare |
| `availability_request` | L’utente chiede disponibilità |
| `modify_request` | L’utente vuole modificare giorno/orario/fascia |
| `cancel_request` | L’utente vuole annullare |
| `out_of_scope` | La richiesta non riguarda SeatSurfing |

---

## Struttura della risposta

L’assistente restituisce sempre JSON valido:

```json
{
  "response": "testo naturale e breve per l'utente",
  "intent": "chat",
  "parsed": {
    "enter": null,
    "leave": null,
    "locationId": null,
    "locationName": null
  },
  "missing_fields": [],
  "next_action": "none"
}