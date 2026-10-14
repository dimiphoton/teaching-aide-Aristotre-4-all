<script setup lang="ts">
import { api } from "../api";
import { store, STUDENT_COLORS } from "../store";
import StudentBadge from "../components/StudentBadge.vue";

const emit = defineEmits<{ admin: [] }>();

// Appui long de 3 s sur le titre : écran d'administration (protégé par code PIN).
let timer: number | undefined;
const holdStart = () => { timer = window.setTimeout(() => emit("admin"), 3000); };
const holdEnd = () => window.clearTimeout(timer);

async function select(index: number) {
  await api.select(index).catch(() => undefined); // le WebSocket rafraîchit ensuite l'écran
}
</script>

<template>
  <main class="home">
    <h1 @pointerdown="holdStart" @pointerup="holdEnd" @pointerleave="holdEnd">Aristote</h1>
    <p class="hint">Appuie sur <strong>ton bouton</strong> pour commencer.</p>
    <div class="students">
      <button v-for="s in store.state?.students ?? []" :key="s.index" class="student"
              :style="{ background: STUDENT_COLORS[s.index] }" @click="select(s.index)">
        <StudentBadge :index="s.index" :pseudo="s.pseudo" large />
      </button>
    </div>
    <footer>
      {{ store.state?.course.title }} · kiosque {{ store.state?.kiosk }}
      <span v-if="store.state?.mode === 'démonstration'"> · mode démonstration</span>
    </footer>
  </main>
</template>

<style scoped>
.home { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 28px; }
h1 { font-size: 3.2rem; margin: 0; letter-spacing: 0.04em; }
.hint { font-size: 1.4rem; margin: 0; color: var(--muted); }
.students { display: grid; grid-template-columns: repeat(4, 220px); gap: 24px; }
.student { height: 220px; display: flex; align-items: center; justify-content: center; }
footer { position: absolute; bottom: 18px; color: var(--muted); font-size: 0.85rem; }
</style>
