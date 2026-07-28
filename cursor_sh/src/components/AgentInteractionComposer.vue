<template>
  <section
    v-if="showInteractionPanel"
    class="agent-interaction-card"
    :class="`is-${interaction?.type || 'text'}`"
    aria-label="选择题回答区"
  >
    <div class="agent-interaction-body">
      <div v-if="isDate" class="agent-interaction-date">
        <el-date-picker
          v-model="dateAnswer"
          class="agent-interaction-date-picker"
          type="date"
          format="YYYY年M月D日"
          value-format="YYYY-MM-DD"
          :placeholder="interaction?.placeholder || '选择日期'"
          :disabled="disabled"
          :clearable="true"
          :teleported="true"
          aria-label="选择日期"
        />
        <button
          type="button"
          class="agent-interaction-date-uncertain"
          :class="{ 'is-selected': isDateUncertain }"
          :aria-pressed="isDateUncertain"
          :disabled="disabled"
          @click="selectDateUncertain"
        >
          不确定
        </button>
      </div>

      <label v-if="isSearchable && !isCustomMode" class="agent-interaction-search-wrap">
        <el-icon aria-hidden="true"><Search /></el-icon>
        <input
          v-model="searchQuery"
          class="agent-interaction-search"
          type="search"
          placeholder="搜索选项"
          aria-label="搜索选项"
          :disabled="disabled"
        />
      </label>

      <template v-if="isChoice && !isCustomMode">
        <div class="agent-interaction-options" :role="isMultiple ? 'group' : 'radiogroup'">
          <button
            v-for="(option, index) in filteredOptions"
            :key="option.id"
            type="button"
            class="agent-interaction-option"
            :class="{ 'is-selected': selectedValues.includes(option.value) }"
            :role="isMultiple ? 'checkbox' : 'radio'"
            :aria-checked="selectedValues.includes(option.value)"
            :disabled="disabled"
            @click="toggleOption(option.value)"
          >
            <span class="agent-interaction-index" aria-hidden="true">{{ getOptionIndex(option.id, index) }}</span>
            <span class="agent-interaction-label">{{ option.label }}</span>
          </button>

          <p v-if="filteredOptions.length === 0" class="agent-interaction-empty">没有匹配的选项</p>

          <button
            v-if="interaction?.allow_other !== false"
            type="button"
            class="agent-interaction-option is-other"
            :disabled="disabled"
            @click="openCustomAnswer"
          >
            <span class="agent-interaction-index" aria-hidden="true"><el-icon><EditPen /></el-icon></span>
            <span class="agent-interaction-label">其他，直接输入</span>
          </button>
        </div>
      </template>

      <div v-else-if="isChoice" class="agent-interaction-custom">
        <button
          type="button"
          class="agent-interaction-back"
          :disabled="disabled"
          aria-label="返回选项"
          @click="closeCustomAnswer"
        >
          <el-icon><Back /></el-icon>
          <span>返回选项</span>
        </button>
        <textarea
          ref="customInputRef"
          v-model="customAnswer"
          class="agent-interaction-custom-input"
          :placeholder="interaction?.placeholder || '输入你的回答'"
          :disabled="disabled"
          rows="3"
          @keydown.enter="handleCustomEnter"
        ></textarea>
      </div>
    </div>

    <footer class="agent-interaction-footer">
      <button
        type="button"
        class="agent-interaction-skip"
        :disabled="disabled"
        @click="emit('skip')"
      >
        跳过
      </button>
      <button
        type="button"
        class="agent-interaction-submit"
        :disabled="disabled || !canSubmit"
        @click="submitAnswer"
      >
        <span>继续</span>
        <el-icon aria-hidden="true"><ArrowRight /></el-icon>
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowRight, Back, EditPen, Search } from '@element-plus/icons-vue'

type InteractionOption = {
  id: string
  label: string
  value: string
  group?: string
}

type AgentInteraction = {
  type: string
  question_id?: string
  placeholder?: string
  options?: InteractionOption[]
  allow_other?: boolean
}

const props = defineProps<{
  interaction: AgentInteraction | null
  disabled?: boolean
}>()

const emit = defineEmits<{
  submit: [value: string]
  skip: []
}>()

const customInputRef = ref<HTMLTextAreaElement | null>(null)
const searchQuery = ref('')
const selectedValues = ref<string[]>([])
const isCustomMode = ref(false)
const customAnswer = ref('')
const dateAnswer = ref('')
const isDateUncertain = ref(false)

