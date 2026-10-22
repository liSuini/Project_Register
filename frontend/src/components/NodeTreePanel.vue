<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { nodesApi } from '../api'

const props = defineProps({ tree: { type: Array, required: true } })
const emit = defineEmits(['changed'])

function onAdd(data) {
  ElMessageBox.prompt('子环节名称（可继续嵌套）', `在【${data.name}】下新增`)
    .then(({ value }) => {
      if (!value || !value.trim()) return
      nodesApi.add(data.id, value.trim()).then(() => emit('changed'))
    }).catch(() => {})
}

function onRename(data) {
  ElMessageBox.prompt('新名称', '重命名', { inputValue: data.name })
    .then(({ value }) => {
      if (!value || !value.trim()) return
      nodesApi.rename(data.id, value.trim()).then(() => emit('changed'))
    }).catch(() => {})
}

function onDelete(data) {
  ElMessageBox.confirm(
    `确认删除环节【${data.name}】？（有子环节或附件时会被系统拒绝）`, '删除')
    .then(() => nodesApi.remove(data.id).then(() => emit('changed')))
    .catch(() => {})
}

// ---------- 附件抽屉 ----------
const drawer = ref(false)
const currentNode = ref(null)
const attachments = ref([])
const uploadInput = ref(null)

function openAttachments(data) {
  currentNode.value = data
  drawer.value = true
  loadAttachments()
}

async function loadAttachments() {
  const { data } = await nodesApi.attachments(currentNode.value.id)
  attachments.value = data
}

function triggerUpload() {
  uploadInput.value?.click()
}

async function doUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  await nodesApi.upload(currentNode.value.id, file)
  e.target.value = ''
  ElMessage.success('已上传')
  loadAttachments()
  emit('changed')
}

function onDeleteAttachment(att) {
  ElMessageBox.confirm(`删除附件【${att.original_name}】？`, '删除附件')
    .then(async () => {
      await nodesApi.deleteAttachment(att.id)
      loadAttachments()
      emit('changed')
    }).catch(() => {})
}

function fmtSize(n) {
  if (n < 1024) return n + ' B'
  if (n < 1048576) return Math.round(n / 1024) + ' KB'
  return (n / 1048576).toFixed(1) + ' MB'
}
</script>

<template>
  <div>
    <el-tree :data="tree" node-key="id" default-expand-all
             :props="{ label: 'name', children: 'children' }">
      <template #default="{ data }">
        <div style="display: flex; align-items: center; gap: 6px; flex: 1; padding: 2px 0">
          <span :style="data.is_anchor ? 'font-weight: bold' : ''">
            {{ data.is_anchor ? '📌 ' : '' }}{{ data.name }}
          </span>
          <el-tag v-if="data.attachment_count" size="small" type="success"
                  effect="light" style="cursor: pointer"
                  @click.stop="openAttachments(data)">
            📎{{ data.attachment_count }}
          </el-tag>
          <el-button size="small" text type="primary"
                     @click.stop="openAttachments(data)">附件</el-button>
          <el-button size="small" text type="primary"
                     @click.stop="onAdd(data)">+子环节</el-button>
          <template v-if="!data.is_anchor">
            <el-button size="small" text @click.stop="onRename(data)">改名</el-button>
            <el-button size="small" text type="danger"
                       @click.stop="onDelete(data)">删</el-button>
          </template>
        </div>
      </template>
    </el-tree>

    <el-drawer v-model="drawer"
               :title="currentNode ? `【${currentNode.name}】附件` : '附件'"
               size="40%">
      <input ref="uploadInput" type="file" style="display: none" @change="doUpload" />
      <el-button type="primary" style="margin-bottom: 10px" @click="triggerUpload">
        上传附件
      </el-button>
      <el-table :data="attachments" border size="small">
        <el-table-column prop="original_name" label="文件名" min-width="220" />
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ fmtSize(row.size) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-link type="primary" :href="`/api/attachments/${row.id}/download`"
                     target="_blank">下载</el-link>
            <el-button size="small" text type="danger" style="margin-left: 8px"
                       @click="onDeleteAttachment(row)">删</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>
