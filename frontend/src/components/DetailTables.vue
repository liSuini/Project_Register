<script setup>
import { reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { detailsApi, toYuan, wan } from '../api'

const props = defineProps({
  projectId: Number,
  purchases: Array,
  acceptances: Array,
  totals: Object
})
const emit = defineEmits(['changed'])

// ---------- 采购 ----------
const purDialog = ref(false)
const purForm = reactive({ name: '', supplier: '', amount_wan: 0 })

async function addPurchase() {
  if (!purForm.name.trim()) return
  await detailsApi.addPurchase(props.projectId, {
    name: purForm.name.trim(), supplier: purForm.supplier,
    amount: toYuan(purForm.amount_wan)
  })
  purDialog.value = false
  Object.assign(purForm, { name: '', supplier: '', amount_wan: 0 })
  emit('changed')
}

function delPurchase(row) {
  ElMessageBox.confirm(`删除采购单【${row.name}】？`, '删除')
    .then(() => detailsApi.delPurchase(row.id).then(() => emit('changed')))
    .catch(() => {})
}

// ---------- 验收 ----------
const accDialog = ref(false)
const accForm = reactive({ name: '', received_wan: 0 })

async function addAcceptance() {
  if (!accForm.name.trim()) return
  await detailsApi.addAcceptance(props.projectId, {
    name: accForm.name.trim(), received_amount: toYuan(accForm.received_wan)
  })
  accDialog.value = false
  Object.assign(accForm, { name: '', received_wan: 0 })
  emit('changed')
}

function delAcceptance(row) {
  ElMessageBox.confirm(`删除验收记录【${row.name}】？`, '删除')
    .then(() => detailsApi.delAcceptance(row.id).then(() => emit('changed')))
    .catch(() => {})
}
</script>

<template>
  <div>
    <div style="display: flex; align-items: center; margin-bottom: 6px">
      <b>采购明细（后向口径）</b>
      <el-button size="small" type="primary" text @click="purDialog = true">
        ＋加采购
      </el-button>
      <span style="margin-left: auto; font-size: 13px">
        采购额合计：<b style="color: #1f4e9c">{{ wan(totals?.purchase_amount) }}</b> 万元
      </span>
    </div>
    <el-table :data="purchases" border size="small">
      <el-table-column prop="name" label="采购名称" min-width="140" />
      <el-table-column prop="supplier" label="供应商" min-width="110" />
      <el-table-column label="金额(万元)" width="110" align="right">
        <template #default="{ row }">{{ wan(row.amount) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="70">
        <template #default="{ row }">
          <el-button size="small" text type="danger"
                     @click="delPurchase(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="display: flex; align-items: center; margin: 14px 0 6px">
      <b>验收记录（交付口径）</b>
      <el-button size="small" type="primary" text @click="accDialog = true">
        ＋加验收
      </el-button>
      <span style="margin-left: auto; font-size: 13px">
        回款额合计：<b style="color: #1f4e9c">{{ wan(totals?.received_amount) }}</b> 万元
      </span>
    </div>
    <el-table :data="acceptances" border size="small">
      <el-table-column prop="name" label="验收名称" min-width="140" />
      <el-table-column label="回款金额(万元)" width="120" align="right">
        <template #default="{ row }">{{ wan(row.received_amount) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="70">
        <template #default="{ row }">
          <el-button size="small" text type="danger"
                     @click="delAcceptance(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="purDialog" title="新增采购单" width="420">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="purForm.name" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="purForm.supplier" />
        </el-form-item>
        <el-form-item label="金额(万元)">
          <el-input-number v-model="purForm.amount_wan" :min="0" :controls="false"
                           style="width: 180px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="purDialog = false">取消</el-button>
        <el-button type="primary" @click="addPurchase">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="accDialog" title="新增验收记录" width="420">
      <el-form label-width="90px">
        <el-form-item label="验收名称" required>
          <el-input v-model="accForm.name" />
        </el-form-item>
        <el-form-item label="回款(万元)">
          <el-input-number v-model="accForm.received_wan" :min="0" :controls="false"
                           style="width: 180px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="accDialog = false">取消</el-button>
        <el-button type="primary" @click="addAcceptance">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
