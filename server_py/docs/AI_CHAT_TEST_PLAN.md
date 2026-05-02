# AI Chat Test Plan - SeatSurfing

## Obiettivo

Verificare che la chat AI:
- interpreti correttamente il linguaggio naturale;
- restituisca JSON valido;
- gestisca richieste incomplete;
- gestisca la conversazione;
- gestisca errori;
- gestisca richieste fuori contesto.

---

## Endpoint testato

POST /chat/

---

## Tecnologie

- pytest
- FastAPI TestClient
- mock OpenAI

---

## Esecuzione test

```bash
python -m pytest tests/test_chat_flow.py