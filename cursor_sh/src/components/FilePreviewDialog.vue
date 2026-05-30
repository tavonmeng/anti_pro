<template>
  <el-dialog
    :model-value="modelValue"
    class="file-preview-dialog"
    width="min(960px, 92vw)"
    align-center
    append-to-body
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="preview-header">
        <div class="preview-title">
          <el-icon><component :is="previewIcon" /></el-icon>
          <span>{{ fileName }}</span>
        </div>
      </div>
    </template>

    <div class="preview-body">
      <template v-if="fileUrl">
        <img
          v-if="fileKind === 'image'"
          :src="fileUrl"
          :alt="fileName"
          class="preview-image"
        />
        <video
          v-else-if="fileKind === 'video'"
          :src="fileUrl"
          class="preview-video"
          controls
          preload="metadata"
          playsinline
        />
        <iframe
          v-else-if="fileKind === 'pdf'"
          :src="fileUrl"
          class="preview-frame"
          title="文件预览"
        />
        <div v-else class="preview-fallback">
          <el-icon :size="42"><Document /></el-icon>
          <p>该文件格式暂不支持网页内预览</p>
          <span>{{ fileName }}</span>
        </div>
      </template>
      <div v-else class="preview-fallback">
        <el-icon :size="42"><Document /></el-icon>
        <p>文件地址为空，无法预览</p>
      </div>
    </div>

    <template #footer>
      <div class="preview-footer">
        <a
          v-if="fileUrl"
          class="preview-download"
          :href="fileUrl"
          :download="fileName"
          target="_blank"
          rel="noopener noreferrer"
        >
          <el-icon><Download /></el-icon>
          下载文件
        </a>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Document, Download, Picture, VideoPlay } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: boolean
  file?: Record<string, any> | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const fileUrl = computed(() =>
  props.file?.url || props.file?.file_url || props.file?.fileUrl || props.file?.href || ''
)

const fileName = computed(() => {
  const name = props.file?.name || props.file?.filename || props.file?.fileName || props.file?.originalName || props.file?.original_filename || ''
  return name || decodeURIComponent(String(fileUrl.value).split('/').pop()?.split('?')[0] || '交付文件')
})

const fileMime = computed(() => String(
  props.file?.mime_type || props.file?.mimeType || props.file?.content_type || props.file?.type || ''
).toLowerCase())

const fileExtension = computed(() => {
  const raw = `${fileName.value} ${String(fileUrl.value).split('?')[0]}`
  const match = raw.toLowerCase().match(/\.([a-z0-9]+)(?:\s|$)/)
  return match?.[1] || ''
})

const fileKind = computed<'image' | 'video' | 'pdf' | 'other'>(() => {
  if (fileMime.value.startsWith('image/')) return 'image'
  if (fileMime.value.startsWith('video/')) return 'video'
  if (fileMime.value === 'application/pdf') return 'pdf'

  const ext = fileExtension.value
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'avif'].includes(ext)) return 'image'
  if (['mp4', 'webm', 'ogg', 'mov', 'm4v'].includes(ext)) return 'video'
  if (ext === 'pdf') return 'pdf'
  return 'other'
})

const previewIcon = computed(() => {
  if (fileKind.value === 'image') return Picture
  if (fileKind.value === 'video') return VideoPlay
  return Document
})
</script>

<style scoped>
.preview-header {
  min-width: 0;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1D1D1F;
}

.preview-title span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-body {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  max-height: 72vh;
  background: #F5F6F8;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  overflow: hidden;
}

.preview-image {
  max-width: 100%;
  max-height: 72vh;
  object-fit: contain;
  display: block;
}

.preview-video {
  width: 100%;
  max-height: 72vh;
  background: #000;
  display: block;
}

.preview-frame {
  width: 100%;
  height: 72vh;
  border: none;
  background: #fff;
}

.preview-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px;
  text-align: center;
  color: #606266;
}

.preview-fallback p {
  margin: 0;
  font-size: 14px;
  color: #303133;
}

.preview-fallback span {
  font-size: 12px;
  color: #86868B;
  word-break: break-all;
}

.preview-footer {
  display: flex;
  justify-content: flex-end;
}

.preview-download {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 6px;
  background: var(--uv-ws-action-button-bg, #A0522D);
  color: #fff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
}

.preview-download:hover {
  background: var(--uv-ws-action-button-hover, #8F4527);
}
</style>
