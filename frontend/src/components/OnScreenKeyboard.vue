<script setup lang="ts">
// Clavier à l'écran (le compositeur kiosque n'affiche pas de clavier virtuel système).
// Disposition AZERTY + couche « 123 » avec chiffres et symboles mathématiques.
import { computed, ref } from "vue";

const model = defineModel<string>({ required: true });
const emit = defineEmits<{ submit: [] }>();

const layer = ref<"abc" | "123">("abc");
const shift = ref(false);

const LETTERS = [
  ["a", "z", "e", "r", "t", "y", "u", "i", "o", "p"],
  ["q", "s", "d", "f", "g", "h", "j", "k", "l", "m"],
  ["w", "x", "c", "v", "b", "n", "'", ",", "."],
];
const ACCENTS = ["é", "è", "ê", "à", "â", "ù", "û", "ç", "ô", "î", "ë", "ï", "œ"];
const SYMBOLS = [
  ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
  ["+", "-", "×", "÷", "/", "=", "(", ")", ",", "."],
  ["²", "³", "^", "√", "π", "%", "<", ">", "≤", "≥"],
  ["?", "!", ":", ";", "°", "€", "\"", "'", "–"],
];

const rows = computed(() => (layer.value === "abc" ? LETTERS : SYMBOLS));
const label = (k: string) => (shift.value && layer.value === "abc" ? k.toUpperCase() : k);

function press(k: string) {
  model.value += label(k);
  if (shift.value) shift.value = false;
}
function backspace() { model.value = Array.from(model.value).slice(0, -1).join(""); }
</script>

<template>
  <div class="kbd">
    <div v-if="layer === 'abc'" class="row accents">
      <button v-for="k in ACCENTS" :key="k" class="key small" @click="press(k)">{{ label(k) }}</button>
    </div>
    <div v-for="(row, i) in rows" :key="i" class="row">
      <button v-for="k in row" :key="k" class="key" @click="press(k)">{{ label(k) }}</button>
    </div>
    <div class="row">
      <button class="key wide secondary" @click="layer = layer === 'abc' ? '123' : 'abc'">
        {{ layer === "abc" ? "123 ±" : "ABC" }}
      </button>
      <button v-if="layer === 'abc'" class="key wide secondary" :class="{ on: shift }" @click="shift = !shift">⇧</button>
      <button class="key space" @click="model += ' '">espace</button>
      <button class="key wide secondary" @click="backspace">⌫</button>
      <button class="key wide send" @click="emit('submit')">Envoyer ➜</button>
    </div>
  </div>
</template>

<style scoped>
.kbd { display: flex; flex-direction: column; gap: 6px; padding: 8px; background: #e9e5db; border-radius: var(--radius); }
.row { display: flex; gap: 6px; justify-content: center; }
.key { min-height: 52px; min-width: 64px; padding: 0 10px; border-radius: 12px; background: white; color: var(--ink);
  font-size: 1.15rem; }
.key.small { min-height: 42px; min-width: 52px; font-size: 1rem; }
.key.wide { min-width: 110px; }
.key.space { flex: 1; max-width: 420px; }
.key.secondary { background: #d6d1c4; }
.key.on { background: var(--accent); color: white; }
.key.send { background: var(--ok); color: white; min-width: 170px; }
</style>
