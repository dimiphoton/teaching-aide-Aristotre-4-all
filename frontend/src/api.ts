// Client de l'API du kiosque (même origine que l'interface).

export interface Student { index: number; pseudo: string }
export interface ItemInfo {
  index: number; notion: string; notion_title: string; question: string;
  status: "en_cours" | "valide" | "verrouille" | "abandonne"; errors: number; max_errors: number;
}
export interface KioskState {
  kiosk: string;
  students: Student[];
  active: { index: number; pseudo: string } | null;
  item: ItemInfo | null;
  course: { id: string; title: string; subject: string };
  capabilities: { camera: boolean; microphone: boolean; printer: boolean; keyboard_buttons: boolean };
  mode: string;
}
export interface TutorTurn {
  reply: string; action: string; verdict: string | null; nature: string | null; misconception: string | null;
  errors: number; max_errors: number; item_status: string; ticket_printed: boolean; item: ItemInfo | null;
}
export interface Capture { capture_id: string; text: string; confidence: number | null; page_found?: boolean; image?: string }
export interface KioskEvent { type: string; payload: Record<string, unknown>; ts: number }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function call<T>(method: string, path: string, body?: unknown, headers: Record<string, string> = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try { detail = (await response.json()).detail ?? detail; } catch { /* réponse non JSON */ }
    throw new ApiError(response.status, typeof detail === "string" ? detail : "Erreur");
  }
  return response.json() as Promise<T>;
}

export const api = {
  state: () => call<KioskState>("GET", "/state"),
  select: (index: number) => call<KioskState>("POST", `/students/${index}/select`),
  endSession: () => call<KioskState>("POST", "/session/end"),
  key: (key: string, long: boolean) => call<{ handled: boolean }>("POST", "/keys", { key, long }),
  next: () => call<{ done: boolean; item: ItemInfo | null }>("POST", "/tutor/next"),
  answer: (text: string, mode = "saisie", capture_id?: string) =>
    call<TutorTurn>("POST", "/tutor/answer", { text, mode, capture_id }),
  printQuestion: () => call<{ printed: boolean }>("POST", "/tutor/print"),
  scan: () => call<Capture>("POST", "/scan"),
  dictationStart: () => call<{ recording: boolean }>("POST", "/dictation/start"),
  dictationStop: () => call<Capture>("POST", "/dictation/stop"),
  diag: (pin: string) => call<Record<string, unknown>>("GET", "/admin/diag", undefined, { "X-Admin-Pin": pin }),
  printTest: (pin: string) => call<{ printed: boolean }>("POST", "/admin/print-test", undefined, { "X-Admin-Pin": pin }),
};

// WebSocket avec reconnexion automatique.
export function connectEvents(onEvent: (event: KioskEvent) => void): () => void {
  let socket: WebSocket | null = null;
  let closed = false;
  let retry = 500;
  const open = () => {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${location.host}/ws`);
    socket.onopen = () => { retry = 500; };
    socket.onmessage = (message) => onEvent(JSON.parse(message.data));
    socket.onclose = () => {
      if (!closed) setTimeout(open, (retry = Math.min(retry * 2, 10000)));
    };
  };
  open();
  return () => { closed = true; socket?.close(); };
}
