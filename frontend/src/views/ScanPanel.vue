<script setup lang="ts">
// Scan d'une réponse manuscrite : aperçu caméra → photo → l'élève relit et corrige le texte reconnu.
import { onMounted, onUnmounted, ref } from "vue";
import { api, type Capture } from "../api";
import OnScreenKeyboard from "../components/OnScreenKeyboard.vue";

const emit = defineEmits<{ cancel: []; validated: [text: string, captureId: string] }>();
const preview = ref("");
const capture = ref<Capture | null>(null);
const text = ref("");
const working = ref(false);
const error = ref("");
let timer: number | undefined;

function refreshPreview() { preview.value = `/api/camera/preview.jpg?t=${Date.now()}`; }
onMounted(() => { refreshPreview(); timer = window.setInterval(refreshPreview, 400); });
onUnmounted(() => window.clearInterval(timer));

async function shoot() {
  working.value = true;
  error.value = "";
  window.clearInterval(timer);
  try {
    capture.value = await api.scan();
    text.value = capture.value.text;
  } catch (e) {
    error.value = (e as Error).message;
    timer = window.setInterval(refreshPreview, 400);
  } finally {
    working.value = false;
  }
}
function retry() {
  capture.value = null;
  timer = window.setInterval(refreshPreview, 400);
}
</script>

<template>
  <div class="overlay">
    <div class="modal panel">
      <template v-if="!capture">
        <h2>Pose ta feuille sous la caméra</h2>
        <img class="preview" :src="preview" alt="Aperçu de la caméra" />
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions">
          <button class="secondary" @click="emit('cancel')">Annuler</button>
          <button :disabled="working" @click="shoot">{{ working ? "Lecture…" : "📷 Prendre la photo" }}</button>
        </div>
      </template>
      <template v-else>
        <h2>Vérifie ce que j'ai lu, corrige si besoin</h2>
        <div class="result">
          <img :src="capture.image" alt="Copie scannée" />
          <textarea v-model="text" rows="5" readonly />
        </div>
        <p v-if="capture.page_found === false" class="warn">Feuille mal cadrée : tu peux reprendre la photo.</p>
        <OnScreenKeyboard v-model="text" @submit="emit('validated', text, capture.capture_id)" />
        <div class="actions">
          <button class="secondary" @click="retry">↺ Reprendre</button>
          <button :disabled="!text.trim()" @click="emit('validated', text, capture.capture_id)">C'est bien ma réponse ✓</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
h2 { margin: 0 0 12px; }
.preview { width: 100%; max-height: 52vh; object-fit: contain; background: #222; border-radius: 12px; }
.result { display: flex; gap: 16px; margin-bottom: 10px; }
.result img { width: 280px; max-height: 280px; object-fit: contain; border-radius: 8px; background: #eee; }
.actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 12px; }
.error { color: var(--bad); }
.warn { color: #9a6b00; }
</style>
