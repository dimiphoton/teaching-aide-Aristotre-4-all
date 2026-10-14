<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { api } from "../api";
import { store } from "../store";
import AttemptMeter from "../components/AttemptMeter.vue";
import ChatBubble from "../components/ChatBubble.vue";
import OnScreenKeyboard from "../components/OnScreenKeyboard.vue";
import StudentBadge from "../components/StudentBadge.vue";
import ScanPanel from "./ScanPanel.vue";
import DictationPanel from "./DictationPanel.vue";

const draft = ref("");
const panel = ref<"none" | "scan" | "dictation">("none");
const printing = ref(false);
const chat = ref<HTMLElement | null>(null);

const caps = computed(() => store.state!.capabilities);
const itemOpen = computed(() => store.item?.status === "en_cours");

watch(() => store.messages.length, async () => {
  await nextTick();
  chat.value?.scrollTo({ top: chat.value.scrollHeight, behavior: "smooth" });
});
// Bouton physique SCAN
watch(() => store.scanRequested, () => { if (itemOpen.value && caps.value.camera) panel.value = "scan"; });

async function send() {
  const text = draft.value.trim();
  if (!text || store.busy) return;
  draft.value = "";
  await store.sendAnswer(text);
}
async function validated(text: string, mode: string, captureId: string) {
  panel.value = "none";
  await store.sendAnswer(text, mode, captureId);
}
async function printQuestion() {
  printing.value = true;
  try {
    await api.printQuestion();
    store.messages.push({ from: "systeme", text: "🖨️ La question s'imprime : réponds sur le ticket puis scanne-le." });
  } catch (e) {
    store.messages.push({ from: "systeme", text: (e as Error).message });
  } finally {
    printing.value = false;
  }
}
</script>

<template>
  <main class="tutor">
    <header>
      <StudentBadge :index="store.state!.active!.index" :pseudo="store.state!.active!.pseudo" />
      <span class="notion">{{ store.item?.notion_title ?? store.state?.course.title }}</span>
      <AttemptMeter v-if="store.item" :errors="store.item.errors" :max="store.item.max_errors" :status="store.item.status" />
      <button class="ghost" @click="api.endSession()">J'ai fini</button>
    </header>

    <section ref="chat" class="chat">
      <ChatBubble v-for="(m, i) in store.messages" :key="i" :message="m" />
      <div v-if="store.busy" class="thinking">Aristote réfléchit…</div>
    </section>

    <section class="input">
      <template v-if="itemOpen">
        <div class="answer-row">
          <textarea v-model="draft" rows="2" placeholder="Écris ta réponse…" readonly />
          <div class="tools">
            <button v-if="caps.camera" class="secondary" :disabled="store.busy" @click="panel = 'scan'">📷 Scanner</button>
            <button v-if="caps.microphone" class="secondary" :disabled="store.busy" @click="panel = 'dictation'">🎤 Dicter</button>
            <button v-if="caps.printer" class="secondary" :disabled="printing" @click="printQuestion">🖨️ Imprimer</button>
          </div>
        </div>
        <OnScreenKeyboard v-model="draft" @submit="send" />
      </template>
      <div v-else class="next">
        <button v-if="!store.done" :disabled="store.busy" @click="store.nextQuestion()">Question suivante ➜</button>
        <button class="secondary" @click="api.endSession()">J'ai fini pour aujourd'hui</button>
      </div>
    </section>

    <ScanPanel v-if="panel === 'scan'" @cancel="panel = 'none'" @validated="(t, id) => validated(t, 'scan', id)" />
    <DictationPanel v-if="panel === 'dictation'" @cancel="panel = 'none'"
                    @validated="(t, id) => validated(t, 'dictee', id)" />
  </main>
</template>

<style scoped>
.tutor { height: 100%; display: flex; flex-direction: column; padding: 12px 18px; gap: 10px; }
header { display: flex; align-items: center; gap: 20px; font-size: 1.1rem; }
.notion { flex: 1; color: var(--muted); }
.chat { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 6px; }
.thinking { color: var(--muted); font-style: italic; }
.input { display: flex; flex-direction: column; gap: 8px; }
.answer-row { display: flex; gap: 10px; align-items: stretch; }
.tools { display: flex; gap: 8px; }
.tools button { min-width: 140px; }
.next { display: flex; gap: 16px; justify-content: center; padding: 20px; }
</style>
