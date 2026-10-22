<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { projectsApi, toYuan, wan } from '../api'

const STAGES = ['商机', '中标', '签约', '立项', '采购', '实施', '交付', '验收', '结算']
const router = useRouter()
const rows = ref([])
const loading = ref(false)
const query = reactive({ keyword: '', stage: '' })
const dialog = ref(false)
const form = reactive({ name: '', customer: '', contract_no: '', owner: '',
                        amount_wan: 0, initial_stage: '商机' })

async function load() {
  loading.value = true
  try {
    const { data } = await projectsApi.list({
      keyword: query.keyword || undefined,
      stage: query.stage || undefined
    })
    rows.value = data
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.name.trim()) return
  await projectsApi.create({
    name: form.name.trim(), customer: form.customer, contract_no: form.contract_no,
    owner: form.owner, contract_amount: toYuan(form.amount_wan),
    initial_stage: form.initial_stage
  })
  dialog.value = false
  Object.assign(form, { name: '', customer: '', contract_no: '', owner: '',
                        amount_wan: 0, initial_stage: '商机' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 12px">
      <el-input v-model="query.keyword" placeholder="按项目名称检索…" clearable
                style="width: 260px" @input="load" />
      <el-select v-model="query.stage" placeholder="按当前阶段筛选" clearable
                 style="width: 180px" @change="load">
        <el-option v-for="s in STAGES" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button type="primary" @click="dialog = true">＋ 新建项目</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border stripe
              highlight-current-row
              @row-click="(r) => router.push(`/projects/${r.id}`)">
      <el-table-column prop="name" label="项目名称" min-width="220" />
      <el-table-column prop="customer" label="客户" min-width="140" />
      <el-table-column prop="contract_no" label="合同编号" min-width="120" />
      <el-table-column label="当前阶段" width="90">
        <template #default="{ row }">
          <el-tag type="primary" effect="light">{{ row.current_stage }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="签约额(万元)" width="120" align="right">
        <template #default="{ row }">{{ wan(row.contract_amount) }}</template>
      </el-table-column>
      <el-table-column prop="owner" label="负责人" width="90" />
    </el-table>
    <el-empty v-if="!loading && !rows.length"
              description="暂无项目，点右上角新建（可选任意起始阶段承接存量）" />

    <el-dialog v-model="dialog" title="新建项目（起始阶段任选，承接存量）" width="520">
      <el-form label-width="90px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="必填" />
        </el-form-item>
        <el-form-item label="客户"><el-input v-model="form.customer" /></el-form-item>
        <el-form-item label="合同编号"><el-input v-model="form.contract_no" /></el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
        <el-form-item label="签约额(万元)">
          <el-input-number v-model="form.amount_wan" :min="0" :controls="false"
                           style="width: 200px" />
        </el-form-item>
        <el-form-item label="起始阶段">
          <el-select v-model="form.initial_stage" style="width: 200px">
            <el-option v-for="s in STAGES" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="create">创建台账</el-button>
      </template>
    </el-dialog>
  </div>
</template>