const options = computed(() => (props.interaction?.options || []).filter(option => option.label && option.value))
const isChoice = computed(() => props.interaction?.type === 'single_choice' || props.interaction?.type === 'multiple_choice')
const isMultiple = computed(() => props.interaction?.type === 'multiple_choice')
const isDate = computed(() => props.interaction?.type === 'date')
const isSearchable = computed(() => isChoice.value && options.value.length > 8)
const showInteractionPanel = computed(() => isDate.value || (isChoice.value && options.value.length > 0))
const filteredOptions = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return options.value
  return options.value.filter(option => `${option.label} ${option.value} ${option.group || ''}`.toLowerCase().includes(query))
})
const canSubmit = computed(() => (
  isDate.value
    ? Boolean(dateAnswer.value) || isDateUncertain.value
    : isCustomMode.value
    ? Boolean(customAnswer.value.trim())
    : selectedValues.value.length > 0
))

watch(
  () => [props.interaction?.question_id, props.interaction?.type],
  () => resetState(),
)

watch(dateAnswer, value => {
  if (value) isDateUncertain.value = false
})

const resetState = () => {
  searchQuery.value = ''
  selectedValues.value = []
  isCustomMode.value = false
  customAnswer.value = ''
  dateAnswer.value = ''
  isDateUncertain.value = false
}

const getOptionIndex = (optionId: string, fallbackIndex: number) => {
  const originalIndex = options.value.findIndex(option => option.id === optionId)
  return (originalIndex >= 0 ? originalIndex : fallbackIndex) + 1
}

const toggleOption = (value: string) => {
  if (props.disabled) return
  if (!isMultiple.value) {
    selectedValues.value = [value]
    return
  }

  selectedValues.value = selectedValues.value.includes(value)
    ? selectedValues.value.filter(item => item !== value)
    : [...selectedValues.value, value]
}

const openCustomAnswer = async () => {
  if (props.disabled) return
  isCustomMode.value = true
  selectedValues.value = []
  await nextTick()
  customInputRef.value?.focus()
}

const closeCustomAnswer = () => {
  if (props.disabled) return
  isCustomMode.value = false
}

const selectDateUncertain = () => {
  if (props.disabled) return
  dateAnswer.value = ''
  isDateUncertain.value = true
}

const submitAnswer = () => {
  if (props.disabled || !canSubmit.value) return
  const selectedLabels = selectedValues.value
    .map(value => options.value.find(option => option.value === value)?.label || value)
  const value = isDate.value
    ? isDateUncertain.value
      ? '不确定'
      : formatDateAnswer(dateAnswer.value)
    : isCustomMode.value
      ? customAnswer.value.trim()
      : selectedLabels.join('、')
  emit('submit', value)
}

const formatDateAnswer = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  if (!year || !month || !day) return value
  return `${year}年${month}月${day}日`
}

const handleCustomEnter = (event: KeyboardEvent) => {
  if (event.isComposing || event.shiftKey) return
  event.preventDefault()
  submitAnswer()
}
</script>

<style scoped lang="scss">
.agent-interaction-card {
  container-type: inline-size;
  width: 100%;
  max-height: min(480px, 58vh);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 14px 38px rgba(40, 32, 28, 0.1);
  color: #1f2020;
}

.agent-interaction-body {
  min-height: 0;
  overflow-y: auto;
  padding: 14px 14px 4px;
  scrollbar-width: thin;
}

.agent-interaction-date {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  padding: 2px;
}

.agent-interaction-date-picker.el-date-editor {
  width: 100%;
  height: 42px;
}

.agent-interaction-date-picker :deep(.el-input__wrapper) {
  border-radius: 11px;
  background: #f8f8f8;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.09) inset;
}

.agent-interaction-date-picker :deep(.el-input__inner) {
  color: #292a2c;
  font: inherit;
  font-size: 13px;
  line-height: 1.68;
}

.agent-interaction-date-picker :deep(.el-input__wrapper.is-focus) {
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(160, 82, 45, 0.32) inset, 0 0 0 3px rgba(160, 82, 45, 0.07);
}

.agent-interaction-date-uncertain {
  min-width: 88px;
  height: 42px;
  padding: 0 14px;
  border: 1px solid rgba(0, 0, 0, 0.09);
  border-radius: 11px;
  background: #f8f8f8;
  color: #55575a;
  font: inherit;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease, transform 0.16s ease;
}

.agent-interaction-date-uncertain:hover:not(:disabled) {
  background: #f7f4f2;
  color: #2f2824;
}

.agent-interaction-date-uncertain:active:not(:disabled) {
  transform: scale(0.98);
}

.agent-interaction-date-uncertain.is-selected {
  border-color: rgba(160, 82, 45, 0.34);
  background: rgba(160, 82, 45, 0.08);
  color: #663b28;
}

.agent-interaction-search-wrap {
  height: 38px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 2px 10px;
  padding: 0 11px;
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.09);
  border-radius: 10px;
  background: #f8f8f8;
  color: #999b9d;
}

