import React, { useMemo, useRef, useState } from "react";
import Booking from "@/types/Booking";
import Space from "@/types/Space";

/**
 Componente frontend della chat AI.

 Flusso principale:
 1. L’utente scrive una richiesta in linguaggio naturale.
 2. Il messaggio viene inviato al backend FastAPI /chat/.
 3. FastAPI usa OpenAI per interpretare i dati.
 4. Se la richiesta è booking_request, il frontend cerca gli spazi disponibili.
 5. L’utente sceglie una scrivania tra le opzioni proposte.
 6. L’utente conferma.
 7. La prenotazione viene salvata tramite Booking.save().
 
 Le chiamate HTTP reali non sono scritte direttamente qui con fetch,
 tranne la chiamata alla chat FastAPI.
 Le API Seatsurfing sono incapsulate nei model:
 - Space.listAvailability(...) = GET disponibilità spazi
 - Booking.save() = POST creazione prenotazione
*/

type ChatOption = {
  label: string;
  value: string;
};

type Message = {
  role: "user" | "assistant";
  text: string;
  options?: ChatOption[];
};

type Props = {
  locationId?: string;
  locationName?: string;
  onBookingCreated?: () => void;
};

type ParsedBooking = {
  enter: string;
  leave: string;
};

type PendingBooking = {
  enter: Date;
  leave: Date;
  options: Space[];
  selectedSpace?: Space;
  stage: "choose_space" | "ask_subject" | "confirm";
  subject?: string;
};

function normalize(text: string) {
  return text.toLowerCase().trim();
}

function isYes(text: string) {
  return ["sì", "si", "ok", "confermo", "procedi", "va bene", "conferma"].includes(
    normalize(text),
  );
}

function isNo(text: string) {
  return ["no", "annulla", "cambia", "non confermo", "cambia desk"].includes(
    normalize(text),
  );
}

function isSkipSubject(text: string) {
  return ["no", "salta", "nessuno", "senza oggetto"].includes(normalize(text));
}

