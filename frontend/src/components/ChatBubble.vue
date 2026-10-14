<script setup lang="ts">
import type { ChatMessage } from "../store";

defineProps<{ message: ChatMessage }>();
const MODE_ICON: Record<string, string> = { scan: "📷", dictee: "🎤", saisie: "" };
</script>

<template>
  <div class="bubble" :class="message.from">
    <span v-if="message.mode && MODE_ICON[message.mode]" class="mode">{{ MODE_ICON[message.mode] }}</span>
    <span class="text">{{ message.text }}</span>
  </div>
</template>

<style scoped>
.bubble { max-width: 78%; padding: 14px 18px; border-radius: 20px; white-space: pre-wrap; line-height: 1.4; }
.tuteur { background: white; align-self: flex-start; border-bottom-left-radius: 6px; font-size: 1.15rem; }
.eleve { background: var(--accent); color: white; align-self: flex-end; border-bottom-right-radius: 6px; }
.systeme { background: #fff4cf; align-self: center; font-size: 0.9rem; }
.mode { margin-right: 8px; }
</style>
