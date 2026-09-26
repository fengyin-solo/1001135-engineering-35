<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <p v-if="errorMessage" class="error-text">
      {{ errorMessage }}
      <button class="btn" type="button" @click="loadOverview">重试</button>
    </p>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchOverview, type Overview } from '@/api/overview'

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])
const errorMessage = ref('')

async function loadOverview() {
  errorMessage.value = ''
  try {
    const payload = await fetchOverview()
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch (error) {
    // 不编造数字：读不到就明说，让人去确认后端是否在运行
    cards.value = []
    moduleRows.value = []
    errorMessage.value = error instanceof Error ? error.message : '运营概览读取失败，请确认后端已启动'
  }
}

onMounted(loadOverview)
</script>