function formatDateTime(date: Date) {
  return date.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function findSpaceFromUserInput(text: string, options: Space[]) {
  const clean = normalize(text);

  // 1. Match esatto sul nome completo: "desk 13"
  const exactName = options.find(
    (space) => normalize(space.name) === clean,
  );
  if (exactName) return exactName;

  // 2. Se scrive solo numero: "13"
  const numberMatch = clean.match(/\d+/);
  if (numberMatch) {
    const requestedNumber = numberMatch[0];

    // Cerca il numero esatto nel nome del desk
    const exactDeskNumber = options.find((space) => {
      const spaceNumber = normalize(space.name).match(/\d+/)?.[0];
      return spaceNumber === requestedNumber;
    });

    if (exactDeskNumber) return exactDeskNumber;

    // Solo dopo: interpreta come numero opzione 1,2,3...
    const optionIndex = Number(requestedNumber) - 1;
    if (optionIndex >= 0 && optionIndex < options.length) {
      return options[optionIndex];
    }
  }

  return options.find((space) => normalize(space.name).includes(clean));
}

export default function ChatLauncher({
  locationId,
  locationName = "",
  onBookingCreated,
}: Props) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingBooking, setPendingBooking] = useState<PendingBooking | null>(
    null,
  );

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Ciao! Posso aiutarti a trovare e prenotare una scrivania.",
      options: [
        { label: "Prenota", value: "Vorrei prenotare" },
        {
          label: "Disponibilità",
          value: "Vorrei controllare la disponibilità",
        },
      ],
    },
  ]);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  const suggestions = useMemo(
    () => [
      "Vorrei prenotare",
      "Vorrei controllare la disponibilità",
      "Voglio annullare una prenotazione",
    ],
    [],
  );

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }, 0);
  };

  const addAssistantMessage = (
    baseMessages: Message[],
    text: string,
    options?: ChatOption[],
  ) => {
    setMessages([
      ...baseMessages,
      {
        role: "assistant",
        text,
        options,
      },
    ]);
    scrollToBottom();
  };

  const createBooking = async (
    baseMessages: Message[],
    bookingState: PendingBooking,
  ) => {
    if (!bookingState.selectedSpace) {
      addAssistantMessage(baseMessages, "Prima scegli una scrivania.");
      return;
    }

    try {
      const bookingLeave = new Date(bookingState.leave);
      bookingLeave.setSeconds(bookingLeave.getSeconds() - 1);

      const booking = new Booking();
      booking.subject = bookingState.subject || "Prenotazione via chat";
      booking.enter = bookingState.enter;
      booking.leave = bookingLeave;
      booking.space = bookingState.selectedSpace;

      await booking.save();  //POST creazione prenotazione
      // Qui viene inviata al backend Seatsurfing la prenotazione definitiva.
      // La chiamata HTTP è incapsulata nel metodo Booking.save()

      addAssistantMessage(
        baseMessages,
        `✅ Prenotazione completata!

📍 Area: ${locationName || "area selezionata"}
🪑 Scrivania: ${bookingState.selectedSpace.name}
🕘 Orario: ${formatDateTime(bookingState.enter)} - ${formatDateTime(
          bookingState.leave,
        )}
${bookingState.subject ? `📝 Oggetto: ${bookingState.subject}` : ""}`,
        [
          {
            label: "Prenota altro",
            value: "Vorrei prenotare un'altra scrivania domani dalle 9 alle 18",
          },
        ],
      );

      setPendingBooking(null);

      //Callback eseguita dopo una prenotazione
      //aggiorna la mappa e mostra lo spazio occupato
      if (onBookingCreated) {
        onBookingCreated();
      }
    } catch (_err) {
      addAssistantMessage(
        baseMessages,
        "Non sono riuscita a completare la prenotazione. Controlla login, disponibilità e area selezionata.",
      );
    }
  };

  const handlePendingBooking = async (
    baseMessages: Message[],
    text: string,
  ) => {
    if (!pendingBooking) return false;

    const cleanText = text.trim();

    if (pendingBooking.stage === "choose_space") {
      const selectedSpace = findSpaceFromUserInput(
        cleanText,
        pendingBooking.options,
      );

      if (!selectedSpace) {
        addAssistantMessage(
          baseMessages,
          "Non ho trovato quella scrivania tra le opzioni. Puoi cliccare un bottone oppure scrivere il nome, ad esempio Desk 12.",
          pendingBooking.options.map((space) => ({
            label: space.name,
            value: space.name,
          })),
        );
        return true;
      }

      const nextState: PendingBooking = {
        ...pendingBooking,
        selectedSpace,
        stage: "ask_subject",
      };

      setPendingBooking(nextState);

      addAssistantMessage(
        baseMessages,
        `Hai scelto ${selectedSpace.name}. Vuoi aggiungere un oggetto alla prenotazione?`,
        [
          { label: "Salta", value: "salta" },
          { label: "Riunione", value: "Riunione" },
          { label: "Smart working", value: "Smart working" },
        ],
      );

      return true;
    }

    if (pendingBooking.stage === "ask_subject") {
      const subject = isSkipSubject(cleanText) ? "" : cleanText;

      const nextState: PendingBooking = {
        ...pendingBooking,
        subject,
        stage: "confirm",
      };

      setPendingBooking(nextState);

      addAssistantMessage(
        baseMessages,
        `Confermi questa prenotazione?

📍 Area: ${locationName || "area selezionata"}
🪑 Scrivania: ${pendingBooking.selectedSpace?.name}
🕘 Orario: ${formatDateTime(pendingBooking.enter)} - ${formatDateTime(
          pendingBooking.leave,
        )}
${subject ? `📝 Oggetto: ${subject}` : ""}`,
        [
          { label: "Conferma", value: "conferma" },
          { label: "Cambia desk", value: "cambia desk" },
          { label: "Annulla", value: "annulla" },
        ],
      );

      return true;
    }

    if (pendingBooking.stage === "confirm") {
      if (isYes(cleanText)) {
        await createBooking(baseMessages, pendingBooking);
        return true;
      }

      if (normalize(cleanText) === "cambia desk") {
        setPendingBooking({
          ...pendingBooking,
          selectedSpace: undefined,
          stage: "choose_space",
        });

        addAssistantMessage(
          baseMessages,
          "Certo, scegli un'altra scrivania tra queste:",
          pendingBooking.options.map((space) => ({
            label: space.name,
            value: space.name,
          })),
        );

        return true;
      }

      if (isNo(cleanText)) {
        setPendingBooking(null);
        addAssistantMessage(
          baseMessages,
          "Va bene, ho annullato la procedura di prenotazione.",
        );
        return true;
      }

      addAssistantMessage(
        baseMessages,
        "Vuoi confermare la prenotazione?",
        [
          { label: "Conferma", value: "conferma" },
          { label: "Cambia desk", value: "cambia desk" },
          { label: "Annulla", value: "annulla" },
        ],
      );
      return true;
    }

    return false;
  };

  const prepareBookingFromOpenAI = async (
    baseMessages: Message[],
    parsed: ParsedBooking,
  ) => {
    if (!locationId) {
      addAssistantMessage(
        baseMessages,
        "Prima seleziona un'area nella schermata principale, poi posso prenotare.",
      );
      return;
    }

    const enter = new Date(parsed.enter);
    const leave = new Date(parsed.leave);

    if (isNaN(enter.getTime()) || isNaN(leave.getTime())) {
      addAssistantMessage(
        baseMessages,
        "Non sono riuscita a interpretare correttamente giorno e orario.",
      );
      return;
    }

    const searchLeave = new Date(leave);
    searchLeave.setSeconds(searchLeave.getSeconds() - 1);


    // GET disponibilità spazi.
    // Questa chiamata recupera dal backend Seatsurfing gli spazi disponibili
    // per l’area selezionata e per la fascia oraria richiesta.
    // La GET è incapsulata nel model Space, quindi qui non vediamo fetch diretto.
    const spaces = await Space.listAvailability(
      locationId,
      enter,
      searchLeave,
      [],
    );


    // Filtra solo le scrivanie realmente prenotabili:
    // - allowed: l’utente ha il permesso di prenotare quello spazio
    // - available: lo spazio è libero nella fascia richiesta
    const freeSpaces = spaces.filter((space) => space.allowed && space.available);

    if (freeSpaces.length === 0) {
      addAssistantMessage(
        baseMessages,
        "Non ho trovato scrivanie libere per questa fascia oraria. Vuoi provare un altro orario?",
        [
          {
            label: "Domani 9-18",
            value: "Vorrei prenotare domani dalle 9 alle 18",
          },
          {
            label: "Domani 10-17",
            value: "Vorrei prenotare domani dalle 10 alle 17",
          },
        ],
      );
      return;
    }

    const options = freeSpaces.slice(0, 5);

    setPendingBooking({
      enter,
      leave,
      options,
      stage: "choose_space",
    });

    addAssistantMessage(
      baseMessages,
      `Ho trovato ${options.length} scrivanie libere 😊
Scegli quella che preferisci:`,
      options.map((space) => ({
        label: space.name,
        value: space.name,
      })),
    );
  };

  const handleAvailability = async (
    baseMessages: Message[],
    parsed: ParsedBooking,
  ) => {
    if (!locationId) {
      addAssistantMessage(
        baseMessages,
        "Prima seleziona un'area nella schermata principale, poi posso controllare la disponibilità.",
      );
      return;
    }

    const enter = new Date(parsed.enter);
    const leave = new Date(parsed.leave);

    const searchLeave = new Date(leave);
    searchLeave.setSeconds(searchLeave.getSeconds() - 1);

    const spaces = await Space.listAvailability(
      locationId,
      enter,
      searchLeave,
      [],
    );

    const freeSpaces = spaces.filter((space) => space.allowed && space.available);

    if (freeSpaces.length === 0) {
      addAssistantMessage(
        baseMessages,
        "Non ho trovato scrivanie libere per quella fascia oraria.",
      );
      return;
    }

    addAssistantMessage(
      baseMessages,
      `Ho trovato ${freeSpaces.length} scrivanie disponibili.
Vuoi prenotarne una?`,
      [
        {
          label: "Sì, prenota",
          value: `Vorrei prenotare dal ${parsed.enter} al ${parsed.leave}`,
        },
        { label: "No", value: "no" },
      ],
    );
  };

  const sendMessage = async (customText?: string) => {
    const trimmed = (customText ?? input).trim();
    if (!trimmed || loading) return;

    const updatedMessages: Message[] = [
      ...messages,
      {
        role: "user",
        text: trimmed,
      },
    ];

    setMessages(updatedMessages);
    setInput("");
    setLoading(true);
    scrollToBottom();

    try {
      const handledPending = await handlePendingBooking(
        updatedMessages,
        trimmed,
      );

      if (handledPending) return;


      // POST verso il backend FastAPI della chat.
      // Qui il frontend invia il testo utente a /chat/.
      // FastAPI poi usa OpenAI per interpretare la richiesta e restituire:
      // - intent: booking_request, availability_request, chat, cancel_request
      // - parsed: enter/leave in formato ISO

      const res = await fetch("http://localhost:8000/chat/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmed,
          history: updatedMessages,
          locationId: locationId || "",
          locationName: locationName || "",
        }),
      });

      const data = await res.json();

      if (
        data.intent === "booking_request" &&
        data.parsed?.enter &&
        data.parsed?.leave
      ) {
        await prepareBookingFromOpenAI(updatedMessages, data.parsed);
        return;
      }

      if (
        data.intent === "availability_request" &&
        data.parsed?.enter &&
        data.parsed?.leave
      ) {
        await handleAvailability(updatedMessages, data.parsed);
        return;
      }

      if (data.intent === "cancel_request") {
        addAssistantMessage(
          updatedMessages,
          "Per ora posso aiutarti a creare prenotazioni reali. L'annullamento via chat sarà il prossimo step.",
        );
        return;
      }

      addAssistantMessage(
        updatedMessages,
        data.response ||
          data.detail ||
          "Non sono riuscita a generare una risposta.",
      );
    } catch (_err) {
      addAssistantMessage(
        updatedMessages,
        "Non riesco a collegarmi al backend della chat.",
      );
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        style={{
          position: "fixed",
          right: "24px",
          bottom: "24px",
          zIndex: 99999,
          background: "linear-gradient(135deg, #0d6efd, #3aa0ff)",
          color: "#fff",
          border: "none",
          borderRadius: "999px",
          padding: "14px 22px",
          fontSize: "16px",
          fontWeight: 700,
          cursor: "pointer",
          boxShadow: "0 10px 28px rgba(13,110,253,0.35)",
        }}
      >
        Chat
      </button>

      {open && (
        <div
          style={{
            position: "fixed",
            right: "24px",
            bottom: "84px",
            top: "16px",
            width: "420px",
            maxWidth: "calc(100vw - 32px)",
            height: "min(620px, calc(100vh - 120px))",
            backgroundColor: "#fff",
            borderRadius: "22px",
            boxShadow: "0 18px 48px rgba(0,0,0,0.22)",
            zIndex: 99999,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            border: "1px solid #e9ecef",
          }}
        >
          <div
            style={{
              background: "linear-gradient(135deg, #0d6efd, #3aa0ff)",
              color: "#fff",
              padding: "18px",
              fontWeight: 700,
              fontSize: "20px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              minHeight: "78px",
              flexShrink: 0,
            }}
          >
            <div>
              <div>Prenota con chat</div>
              <div
                style={{
                  fontSize: "12px",
                  opacity: 0.9,
                  fontWeight: 500,
                  marginTop: "4px",
                }}
              >
                Assistente AI per postazioni
              </div>
            </div>

            <button
              onClick={() => setOpen(false)}
              style={{
                background: "transparent",
                border: "none",
                color: "#fff",
                fontSize: "24px",
                cursor: "pointer",
              }}
            >
              ×
            </button>
          </div>

          <div
            style={{
              padding: "10px 12px",
              borderBottom: "1px solid #eef2f7",
              backgroundColor: "#f8fbff",
              display: "flex",
              gap: "8px",
              flexWrap: "wrap",
              flexShrink: 0,
            }}
          >
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => sendMessage(suggestion)}
                style={{
                  border: "1px solid #d0e3ff",
                  backgroundColor: "#fff",
                  color: "#0d6efd",
                  borderRadius: "999px",
                  padding: "8px 12px",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                {suggestion}
              </button>
            ))}
          </div>

          <div
            ref={scrollRef}
            style={{
              flex: 1,
              padding: "16px",
              backgroundColor: "#f7f9fc",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            {messages.map((msg, index) => (
              <div
                key={index}
                style={{
                  display: "flex",
                  justifyContent:
                    msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    background:
                      msg.role === "user"
                        ? "linear-gradient(135deg, #0d6efd, #2f8cff)"
                        : "#ffffff",
                    color: msg.role === "user" ? "#fff" : "#1f2937",
                    padding: "12px 14px",
                    borderRadius: "18px",
                    maxWidth: "82%",
                    fontSize: "14px",
                    lineHeight: "1.5",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  <div>{msg.text}</div>

                  {msg.options && msg.options.length > 0 && (
                    <div
                      style={{
                        marginTop: "10px",
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "8px",
                      }}
                    >
                      {msg.options.map((option, i) => (
                        <button
                          key={i}
                          onClick={() => sendMessage(option.value)}
                          style={{
                            padding: "7px 11px",
                            borderRadius: "999px",
                            border: "1px solid #0d6efd",
                            backgroundColor: "#fff",
                            color: "#0d6efd",
                            cursor: "pointer",
                            fontSize: "12px",
                            fontWeight: 600,
                          }}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div
                  style={{
                    backgroundColor: "#ffffff",
                    color: "#1f2937",
                    padding: "12px 14px",
                    borderRadius: "18px",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                    fontSize: "14px",
                  }}
                >
                  Sto cercando…
                </div>
              </div>
            )}
          </div>

          <div
            style={{
              padding: "12px",
              borderTop: "1px solid #e9ecef",
              backgroundColor: "#fff",
              display: "flex",
              gap: "8px",
              flexShrink: 0,
            }}
          >
            <input
              type="text"
              placeholder="Scrivi quello che vuoi..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              style={{
                flex: 1,
                padding: "12px 14px",
                borderRadius: "14px",
                border: "1px solid #ced4da",
                outline: "none",
                fontSize: "14px",
              }}
            />

            <button
              onClick={() => sendMessage()}
              disabled={loading}
              style={{
                background: "linear-gradient(135deg, #0d6efd, #3aa0ff)",
                color: "#fff",
                border: "none",
                borderRadius: "14px",
                padding: "0 18px",
                cursor: "pointer",
                fontWeight: 700,
                minWidth: "88px",
              }}
            >
              Invia
            </button>
          </div>
        </div>
      )}
    </>
  );
}