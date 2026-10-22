<script setup>
import { onMounted, ref } from 'vue'
import { statsApi, wan } from '../api'

const stats = ref(null)

function load() {
  statsApi.get().then(({ data }) => (stats.value = data))
}

function exportFile() {
  window.open('/api/stats/export')
}

onMounted(load)

const cards = [
  { key: 'forward', title: '前向 · 签约口径', sub: '有签约额项目' },
  { key: 'backward', title: '后向 · 采购口径', sub: '有采购单项目' },
  { key: 'deliver', title: '交付 · 回款口径', sub: '有验收回款项目' }
]
</script>

<template>
  <div v-if="stats">
    <el-row :gutter="14" style="margin-bottom: 14px">
      <el-col v-for="c in cards" :key="c.key" :span="8">
        <el-card>
          <div style="font-size: 13px; color: #909399">{{ c.title }}</div>
          <div style="font-size: 28px; font-weight: bold; color: #1f4e9c; margin: 6px 0">
            {{ wan(stats[c.key].amount) }}
            <span style="font-size: 14px">万元</span>
          </div>
          <div style="font-size: 12px; color: #606266">
            {{ c.sub }} {{ stats[c.key].count }} 个
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-button type="primary" @click="exportFile">导出三口径明细 Excel</el-button>
    <div style="color: #909399; font-size: 12px; margin-top: 8px">
      口径说明：前向=项目签约额；后向=Σ采购单金额；交付=Σ验收回款金额（均由明细聚合，只算不存）
    </div>
  </div>
</template>
