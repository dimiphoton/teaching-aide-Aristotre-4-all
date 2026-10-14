<script setup lang="ts">
// Réponse orale : enregistrement → transcription locale → l'élève relit et corrige.
import { onUnmounted, ref } from "vue";
import { api, type Capture } from "../api";
import OnScreenKeyboard from "../components/OnScreenKeyboard.vue";

const emit = defineEmits<{ cancel: []; validated: [text: string, captureId: string] }>();
const recording = ref(false);
const working = ref(false);
const capture = ref<Capture | null>(null);
const text = ref("");
const error = ref("");
const seconds = ref(0);
let timer: number | undefined;

async function start() {
  error.value = "";
  try {
    await api.dictationStart();
    recording.value = true;
    seconds.value = 0;
    timer = window.setInterval(() => seconds.value++, 1000);
  } catch (e) { error.value = (e as Error).message; }
}
async function stop() {
  window.clearInterval(timer);
  recording.value = false;
  working.value = true;
  try {
    capture.value = await api.dictationStop();
    text.value = capture.value.text;
  } catch (e) { error.value = (e as Error).message; } finally { working.value = false; }
}
async function cancel() {
  if (recording.value) await api.dictationStop().catch(() => undefined);
  emit("cancel");
}
onUnmounted(() => window.clearInterval(timer));
</script>

<template>
  <div class="overlay">
    <div class="modal panel">
      <template v-if="!capture">
        <h2>Dis ta réponse à voix haute</h2>
        <div class="mic">
          <button class="big" :class="{ rec: recording }" :disabled="working" @click="recording ? stop() : start()">
            {{ working ? "Je transcris…" : recording ? `■ Stop (${seconds} s)` : "🎤 Parler" }}
          </button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions"><button class="secondary" @click="cancel">Annuler</button></div>
      </template>
      <template v-else>
        <h2>Vérifie ce que j'ai entendu, corrige si besoin</h2>
        <textarea v-model="text" rows="3" readonly />
        <OnScreenKeyboard v-model="text" @submit="emit('validated', text, capture.capture_id)" />
        <div class="actions">
          <button class="secondary" @click="capture = null">↺ Recommencer</button>
          <button :disabled="!text.trim()" @click="emit('validated', text, capture.capture_id)">C'est bien ma réponse ✓</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
h2 { margin: 0 0 12px; }
.mic { display: flex; justify-content: center; padding: 40px; }
.big { width: 320px; height: 320px; border-radius: 50%; font-size: 1.6rem; }
.big.rec { background: var(--bad); animation: pulse 1.2s infinite; }
@keyframes pulse { 50% { transform: scale(1.04); } }
.actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 12px; }
.error { color: var(--bad); text-align: center; }
</style>
