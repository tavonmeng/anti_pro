<template>
  <el-dialog
    v-model="visible"
    title="分配负责人"
    width="500px"
    @close="handleClose"
  >
    <div class="assignee-dialog-content">
      <el-form label-width="80px">
        <el-form-item label="搜索负责人">
          <div class="assignee-input-wrapper">
            <!-- 已选中的负责人tags -->
            <div class="selected-tags">
              <el-tag
                v-for="staff in selectedAssignees"
                :key="staff.id"
                closable
                @close="handleRemoveTag(staff.id)"
                class="assignee-tag"
              >
                {{ staff.realName || staff.username }}
              </el-tag>
            </div>
            <!-- 搜索输入框 -->
            <el-autocomplete
              v-model="searchText"
              :fetch-suggestions="querySearch"
              placeholder="搜索负责人姓名或用户名"
              @select="handleSelect"
              class="search-input"
              value-key="displayName"
            >
              <template #default="{ item }">
                <div class="autocomplete-item">
                  <div class="assignee-name">{{ item.realName || item.username }}</div>
                  <div class="assignee-meta">
                    <span>{{ item.username }}</span>
                    <span v-if="item.email">{{ item.email }}</span>
                  </div>
                </div>
              </template>
            </el-autocomplete>
          </div>
        </el-form-item>
      </el-form>
    </div>
    
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleConfirm" :disabled="selectedAssignees.length === 0">
        确认分配
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useStaffStore } from '@/stores/staff'
import type { User } from '@/types'

interface Props {
  modelValue: boolean
  currentAssigneeId?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [assignees: Array<{ id: string, name: string }>]
}>()

const staffStore = useStaffStore()
const visible = ref(props.modelValue)
const searchText = ref('')
const selectedAssignees = ref<User[]>([]) // 选中的负责人数组

// 过滤只显示staff角色的负责人
const staffList = computed(() => {
  return staffStore.staffList.filter(staff => staff.role === 'staff')
})

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    // 如果提供了currentAssigneeId，尝试找到对应的staff并选中
    // 注意：这里只支持单个ID的初始化，因为prop是单个ID
    // 如果需要支持多个，需要修改prop为数组类型
    if (props.currentAssigneeId) {
      const currentStaff = staffList.value.find(s => s.id === props.currentAssigneeId)
      if (currentStaff) {
        selectedAssignees.value = [currentStaff]
      } else {
        selectedAssignees.value = []
      }
    } else {
      selectedAssignees.value = []
    }
    searchText.value = ''
  } else {
    selectedAssignees.value = []
    searchText.value = ''
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// el-autocomplete的搜索建议方法（排除已选中的）
const querySearch = (queryString: string, cb: (suggestions: any[]) => void) => {
  if (!queryString || queryString.trim() === '') {
    cb([])
    return
  }
  
  const search = queryString.toLowerCase().trim()
  const selectedIds = selectedAssignees.value.map(s => s.id)
  const results = staffList.value
    .filter(staff => !selectedIds.includes(staff.id)) // 排除已选中的
    .filter(staff => {
      const username = staff.username?.toLowerCase() || ''
      const realName = staff.realName?.toLowerCase() || ''
      const email = staff.email?.toLowerCase() || ''
      return username.includes(search) || realName.includes(search) || email.includes(search)
    })
    .map(staff => ({
      ...staff,
      displayName: staff.realName || staff.username
    }))
  
  cb(results)
}

// 处理选择
const handleSelect = (item: User) => {
  // 检查是否已选中
  if (!selectedAssignees.value.find(s => s.id === item.id)) {
    selectedAssignees.value.push(item)
    searchText.value = '' // 清空搜索框，准备下次搜索
  }
}

// 处理删除tag
const handleRemoveTag = (staffId: string) => {
  selectedAssignees.value = selectedAssignees.value.filter(s => s.id !== staffId)
}

onMounted(() => {
  staffStore.fetchStaff()
})

const handleClose = () => {
  visible.value = false
  // 清空搜索框和选中列表
  searchText.value = ''
  selectedAssignees.value = []
}

const handleConfirm = () => {
  if (selectedAssignees.value.length === 0) {
    return
  }
  
  // 传递多个负责人信息
  const assignees = selectedAssignees.value.map(staff => ({
    id: staff.id,
    name: staff.realName || staff.username
  }))
  
  emit('confirm', assignees)
  handleClose()
}
</script>

<style lang="scss" scoped>
.assignee-dialog-content {
  max-height: 60vh;
  overflow-y: auto;
}

.assignee-input-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-height: 32px;
  padding: 4px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  
  &:focus-within {
    border-color: #409eff;
  }
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.assignee-tag {
  margin: 0;
  
  :deep(.el-tag__close) {
    color: #f56c6c; // 红色删除按钮
  }
}

.search-input {
  flex: 1;
  min-width: 120px;
  
  :deep(.el-input__inner) {
    border: none;
    box-shadow: none;
    
    &:focus {
      border: none;
      box-shadow: none;
    }
  }
}

.autocomplete-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  
  .assignee-name {
    font-size: 15px;
    font-weight: 500;
    color: #1D1D1F;
    opacity: 1; // 确保不透明
  }
  
  .assignee-meta {
    display: flex;
    gap: 12px;
    font-size: 13px;
    color: #86868B;
    opacity: 1; // 确保不透明
  }
}
</style>

