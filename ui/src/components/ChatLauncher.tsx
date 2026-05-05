import React, { useEffect, useMemo, useRef, useState } from "react";
import Booking from "@/types/Booking";
import Space from "@/types/Space";

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
  allOptions: Space[];
  visibleOptions: Space[];
  page: number;
  selectedSpace?: Space;
  stage: "choose_space" | "ask_subject" | "confirm";
  subject?: string;
};

const CHAT_STORAGE_KEY = "seatsurfing_chat_history";
const PAGE_SIZE = 5;

const initialMessages: Message[] = [
  {
    role: "assistant",
    text: "Ciao! Posso aiutarti a trovare una postazione, controllare la disponibilità o gestire le tue prenotazioni.",
    options: [
      { label: "Prenota", value: "Vorrei prenotare una scrivania" },
      { label: "Disponibilità", value: "Vorrei controllare la disponibilità" },
      { label: "Le mie prenotazioni", value: "quali sono le mie prenotazioni?" },
    ],
  },
];

function loadStoredMessages(): Message[] {
  if (typeof window === "undefined") return initialMessages;

  try {
    const saved = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!saved) return initialMessages;

    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) && parsed.length > 0
      ? parsed
      : initialMessages;
  } catch {
    return initialMessages;
  }
}

function normalize(text: string) {
  return text.toLowerCase().trim().replace(/[’']/g, " ");
}

function isYes(text: string) {
  return [
    "sì",
    "si",
    "ok",
    "confermo",
    "procedi",
    "va bene",
    "conferma",
    "conferma annullamento",
  ].includes(normalize(text));
}

function isNo(text: string) {
  return [
    "no",
    "annulla",
    "non annullare",
    "annulla operazione",
    "cambia",
    "non confermo",
    "cambia desk",
  ].includes(normalize(text));
}

function isSkipSubject(text: string) {
  return ["no", "salta", "nessuno", "senza oggetto"].includes(normalize(text));
}

function isListBookingsRequest(text: string) {
  const clean = normalize(text);

  return (
    clean.includes("mie prenotazioni") ||
    clean.includes("le mie prenotazioni") ||
    clean.includes("quali sono le mie prenotazioni") ||
    clean.includes("mostrami le prenotazioni") ||
    clean.includes("vedere le prenotazioni") ||
    clean.includes("prenotazioni attive") ||
    clean.includes("che prenotazioni ho")
  );
}

function isAskingForMoreOptions(text: string) {
  const clean = normalize(text);

  return (
    clean.includes("altre") ||
    clean.includes("altri") ||
    clean.includes("altro") ||
    clean.includes("mostrami") ||
    clean.includes("mostra") ||
    clean.includes("vedere altre") ||
    clean.includes("ce ne sono altre") ||
    clean.includes("ci sono altre") ||
    clean.includes("hai altre") ||
    clean.includes("altre disponibili") ||
    clean.includes("altre scrivanie")
  );
}

function isAskingForAllOptions(text: string) {
  const clean = normalize(text);

  return (
    clean.includes("tutte") ||
    clean.includes("tutti") ||
    clean.includes("tutto") ||
    clean.includes("fammi vedere tutto") ||
    clean.includes("mostrami tutto") ||
    clean.includes("mostrami tutte") ||
    clean.includes("tutte le scrivanie")
  );
}

function isAskingToChooseAnotherSpace(text: string) {
  const clean = normalize(text);

  return (
    clean.includes("altra scrivania") ||
    clean.includes("un altra scrivania") ||
    clean.includes("altro desk") ||
    clean.includes("un altro desk") ||
    clean.includes("altra postazione") ||
    clean.includes("un altra postazione") ||
    clean.includes("vorrei prenotare un altra") ||
    clean.includes("voglio un altra") ||
    clean.includes("vorrei sceglierne un altra") ||
    clean.includes("sceglierne un altra") ||
    clean.includes("ne vorrei un altra")
  );
}

function isRejectingCurrentOption(text: string) {
  const clean = normalize(text);

  return (
    clean.includes("non questa") ||
    clean.includes("questa no") ||
    clean.includes("non mi piace") ||
    clean.includes("non va bene") ||
    clean.includes("scegline un altra") ||
    clean.includes("scegli un altra") ||
    clean.includes("non voglio piu questo desk") ||
    clean.includes("non voglio questo desk") ||
    clean.includes("non voglio piu questa scrivania") ||
    clean.includes("voglio cambiare desk")
  );
}

function isAskingForBetterOption(text: string) {
  const clean = normalize(text);

  return (
    clean.includes("meglio") ||
    clean.includes("migliore") ||
    clean.includes("piu tranquilla") ||
    clean.includes("più tranquilla") ||
    clean.includes("piu comoda") ||
    clean.includes("più comoda") ||
    clean.includes("qualcosa di meglio")
  );
}

function isChangingTime(text: string) {
  const clean = normalize(text);

  return (
    clean.includes("cambio orario") ||
    clean.includes("cambiare orario") ||
    clean.includes("altro orario") ||
    clean.includes("nuovo orario") ||
    clean.includes("facciamo dalle") ||
    clean.includes("facciamo") ||
    clean.includes("meglio dalle") ||
    /\b\d{1,2}\s*[-:]\s*\d{1,2}\b/.test(clean) ||
    /\bdalle\s*\d{1,2}/.test(clean)
  );
}

function isAvailabilityQuestionForDesk(text: string) {
  const clean = normalize(text);

  return (
    /desk\s*\d+/.test(clean) &&
    (clean.includes("libero") ||
      clean.includes("libera") ||
      clean.includes("disponibile") ||
      clean.includes("disponibili") ||
      clean.includes("c e") ||
      clean.includes("ce") ||
      clean.includes("posso"))
  );
}

function extractDeskName(text: string) {
  const clean = normalize(text);
  const match = clean.match(/desk\s*(\d+)/);

  if (!match) return null;

  return `Desk ${match[1]}`;
}

function getOrdinalIndex(text: string): number | null {
  const clean = normalize(text);

  if (clean.includes("prima")) return 0;
  if (clean.includes("seconda")) return 1;
  if (clean.includes("terza")) return 2;
  if (clean.includes("quarta")) return 3;
  if (clean.includes("quinta")) return 4;

  return null;
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

function formatTimeRange(enter: Date, leave: Date) {
  return `${formatDateTime(enter)} - ${formatDateTime(leave)}`;
}

function findSpaceFromUserInput(text: string, options: Space[]) {
  const clean = normalize(text);

  const exactName = options.find((space) => normalize(space.name) === clean);
  if (exactName) return exactName;

  const deskNumberMatch = clean.match(/desk\s*(\d+)/);
  if (deskNumberMatch) {
    const requestedNumber = deskNumberMatch[1];

    return options.find((space) => {
      const spaceNumber = normalize(space.name).match(/desk\s*(\d+)/)?.[1];
      return spaceNumber === requestedNumber;
    });
  }

  const onlyNumberMatch = clean.match(/^\d+$/);
  if (onlyNumberMatch) {
    const requestedNumber = onlyNumberMatch[0];

    const exactDeskNumber = options.find((space) => {
      const spaceNumber = normalize(space.name).match(/desk\s*(\d+)/)?.[1];
      return spaceNumber === requestedNumber;
    });

    if (exactDeskNumber) return exactDeskNumber;

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

  const [pendingCancelBooking, setPendingCancelBooking] =
    useState<Booking | null>(null);

  const [messages, setMessages] = useState<Message[]>(loadStoredMessages);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const suggestions = useMemo(
    () => [
      "Vorrei prenotare una scrivania",
      "Vorrei controllare la disponibilità",
      "Le mie prenotazioni",
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

  const resetChat = () => {
    setMessages(initialMessages);
    setPendingBooking(null);
    setPendingCancelBooking(null);
    localStorage.removeItem(CHAT_STORAGE_KEY);
  };

  const getOptionButtons = (
    spaces: Space[],
    includeMoreButton: boolean,
  ): ChatOption[] => {
    const options = spaces.map((space) => ({
      label: space.name,
      value: space.name,
    }));

    if (includeMoreButton) {
      options.push({
        label: "Mostra altre",
        value: "mostra altre scrivanie",
      });
    }

    return options;
  };

  const createBooking = async (
    baseMessages: Message[],
    bookingState: PendingBooking,
  ) => {
    if (!bookingState.selectedSpace) {
      addAssistantMessage(
        baseMessages,
        "Quasi fatto! Prima scegli una scrivania tra quelle disponibili.",
      );
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

      await booking.save();

      addAssistantMessage(
        baseMessages,
        `Prenotazione completata!

📍 Area: ${locationName || "area selezionata"}
🪑 Scrivania: ${bookingState.selectedSpace.name}
🕘 Orario: ${formatTimeRange(bookingState.enter, bookingState.leave)}
${bookingState.subject ? `📝 Oggetto: ${bookingState.subject}` : ""}`,
        [
          {
            label: "Prenota altro",
            value: "Vorrei prenotare un'altra scrivania domani dalle 9 alle 18",
          },
          {
            label: "Le mie prenotazioni",
            value: "quali sono le mie prenotazioni?",
          },
        ],
      );

      setPendingBooking(null);

      if (onBookingCreated) {
        onBookingCreated();
      }
    } catch (err) {
      console.error("ERRORE BOOKING:", err);

      addAssistantMessage(
        baseMessages,
        "Non sono riuscito a completare la prenotazione. Controlla login, disponibilità e area selezionata.",
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
      const hasMore =
        pendingBooking.visibleOptions.length < pendingBooking.allOptions.length;

      if (isChangingTime(cleanText)) {
        setPendingBooking(null);

        addAssistantMessage(
          baseMessages,
          "Va bene, dimmi pure il nuovo giorno e orario, così controllo di nuovo le disponibilità.",
        );

        return true;
      }

      if (isAskingForAllOptions(cleanText)) {
        setPendingBooking({
          ...pendingBooking,
          options: pendingBooking.allOptions,
          visibleOptions: pendingBooking.allOptions,
          page: Math.ceil(pendingBooking.allOptions.length / PAGE_SIZE),
        });

        addAssistantMessage(
          baseMessages,
          `Certo! Ecco tutte le ${pendingBooking.allOptions.length} scrivanie disponibili per questa fascia:`,
          getOptionButtons(pendingBooking.allOptions, false),
        );

        return true;
      }

      if (
        isAskingToChooseAnotherSpace(cleanText) ||
        isRejectingCurrentOption(cleanText)
      ) {
        addAssistantMessage(
          baseMessages,
          `Sì certo, ti mostro le opzioni disponibili.

Puoi scegliere una di queste oppure chiedermi di mostrartene altre:`,
          getOptionButtons(pendingBooking.visibleOptions, hasMore),
        );

        return true;
      }

      if (isAskingForBetterOption(cleanText)) {
        addAssistantMessage(
          baseMessages,
          "Posso mostrarti altre scrivanie disponibili. Vuoi vedere altre opzioni?",
          [
            { label: "Sì, mostrami altre", value: "mostra altre scrivanie" },
            { label: "No, scelgo tra queste", value: "no" },
          ],
        );

        return true;
      }

      if (isAskingForMoreOptions(cleanText)) {
        const nextPage = pendingBooking.page + 1;
        const start = nextPage * PAGE_SIZE;
        const end = start + PAGE_SIZE;
        const nextOptions = pendingBooking.allOptions.slice(start, end);

        if (nextOptions.length === 0) {
          addAssistantMessage(
            baseMessages,
            `Ti ho già mostrato tutte le ${pendingBooking.allOptions.length} scrivanie disponibili per questa fascia.

Puoi sceglierne una tra quelle già proposte oppure provare un altro orario.`,
            [
              ...getOptionButtons(pendingBooking.visibleOptions, false),
              {
                label: "Prova altro orario",
                value: "Vorrei provare un altro orario",
              },
            ],
          );

          return true;
        }

        const updatedVisibleOptions = [
          ...pendingBooking.visibleOptions,
          ...nextOptions,
        ];

        const stillHasMore =
          updatedVisibleOptions.length < pendingBooking.allOptions.length;

        setPendingBooking({
          ...pendingBooking,
          options: updatedVisibleOptions,
          visibleOptions: updatedVisibleOptions,
          page: nextPage,
        });

        addAssistantMessage(
          baseMessages,
          `Certo, ti mostro altre ${nextOptions.length} scrivanie disponibili:`,
          getOptionButtons(nextOptions, stillHasMore),
        );

        return true;
      }

      if (isAvailabilityQuestionForDesk(cleanText)) {
        const requestedDeskName = extractDeskName(cleanText);

        const requestedDesk = pendingBooking.allOptions.find(
          (space) =>
            normalize(space.name) === normalize(requestedDeskName || ""),
        );

        if (requestedDesk) {
          addAssistantMessage(
            baseMessages,
            `${requestedDesk.name} è disponibile in questa fascia, vuoi selezionarlo?`,
            [
              { label: `Sì, ${requestedDesk.name}`, value: requestedDesk.name },
              { label: "Mostrami gli altri", value: "mostra altre scrivanie" },
            ],
          );
          return true;
        }

        addAssistantMessage(
          baseMessages,
          `${
            requestedDeskName || "Quel desk"
          } non risulta disponibile in questa fascia oraria.

Puoi scegliere una delle scrivanie disponibili oppure chiedermi di mostrartene altre:`,
          getOptionButtons(pendingBooking.visibleOptions, hasMore),
        );

        return true;
      }

      const ordinalIndex = getOrdinalIndex(cleanText);

      if (ordinalIndex !== null) {
        const selectedByOrdinal = pendingBooking.visibleOptions[ordinalIndex];

        if (selectedByOrdinal) {
          setPendingBooking({
            ...pendingBooking,
            selectedSpace: selectedByOrdinal,
            stage: "ask_subject",
          });

          addAssistantMessage(
            baseMessages,
            `Perfetto, hai scelto ${selectedByOrdinal.name}. Vuoi aggiungere un oggetto alla prenotazione?`,
            [
              { label: "Salta", value: "salta" },
              { label: "Riunione", value: "Riunione" },
              { label: "Smart working", value: "Smart working" },
            ],
          );

          return true;
        }
      }

      const selectedSpace = findSpaceFromUserInput(
        cleanText,
        pendingBooking.allOptions,
      );

      if (!selectedSpace) {
        addAssistantMessage(
          baseMessages,
          `Non ho trovato una corrispondenza tra le scrivanie disponibili.

Dimmi il nome della scrivania che preferisci, oppure chiedimi di mostrartene altre:`,
          getOptionButtons(pendingBooking.visibleOptions, hasMore),
        );

        return true;
      }

      setPendingBooking({
        ...pendingBooking,
        selectedSpace,
        stage: "ask_subject",
      });

      addAssistantMessage(
        baseMessages,
        `Perfetto, hai scelto ${selectedSpace.name}. Vuoi aggiungere un oggetto alla prenotazione?`,
        [
          { label: "Salta", value: "salta" },
          { label: "Riunione", value: "Riunione" },
          { label: "Smart working", value: "Smart working" },
        ],
      );

      return true;
    }

    if (pendingBooking.stage === "ask_subject") {
      const clean = normalize(cleanText);

      if (
        clean.includes("cambia desk") ||
        clean.includes("cambiare desk") ||
        clean.includes("voglio cambiare desk") ||
        clean.includes("non voglio questo desk") ||
        clean.includes("non voglio piu questo desk") ||
        clean.includes("non questo desk") ||
        clean.includes("questo desk no") ||
        clean.includes("altra scrivania") ||
        clean.includes("un altra scrivania") ||
        clean.includes("altro desk") ||
        clean.includes("un altro desk") ||
        clean.includes("non questa") ||
        clean.includes("questa no")
      ) {
        const hasMore =
          pendingBooking.visibleOptions.length <
          pendingBooking.allOptions.length;

        setPendingBooking({
          ...pendingBooking,
          selectedSpace: undefined,
          subject: undefined,
          stage: "choose_space",
        });

        addAssistantMessage(
          baseMessages,
          `Certo, nessun problema: cambiamo scrivania.

Scegli un'altra opzione tra quelle disponibili:`,
          getOptionButtons(pendingBooking.visibleOptions, hasMore),
        );

        return true;
      }

      if (clean.includes("annulla")) {
        setPendingBooking(null);

        addAssistantMessage(
          baseMessages,
          "Va bene, ho annullato la procedura di prenotazione. Quando vuoi possiamo ricominciare.",
        );

        return true;
      }

      const subject = isSkipSubject(cleanText) ? "" : cleanText;

      setPendingBooking({
        ...pendingBooking,
        subject,
        stage: "confirm",
      });

      addAssistantMessage(
        baseMessages,
        `Ti riepilogo tutto prima di confermare.

📍 Area: ${locationName || "area selezionata"}
🪑 Scrivania: ${pendingBooking.selectedSpace?.name}
🕘 Orario: ${formatTimeRange(pendingBooking.enter, pendingBooking.leave)}
${subject ? `📝 Oggetto: ${subject}` : ""}

Vuoi confermare la prenotazione?`,
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
        const hasMore =
          pendingBooking.visibleOptions.length <
          pendingBooking.allOptions.length;

        setPendingBooking({
          ...pendingBooking,
          selectedSpace: undefined,
          stage: "choose_space",
        });

        addAssistantMessage(
          baseMessages,
          "Certo, scegli un'altra scrivania tra quelle disponibili:",
          getOptionButtons(pendingBooking.visibleOptions, hasMore),
        );

        return true;
      }

      if (isNo(cleanText)) {
        setPendingBooking(null);

        addAssistantMessage(
          baseMessages,
          "Va bene, ho annullato la procedura di prenotazione. Quando vuoi possiamo ricominciare.",
        );

        return true;
      }

      addAssistantMessage(baseMessages, "Vuoi confermare la prenotazione?", [
        { label: "Conferma", value: "conferma" },
        { label: "Cambia desk", value: "cambia desk" },
        { label: "Annulla", value: "annulla" },
      ]);

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
        "Prima seleziona un'area nella schermata principale, poi posso cercare una postazione per te.",
      );
      return;
    }

    const enter = new Date(parsed.enter);
    const leave = new Date(parsed.leave);

    if (isNaN(enter.getTime()) || isNaN(leave.getTime())) {
      addAssistantMessage(
        baseMessages,
        "Non sono riuscita a interpretare bene giorno e orario. Puoi riscrivermeli, ad esempio: domani dalle 9 alle 13?",
      );
      return;
    }

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
        `Non ho trovato scrivanie libere per ${formatTimeRange(
          enter,
          leave,
        )}. Vuoi provare con un altro orario?`,
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

    const visibleOptions = freeSpaces.slice(0, PAGE_SIZE);
    const hasMore = visibleOptions.length < freeSpaces.length;

    setPendingBooking({
      enter,
      leave,
      options: visibleOptions,
      allOptions: freeSpaces,
      visibleOptions,
      page: 0,
      stage: "choose_space",
    });

    addAssistantMessage(
      baseMessages,
      `Ho trovato ${freeSpaces.length} scrivanie disponibili.

Ti mostro le prime ${visibleOptions.length}. Scegli quella che preferisci oppure chiedimi di mostrartene altre:`,
      getOptionButtons(visibleOptions, hasMore),
    );
  };

  const handleAvailability = async (
    baseMessages: Message[],
    parsed: ParsedBooking,
  ) => {
    await prepareBookingFromOpenAI(baseMessages, parsed);
  };

  const handleListBookingsRequest = async (baseMessages: Message[]) => {
    try {
      const bookings = await Booking.list();

      if (!bookings || bookings.length === 0) {
        addAssistantMessage(
          baseMessages,
          "Non hai prenotazioni attive al momento.",
          [
            {
              label: "Prenota una scrivania",
              value: "Vorrei prenotare una scrivania",
            },
          ],
        );
        return;
      }

      const sortedBookings = bookings.sort(
        (a, b) => new Date(a.enter).getTime() - new Date(b.enter).getTime(),
      );

      const bookingsText = sortedBookings
        .slice(0, 5)
        .map((booking, index) => {
          return `${index + 1}. ${booking.space.location.name}, ${
            booking.space.name
          }
${formatTimeRange(booking.enter, booking.leave)}${
            booking.subject ? `\nOggetto: ${booking.subject}` : ""
          }`;
        })
        .join("\n\n");

      addAssistantMessage(
        baseMessages,
        `Ecco le tue prossime prenotazioni:\n\n${bookingsText}`,
        [
          { label: "Annulla ultima", value: "annulla ultima prenotazione" },
          { label: "Prenota altro", value: "Vorrei prenotare una scrivania" },
        ],
      );
    } catch (err) {
      console.error("ERRORE LIST BOOKINGS:", err);

      addAssistantMessage(
        baseMessages,
        "Non sono riuscito a recuperare le tue prenotazioni.",
      );
    }
  };

  const handleCancelRequest = async (baseMessages: Message[]) => {
    try {
      const bookings = await Booking.list();

      if (!bookings || bookings.length === 0) {
        addAssistantMessage(
          baseMessages,
          "Non hai prenotazioni attive da annullare.",
        );
        return;
      }

      const sortedBookings = bookings.sort(
        (a, b) => new Date(b.enter).getTime() - new Date(a.enter).getTime(),
      );

      const lastBooking = sortedBookings[0];

      setPendingCancelBooking(lastBooking);

      addAssistantMessage(
        baseMessages,
        `Ho trovato questa prenotazione da annullare:

📍 Area: ${lastBooking.space.location.name}
🪑 Scrivania: ${lastBooking.space.name}
🕘 Orario: ${formatTimeRange(lastBooking.enter, lastBooking.leave)}
${lastBooking.subject ? `📝 Oggetto: ${lastBooking.subject}` : ""}

Vuoi confermare l'annullamento?`,
        [
          { label: "Conferma annullamento", value: "conferma annullamento" },
          { label: "Non annullare", value: "non annullare" },
        ],
      );
    } catch (err) {
      console.error("ERRORE CANCEL BOOKING:", err);

      addAssistantMessage(
        baseMessages,
        "Non riesco a recuperare le tue prenotazioni da annullare.",
      );
    }
  };

  const handlePendingCancel = async (
    baseMessages: Message[],
    text: string,
  ) => {
    if (!pendingCancelBooking) return false;

    const clean = normalize(text);

    if (clean.includes("conferma")) {
      try {
        await pendingCancelBooking.delete();

        addAssistantMessage(
          baseMessages,
          "Prenotazione annullata con successo.",
          [
            {
              label: "Prenota altro",
              value: "Vorrei prenotare una scrivania",
            },
            {
              label: "Le mie prenotazioni",
              value: "quali sono le mie prenotazioni?",
            },
          ],
        );

        setPendingCancelBooking(null);

        if (onBookingCreated) {
          onBookingCreated();
        }
      } catch (err) {
        console.error("ERRORE DELETE BOOKING:", err);

        addAssistantMessage(
          baseMessages,
          "Non sono riuscito ad annullare la prenotazione.",
        );
      }

      return true;
    }

    if (
      clean.includes("non annullare") ||
      clean.includes("annulla operazione") ||
      clean === "no"
    ) {
      setPendingCancelBooking(null);

      addAssistantMessage(baseMessages, "Va bene, non ho annullato nulla.");

      return true;
    }

    addAssistantMessage(
      baseMessages,
      "Vuoi confermare l'annullamento della prenotazione?",
      [
        { label: "Conferma annullamento", value: "conferma annullamento" },
        { label: "Non annullare", value: "non annullare" },
      ],
    );

    return true;
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
      const clean = normalize(trimmed);

      const handledCancel = await handlePendingCancel(updatedMessages, trimmed);
      if (handledCancel) return;

      const handledPending = await handlePendingBooking(
        updatedMessages,
        trimmed,
      );

      if (handledPending) return;

      if (isListBookingsRequest(trimmed)) {
        await handleListBookingsRequest(updatedMessages);
        return;
      }

      if (!pendingBooking && clean.includes("desk")) {
        addAssistantMessage(
          updatedMessages,
          "Prima dimmi giorno e orario, poi ti mostro le scrivanie disponibili.",
        );
        return;
      }

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
        await handleCancelRequest(updatedMessages);
        return;
      }

      if (data.intent === "out_of_scope") {
        addAssistantMessage(
          updatedMessages,
          data.response ||
            "Posso aiutarti con prenotazioni e disponibilità delle postazioni. Vuoi cercare una scrivania?",
        );
        return;
      }

      addAssistantMessage(
        updatedMessages,
        data.response ||
          data.detail ||
          "Non ho capito benissimo. Puoi riscrivere la richiesta?",
      );
    } catch (_err) {
      addAssistantMessage(
        updatedMessages,
        "Non riesco a collegarmi al backend della chat. Controlla che FastAPI sia avviato.",
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

            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <button
                onClick={resetChat}
                title="Cancella chat"
                style={{
                  background: "rgba(255,255,255,0.18)",
                  border: "1px solid rgba(255,255,255,0.35)",
                  color: "#fff",
                  fontSize: "12px",
                  cursor: "pointer",
                  borderRadius: "999px",
                  padding: "6px 10px",
                  fontWeight: 600,
                }}
              >
                Reset
              </button>

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
              placeholder="Scrivi la tua richiesta..."
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
                cursor: loading ? "not-allowed" : "pointer",
                fontWeight: 700,
                minWidth: "88px",
                opacity: loading ? 0.7 : 1,
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