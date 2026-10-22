<script setup>
defineProps({
  stages: { type: Array, required: true },
  current: String,
  initial: String
})
const emit = defineEmits(['select'])
</script>

<template>
  <div style="display: flex; gap: 4px">
    <div v-for="(s, i) in stages" :key="s" class="step"
         :class="{ current: s === current,
                   excluded: i < stages.indexOf(initial),
                   reached: i >= stages.indexOf(initial) && s !== current }"
         @click="emit('select', s)">
      <span class="idx">{{ i + 1 }}</span>{{ s }}
      <span v-if="s === current" class="tag">当前</span>
      <span v-else-if="i < stages.indexOf(initial)" class="tag dim">存量未纳入</span>
    </div>
  </div>
</template>

<style scoped>
.step {
  flex: 1; text-align: center; padding: 8px 2px;
  border-bottom: 3px solid #dcdfe6; cursor: pointer;
  font-size: 13px; color: #606266; user-select: none;
}
.step .idx { display: block; font-size: 11px; color: #909399; }
.step:hover { background: #f5f7fa; }
.step.reached { border-bottom-color: #a0c6ff; }
.step.current {
  border-bottom-color: #1f4e9c; font-weight: bold;
  color: #1f4e9c; background: #ecf2fb;
}
.step.excluded { border-bottom-style: dashed; color: #c0c4cc; }
.tag { display: block; font-size: 10px; color: #e6a23c; }
.tag.dim { color: #c0c4cc; }
</style>
