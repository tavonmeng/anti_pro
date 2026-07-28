<template>
  <section
    v-if="progress.visible"
    class="brief-progress-panel"
    :class="[`is-${progress.status}`, { 'is-expanded': isExpanded }]"
    aria-label="Brief进度"
  >
    <button
      type="button"
      class="brief-progress-toggle"
      :aria-expanded="isExpanded"
      aria-controls="brief-progress-details"
      @click="isExpanded = !isExpanded"
    >
      <span class="brief-progress-title">Brief进度</span>
      <span class="brief-progress-percent">{{ progress.percent }}%</span>
      <el-icon class="brief-progress-arrow" :class="{ 'is-expanded': isExpanded }" aria-hidden="true">
        <ArrowRight />
      </el-icon>
    </button>

    <transition name="brief-progress-disclosure">
      <div v-if="isExpanded" id="brief-progress-details" class="brief-progress-details">
        <div class="brief-progress-overview">
          <span>{{ progress.statusLabel }}</span>
          <span>{{ progress.filledCount }} / {{ progress.totalCount }} 项</span>
        </div>

        <div class="brief-progress-field-list">
          <article
            v-for="field in progress.fields"
            :key="field.key"
            class="brief-progress-field"
          >
            <div class="brief-progress-field-heading">
              <span class="brief-progress-field-label">{{ field.label }}</span>
              <span class="brief-progress-confidence" :class="`is-${field.confidence}`">
                {{ confidenceLabel(field.confidence) }}
              </span>
            </div>
            <p class="brief-progress-field-value">{{ field.value }}</p>
          </article>
        </div>

        <div v-if="progress.missingFields.length" class="brief-progress-missing">
          <strong>接下来继续补充</strong>
          <span>{{ progress.missingFields.join('、') }}</span>
        </div>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import { getBriefProgress, type AgentStateWithBrief } from '@/utils/briefProgress'

const props = defineProps<{
  agentState?: AgentStateWithBrief | null
}>()

const isExpanded = ref(false)
const progress = computed(() => getBriefProgress(props.agentState))

const confidenceLabel = (confidence: string) => {
  if (confidence === 'high') return '已确认'
  if (confidence === 'medium') return '已收集'
  return '待确认'
}
</script>

<style scoped lang="scss">
.brief-progress-panel {
  --progress-accent: #925237;
  --progress-accent-soft: rgba(146, 82, 55, 0.07);
  width: min(100%, 680px);
  margin-top: 7px;
  color: #77797c;
}

.brief-progress-panel.is-ready,
.brief-progress-panel.is-complete {
  --progress-accent: #4f8468;
  --progress-accent-soft: rgba(79, 132, 104, 0.08);
}

.brief-progress-toggle {
  width: auto;
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 1px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font: inherit;
  line-height: 1;
  cursor: pointer;
}

.brief-progress-toggle:hover {
  color: #4d5053;
}

.brief-progress-toggle:focus-visible {
  outline: 2px solid rgba(146, 82, 55, 0.22);
  outline-offset: 2px;
}

.brief-progress-title,
.brief-progress-percent {
  font-size: 11px;
  line-height: 1.5;
}

.brief-progress-title {
  font-weight: 550;
}

.brief-progress-percent {
  color: var(--progress-accent);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.brief-progress-arrow {
  width: 16px;
  height: 16px;
  font-size: 12px;
  color: #999c9f;
  transition: transform 0.18s ease, color 0.18s ease;
}

.brief-progress-toggle:hover .brief-progress-arrow {
  color: var(--progress-accent);
}

.brief-progress-arrow.is-expanded {
  transform: rotate(90deg);
}

.brief-progress-details {
  width: 100%;
  margin-top: 5px;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid rgba(58, 43, 35, 0.08);
  border-radius: 12px;
  background: #faf9f8;
}

.brief-progress-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #817975;
  font-size: 10px;
  line-height: 1.4;
}

.brief-progress-overview span:last-child {
  flex: 0 0 auto;
  color: var(--progress-accent);
  font-variant-numeric: tabular-nums;
}

.brief-progress-field-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.brief-progress-field {
  min-width: 0;
  padding: 8px 9px;
  border-radius: 9px;
  background: #ffffff;
}

.brief-progress-field-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.brief-progress-field-label {
  min-width: 0;
  overflow: hidden;
  color: #77706c;
  font-size: 10px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brief-progress-confidence {
  flex: 0 0 auto;
  color: #9b765f;
  font-size: 9px;
  line-height: 1.3;
}

.brief-progress-confidence.is-high {
  color: #4f8468;
}

.brief-progress-confidence.is-unknown {
  color: #aaa09a;
}

.brief-progress-field-value {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  color: #34302e;
  font-size: 11px;
  line-height: 1.5;
}

.brief-progress-missing {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 7px;
  padding: 8px 9px;
  border-radius: 9px;
  background: var(--progress-accent-soft);
  color: #776a63;
  font-size: 10px;
  line-height: 1.5;
}

.brief-progress-missing strong {
  flex: 0 0 auto;
  color: var(--progress-accent);
  font-weight: 600;
}

.brief-progress-disclosure-enter-active,
.brief-progress-disclosure-leave-active {
  overflow: hidden;
  max-height: 2400px;
  transition: opacity 0.18s ease, max-height 0.22s ease;
}

.brief-progress-disclosure-enter-from,
.brief-progress-disclosure-leave-to {
  max-height: 0;
  opacity: 0;
}

@media (max-width: 640px) {
  .brief-progress-panel {
    width: 100%;
    margin-top: 6px;
  }

  .brief-progress-field-list {
    grid-template-columns: 1fr;
  }

  .brief-progress-missing {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .brief-progress-arrow,
  .brief-progress-disclosure-enter-active,
  .brief-progress-disclosure-leave-active {
    transition: none;
  }
}
</style>
