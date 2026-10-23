<script setup lang="ts">
const props = defineProps<{ errors: number; max: number; status: string }>();
</script>

<template>
  <div class="meter" :title="`${props.errors} essai(s) sur ${props.max}`">
    <span v-for="n in props.max" :key="n" class="dot" :class="{ used: n <= props.errors }" />
    <span v-if="props.status === 'valide'" class="label ok">Réussi</span>
    <span v-else-if="props.status === 'verrouille'" class="label lock">À revoir</span>
  </div>
</template>

<style scoped>
.meter { display: flex; align-items: center; gap: 8px; }
.dot { width: 22px; height: 22px; border-radius: 50%; border: 3px solid #c9c3b5; background: white; }
.dot.used { background: var(--warn); border-color: var(--warn); }
.label { font-weight: 700; margin-left: 6px; }
.ok { color: var(--ok); }
.lock { color: var(--muted); }
</style>
