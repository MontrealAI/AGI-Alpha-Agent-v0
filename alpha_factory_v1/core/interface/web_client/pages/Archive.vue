<!-- SPDX-License-Identifier: Apache-2.0 -->
<template>
  <div>
    <h1>Agent Archive</h1>
    <div>
      <button
        v-for="tab in tabs"
        :key="tab"
        @click="current = tab"
        :class="{ active: current === tab }"
      >
        {{ tab }}
      </button>
    </div>
    <div v-if="current === 'Agents'">
      <ul>
        <li v-for="a in agents" :key="a.hash" class="agent-row">
          <a href="#" @click.prevent="select(a)">{{ a.hash }}</a>
          <span>score {{ a.score.toFixed(2) }}</span>
          <a :href="`${API_BASE}/archive/${a.hash}/diff`" download>Download diff</a>
        </li>
      </ul>
    </div>
    <div v-if="selected">
      <h2>Patch Diff</h2>
      <pre class="diff">{{ diff }}</pre>
      <h3>Tool Evolution</h3>
      <ul>
        <li v-for="p in timeline" :key="p.ts">{{ p.tool }} - {{ p.ts }}</li>
      </ul>
      <a v-if="parent" :href="`/archive/${parent}`" class="parent-link">Parent</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface Agent { hash: string; parent: string | null; score: number; }
interface TimelinePoint { tool: string; ts: number; }

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');

const agents = ref<Agent[]>([]);
const diff = ref('');
const timeline = ref<TimelinePoint[]>([]);
const parent = ref<string | null>(null);
const selected = ref<string | null>(null);
const tabs = ['Agents'];
const current = ref('Agents');

onMounted(fetchAgents);

async function fetchAgents() {
  try {
    const res = await fetch(`${API_BASE}/archive`);
    if (res.ok) agents.value = await res.json();
  } catch {
    // ignore
  }
}

async function select(a: Agent) {
  selected.value = a.hash;
  parent.value = a.parent;
  await fetchDiff(a.hash);
  await fetchTimeline(a.hash);
}

async function fetchDiff(hash: string) {
  try {
    const res = await fetch(`${API_BASE}/archive/${hash}/diff`);
    if (res.ok) diff.value = await res.text();
  } catch {
    diff.value = '';
  }
}

async function fetchTimeline(hash: string) {
  try {
    const res = await fetch(`${API_BASE}/archive/${hash}/timeline`);
    if (res.ok) timeline.value = await res.json();
  } catch {
    timeline.value = [];
  }
}
</script>

<style scoped>
.active {
  font-weight: bold;
}
</style>
