<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { api, connectEvents } from "./api";
import { store } from "./store";
import HomeView from "./views/HomeView.vue";
import TutorView from "./views/TutorView.vue";
import AdminView from "./views/AdminView.vue";

const showAdmin = ref(false);
let disconnect: (() => void) | null = null;

// Boutons physiques câblés sur un clavier USB (mini-PC) : F13 à F17, appui long ≥ 3 s.
const keyDownAt = new Map<string, number>();
const FORWARDED = new Set(["F13", "F14", "F15", "F16", "F17"]);
function onKeyDown(e: KeyboardEvent) {
  if (!FORWARDED.has(e.key)) return;
  e.preventDefault();
  if (!e.repeat) keyDownAt.set(e.key, performance.now());
}
async function onKeyUp(e: KeyboardEvent) {
  if (!FORWARDED.has(e.key) || !store.state?.capabilities.keyboard_buttons) return;
  const started = keyDownAt.get(e.key) ?? performance.now();
  keyDownAt.delete(e.key);
  await api.key(e.key, performance.now() - started >= 3000).catch(() => undefined);
}

onMounted(async () => {
  await store.refresh();
  disconnect = connectEvents(async (event) => {
    if (event.type === "student.changed") {
      store.resetConversation();
      await store.refresh();
      if (store.state?.active) await store.nextQuestion();
    } else if (event.type === "button.scan") {
      store.scanRequested++;
    }
  });
  window.addEventListener("keydown", onKeyDown);
  window.addEventListener("keyup", onKeyUp);
  window.addEventListener("contextmenu", (e) => e.preventDefault()); // pas de menu sur appui long tactile
});
onUnmounted(() => {
  disconnect?.();
  window.removeEventListener("keydown", onKeyDown);
  window.removeEventListener("keyup", onKeyUp);
});
</script>

<template>
  <AdminView v-if="showAdmin" @close="showAdmin = false" />
  <template v-else>
    <TutorView v-if="store.state?.active" />
    <HomeView v-else @admin="showAdmin = true" />
  </template>
  <div v-if="store.error && !store.state" class="offline">{{ store.error }}</div>
</template>

<style scoped>
.offline { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); background: var(--bad);
  color: white; padding: 8px 20px; border-radius: 999px; }
</style>
