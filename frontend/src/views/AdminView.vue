<script setup lang="ts">
import { ref } from "vue";
import { api } from "../api";

const emit = defineEmits<{ close: [] }>();
const pin = ref("");
const diag = ref<Record<string, unknown> | null>(null);
const message = ref("");

async function unlock() {
  message.value = "";
  try { diag.value = await api.diag(pin.value); } catch (e) { message.value = (e as Error).message; pin.value = ""; }
}
async function printTest() {
  try { await api.printTest(pin.value); message.value = "Ticket de test envoyé."; }
  catch (e) { message.value = (e as Error).message; }
}
const digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"];
function key(d: string) {
  if (d === "⌫") pin.value = pin.value.slice(0, -1);
  else if (d === "OK") unlock();
  else if (pin.value.length < 8) pin.value += d;
}
</script>

<template>
  <main class="admin">
    <header><h1>Diagnostic</h1><button class="secondary" @click="emit('close')">Fermer</button></header>
    <div v-if="!diag" class="pin">
      <div class="dots">{{ "•".repeat(pin.length) || "Code PIN" }}</div>
      <div class="pad"><button v-for="d in digits" :key="d" class="secondary" @click="key(d)">{{ d }}</button></div>
    </div>
    <template v-else>
      <table>
        <tr v-for="(value, name) in diag" :key="name"><th>{{ name }}</th><td>{{ typeof value === "object" ? JSON.stringify(value) : value }}</td></tr>
      </table>
      <div class="actions"><button @click="printTest">🖨️ Ticket de test</button><button class="secondary" @click="unlock">↻ Actualiser</button></div>
    </template>
    <p class="msg">{{ message }}</p>
  </main>
</template>

<style scoped>
.admin { padding: 24px 40px; height: 100%; overflow: auto; }
header { display: flex; justify-content: space-between; align-items: center; }
.pin { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.dots { font-size: 2rem; letter-spacing: 0.3em; min-height: 2.5rem; color: var(--muted); }
.pad { display: grid; grid-template-columns: repeat(3, 110px); gap: 10px; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #ddd; }
th { width: 220px; color: var(--muted); }
.actions { display: flex; gap: 12px; margin-top: 16px; }
.msg { color: var(--muted); }
</style>
