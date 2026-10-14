<script setup lang="ts">
import { STUDENT_COLORS } from "../store";

defineProps<{ index: number; pseudo: string; large?: boolean }>();
const SHAPES = ["●", "■", "▲", "★"]; // forme + couleur : lisible aussi pour les élèves daltoniens
</script>

<template>
  <span class="badge" :class="{ large }" :style="{ '--c': STUDENT_COLORS[index] }">
    <span class="shape">{{ SHAPES[index] }}</span>
    <span class="pseudo">{{ pseudo }}</span>
  </span>
</template>

<style scoped>
.badge { display: inline-flex; align-items: center; gap: 0.4em; font-weight: 700; color: var(--c); }
.large { flex-direction: column; color: white; font-size: 2rem; }
.large .shape { font-size: 3.5rem; line-height: 1; }
</style>