.agent-interaction-search {
  min-width: 0;
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: #292a2c;
  font: inherit;
  font-size: 13px;
}

.agent-interaction-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.agent-interaction-option {
  width: 100%;
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 10px;
  box-sizing: border-box;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: #424446;
  font: inherit;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.68;
  letter-spacing: -0.01em;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease, transform 0.16s ease;
}

.agent-interaction-option:hover:not(:disabled) {
  background: #f7f4f2;
  color: #2f2824;
}

.agent-interaction-option:active:not(:disabled) {
  transform: scale(0.995);
}

.agent-interaction-option.is-selected {
  border-color: rgba(160, 82, 45, 0.34);
  background: rgba(160, 82, 45, 0.08);
  color: #663b28;
}

.agent-interaction-option.is-other {
  color: #77797c;
}

.agent-interaction-option:focus-visible,
.agent-interaction-date-uncertain:focus-visible,
.agent-interaction-back:focus-visible,
.agent-interaction-skip:focus-visible,
.agent-interaction-submit:focus-visible {
  outline: 3px solid rgba(160, 82, 45, 0.17);
  outline-offset: 2px;
}

.agent-interaction-option:disabled,
.agent-interaction-date-uncertain:disabled,
.agent-interaction-back:disabled,
.agent-interaction-skip:disabled,
.agent-interaction-submit:disabled {
  cursor: default;
  opacity: 0.5;
}

.agent-interaction-index {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #efefef;
  color: #55575a;
  font-size: 11px;
  font-weight: 600;
  transition: background 0.16s ease, color 0.16s ease;
}

.agent-interaction-index .el-icon {
  font-size: 13px;
}

.agent-interaction-option.is-selected .agent-interaction-index {
  background: var(--uv-ws-ai-chat-accent, #A0522D);
  color: #ffffff;
}

.agent-interaction-label {
  min-width: 0;
  overflow-wrap: anywhere;
}

.agent-interaction-empty {
  margin: 10px 0;
  color: #96989a;
  font-size: 13px;
  text-align: center;
}

@container (min-width: 640px) {
  .agent-interaction-options {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: stretch;
  }

  .agent-interaction-option {
    height: 100%;
  }

  .agent-interaction-option:last-child:nth-child(odd),
  .agent-interaction-empty {
    grid-column: 1 / -1;
  }
}

@container (max-width: 360px) {
  .agent-interaction-date {
    grid-template-columns: 1fr;
  }

  .agent-interaction-date-uncertain {
    width: 100%;
  }
}

.agent-interaction-custom {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-interaction-back {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 2px;
  border: 0;
  background: transparent;
  color: #77797c;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.agent-interaction-custom-input {
  width: 100%;
  min-height: 96px;
  max-height: 180px;
  resize: vertical;
  padding: 12px 13px;
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  outline: 0;
  background: #f8f8f8;
  color: #292a2c;
  font: inherit;
  font-size: 13px;
  line-height: 1.5;
  letter-spacing: -0.01em;
}

.agent-interaction-custom-input:focus {
  border-color: rgba(160, 82, 45, 0.32);
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(160, 82, 45, 0.07);
}

.agent-interaction-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 16px 16px;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.88), #ffffff 30%);
}

.agent-interaction-skip,
.agent-interaction-submit {
  height: 38px;
  border: 0;
  border-radius: 11px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.agent-interaction-skip {
  padding: 0 12px;
  background: transparent;
  color: #686a6d;
}

.agent-interaction-skip:hover:not(:disabled) {
  background: #f5f5f5;
}

.agent-interaction-submit {
  min-width: 88px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 15px;
  background: var(--uv-ws-ai-chat-accent, #A0522D);
  color: #ffffff;
  box-shadow: 0 5px 14px rgba(160, 82, 45, 0.22);
}

.agent-interaction-submit:hover:not(:disabled) {
  filter: brightness(0.96);
}

.agent-interaction-submit:disabled {
  box-shadow: none;
}

@media (max-width: 640px) {
  .agent-interaction-card {
    max-height: min(520px, 64vh);
    border-radius: 18px;
  }

  .agent-interaction-body {
    padding: 10px 9px 4px;
  }

  .agent-interaction-option {
    min-height: 44px;
    padding-inline: 10px;
  }

  .agent-interaction-date-picker.el-date-editor {
    height: 44px;
  }

  .agent-interaction-date-uncertain {
    height: 44px;
  }

  .agent-interaction-footer {
    padding: 12px 12px calc(12px + env(safe-area-inset-bottom));
  }

  .agent-interaction-skip,
  .agent-interaction-submit {
    height: 40px;
  }
}
</style>
