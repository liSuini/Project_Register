<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { projectsApi, wan } from '../api'
import StageStepper from '../components/StageStepper.vue'
import NodeTreePanel from '../components/NodeTreePanel.vue'
import DetailTables from '../components/DetailTables.vue'

const STAGES = ['商机', '中标', '签约', '立项', '采购', '实施', '交付', '验收', '结算']
const route = useRoute()
const ledger = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const { data } = await projectsApi.ledger(route.params.id)
    ledger.value = data
  } finally {
    loading.value = false
  }

}

function onSelectStage(stage) {
  const p = ledger.value.project
  if (stage === p.current_stage) return
  if (STAGES.indexOf(stage) < STAGES.indexOf(p.initial_stage)) {
    ElMessageBox.confirm(
      `【${stage}】在起始阶段【${p.initial_stage}】之前，通常为存量未纳入阶段，仍要流转吗？`)
      .then(() => doChange(stage)).catch(() => {})
  } else {
    doChange(stage)
  }
}

async function doChange(stage) {
  await projectsApi.changeStage(ledger.value.project.id, stage)
  load()
}

onMounted(load)
const p = computed(() => ledger.value?.project)
</script>

<template>
  <div v-loading="loading">
    <template v-if="p">
      <el-card style="margin-bottom: 12px">
        <div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap">
          <b style="font-size: 17px">{{ p.name }}</b>
          <span style="color: #909399">客户：{{ p.customer || '—' }}</span>
          <span style="color: #909399">合同编号：{{ p.contract_no || '—' }}</span>
          <span style="color: #909399">负责人：{{ p.owner || '—' }}</span>
          <span style="margin-left: auto">
            签约额：<b style="color: #1f4e9c; font-size: 16px">
              {{ wan(p.contract_amount) }}</b> 万元
          </span>
        </div>
      </el-card>

      <el-card style="margin-bottom: 12px">
        <StageStepper :stages="STAGES" :current="p.current_stage"
                      :initial="p.initial_stage" @select="onSelectStage" />
        <div style="font-size: 12px; color: #909399; margin-top: 6px">
          起始阶段：<b>{{ p.initial_stage }}</b>｜点击阶段可流转（推进/回退/跳转），
          回退不影响左侧资料树
        </div>
      </el-card>

      <el-row :gutter="12">
        <el-col :span="10">
          <el-card>
            <template #header><b>环节树（按环节归档资料）</b></template>
            <NodeTreePanel :tree="ledger.tree" @changed="load" />
          </el-card>
        </el-col>
        <el-col :span="14">
          <el-card>
            <DetailTables :project-id="p.id" :purchases="ledger.purchases"
                          :acceptances="ledger.acceptances" :totals="ledger.totals"
                          @changed="load" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>
