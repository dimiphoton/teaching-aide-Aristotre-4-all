import { reactive } from "vue";
import { api, type ItemInfo, type KioskState } from "./api";

export interface ChatMessage { from: "tuteur" | "eleve" | "systeme"; text: string; mode?: string }

export const STUDENT_COLORS = ["#d93a3a", "#2f6fdb", "#2e9d55", "#e2b420"];

export const store = reactive({
  state: null as KioskState | null,
  item: null as ItemInfo | null,
  messages: [] as ChatMessage[],
  busy: false,
  error: "",
  done: false,
  scanRequested: 0, // incrémenté par le bouton physique SCAN

  async refresh() {
    try {
      this.state = await api.state();
      this.item = this.state.item;
      this.error = "";
    } catch (e) {
      this.error = "Le kiosque redémarre…";
    }
  },

  resetConversation() {
    this.messages = [];
    this.item = null;
    this.done = false;
  },

  async nextQuestion() {
    this.busy = true;
    try {
      const result = await api.next();
      this.done = result.done;
      this.item = result.item;
      if (result.done) {
        this.messages.push({ from: "tuteur", text: "Tu as fait toutes les questions disponibles. Bravo pour ton travail !" });
      } else if (result.item) {
        this.messages.push({ from: "tuteur", text: result.item.question });
      }
    } catch (e) {
      this.error = (e as Error).message;
    } finally {
      this.busy = false;
    }
  },

  async sendAnswer(text: string, mode = "saisie", captureId?: string) {
    if (!text.trim()) return;
    this.messages.push({ from: "eleve", text, mode });
    this.busy = true;
    try {
      const turn = await api.answer(text, mode, captureId);
      this.item = turn.item;
      this.messages.push({ from: "tuteur", text: turn.reply });
      if (turn.ticket_printed) {
        this.messages.push({ from: "systeme", text: "🖨️ Un ticket de révision s'imprime : agrafe-le dans ton cahier." });
      }
    } catch (e) {
      this.messages.push({ from: "systeme", text: (e as Error).message });
    } finally {
      this.busy = false;
    }
  },
});
