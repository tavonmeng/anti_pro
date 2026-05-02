<template>
  <div class="admin-order-detail-page">
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>
    
    <div v-else-if="!order" class="empty-state">
      <el-empty description="订单不存在" />
      <el-button type="primary" @click="goBack">返回订单列表</el-button>
    </div>
    
    <div v-else class="order-detail-content">
      <div class="page-header">
        <el-button :icon="ArrowLeft" @click="goBack">返回订单列表</el-button>
        <div class="header-actions">
          <el-button 
            :icon="User" 
            @click="handleAssign"
            :disabled="order.status === 'completed' || order.status === 'cancelled'"
          >
            {{ (order.assignees && order.assignees.length > 0) ? '重新分配负责人' : '分配负责人' }}
          </el-button>
          <el-button 
            :icon="Upload" 
            type="primary"
            @click="handleUploadPreview"
            :disabled="order.status === 'pending_assign' || order.status === 'pending_contract' || order.status === 'completed' || order.status === 'cancelled' || order.status === 'pending_review'"
          >
            上传预览文件
          </el-button>
          <el-dropdown trigger="click" @command="handlePdfDownload">
            <el-button :icon="Download">
              下载 PDF
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="confirmation">需求告知函</el-dropdown-item>
                <el-dropdown-item command="detail">订单详情报告</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      
      <el-card class="detail-card">
        <!-- 订单进度条 -->
        <div class="order-progress" style="margin-bottom: 30px; padding: 20px 10px; background: #fafafa; border-radius: 8px;">
          <el-steps :active="activeStep" :process-status="order.status === 'cancelled' ? 'error' : 'process'" finish-status="success" align-center>
            <el-step title="需求确认" description="收到订单" />
            <el-step title="合同与付款" description="签订合同、收取首付款" />
            <el-step title="内容制作" description="开发与设计环节" />
            <el-step title="初稿交付" description="内部审核与客户反馈" />
            <el-step title="终稿交付" description="内部审核与定稿" />
            <el-step title="项目完成" description="订单已结束" />
          </el-steps>
        </div>
        
        <template #header>
          <div class="card-header">
            <div>
              <h2 class="order-number">{{ order.orderNumber }}</h2>
              <p class="order-type-text">{{ orderTypeText }}</p>
            </div>
            <div class="header-right">
              <OrderStatusBadge :status="order.status" size="large" />
              <el-dropdown 
                @command="handleStatusChange" 
                v-if="order.status !== 'completed' && order.status !== 'cancelled' && order.status !== 'pending_review' && order.status !== 'pending_contract'"
              >
                <el-button>
                  更改状态
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="in_production" :disabled="order.status === 'in_production'">
                      制作中
                    </el-dropdown-item>
                    <el-dropdown-item command="preview_ready" :disabled="order.status === 'preview_ready'">
                      初稿预览
                    </el-dropdown-item>
                    <el-dropdown-item command="final_preview" :disabled="order.status === 'final_preview'">
                      终稿预览
                    </el-dropdown-item>
                    <el-dropdown-item command="completed">
                      已完成
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button 
                v-if="order.status === 'pending_contract'" 
                type="success" 
                @click="showContractDialog = true"
              >
                确认合同与付款
              </el-button>
              <el-button 
                v-if="order.status !== 'completed' && order.status !== 'cancelled'" 
                type="danger" 
                plain 
                @click="showCancelDialog = true"
              >
                取消订单
              </el-button>
            </div>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="创建时间">{{ formatTime(order.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(order.updatedAt) }}</el-descriptions-item>
          <el-descriptions-item label="提交用户">{{ order.userName }}</el-descriptions-item>
          <el-descriptions-item label="当前负责人">
            <div v-if="order.assignees && order.assignees.length > 0" class="assignees-list">
              <el-tag
                v-for="assignee in order.assignees"
                :key="assignee.id"
                size="small"
                class="assignee-tag"
              >
                {{ assignee.name }}
              </el-tag>
            </div>
            <el-tag v-else type="info" size="small">暂未分配</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="修改次数">
            <el-tag v-if="order.revisionCount > 0" type="warning">
              {{ order.revisionCount }}次
            </el-tag>
            <span v-else>0次</span>
          </el-descriptions-item>
          <el-descriptions-item label="反馈数量">{{ order.feedbacks.length }}条</el-descriptions-item>
        </el-descriptions>
        
        <!-- 订单详细信息 -->
        <div class="order-specific-info">
          <h3>订单详情</h3>
          <div v-if="order.orderType === 'video_purchase'">
            <el-row :gutter="20">
              <el-col :span="12"><p><strong>行业类型：</strong>{{ getIndustryText() }}</p></el-col>
              <el-col :span="12"><p><strong>视觉风格：</strong>{{ getStyleText() }}</p></el-col>
              <el-col :span="12"><p><strong>时长：</strong>{{ order.duration }}秒</p></el-col>
              <el-col :span="12"><p><strong>价格区间：</strong>¥{{ order.priceRange.min }} - ¥{{ order.priceRange.max }}</p></el-col>
              <el-col :span="12"><p><strong>分辨率：</strong>{{ order.resolution }}</p></el-col>
              <el-col :span="12"><p><strong>尺寸：</strong>{{ order.size }}</p></el-col>
              <el-col :span="12" v-if="order.curvature"><p><strong>曲率：</strong>{{ order.curvature }}</p></el-col>
            </el-row>
          </div>
          <div v-else-if="order.orderType === 'ai_3d_custom'">
            <!-- 媒体方订单详情 -->
            <template v-if="order.project_name">
              <el-descriptions :column="2" border size="small" style="margin-bottom: 20px;">
                <el-descriptions-item label="项目名称">{{ order.project_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="投放城市 & 媒体位置">{{ order.city_location || '-' }}</el-descriptions-item>
                <el-descriptions-item label="媒体定位 & 品牌调性">{{ order.media_positioning || '-' }}</el-descriptions-item>
                <el-descriptions-item label="艺术方向 & 风格偏好">{{ order.art_direction || '-' }}</el-descriptions-item>
                <el-descriptions-item label="内容主题 & 核心表达">{{ order.theme_concept || '-' }}</el-descriptions-item>
                <el-descriptions-item label="媒体尺寸 & 物理规格">{{ order.media_specs || '-' }}</el-descriptions-item>
                <el-descriptions-item label="技术需求">{{ order.tech_delivery || '-' }}</el-descriptions-item>
                <el-descriptions-item label="投放时长 & 数量">{{ order.timing_number || '-' }}</el-descriptions-item>
                <el-descriptions-item label="项目制作预算">{{ order.budget || '-' }}</el-descriptions-item>
                <el-descriptions-item label="预计上刊时间">{{ order.online_time || '-' }}</el-descriptions-item>
              </el-descriptions>
              
              <p><strong>项目背景 & 媒体简介：</strong></p>
              <p class="description-text">{{ order.resource_background || '-' }}</p>
              <p><strong>目标受众 & 场景特点：</strong></p>
              <p class="description-text">{{ order.audience_scene || '-' }}</p>
              <p><strong>观看动线说明：</strong></p>
              <p class="description-text">{{ order.viewing_path || '-' }}</p>
              <p v-if="order.content_review"><strong>素材审核规范 & 周期：</strong></p>
              <p v-if="order.content_review" class="description-text">{{ order.content_review }}</p>
              <p v-if="order.special_requirements"><strong>其他特殊合作要求：</strong></p>
              <p v-if="order.special_requirements" class="description-text">{{ order.special_requirements }}</p>
              <p v-if="order.remarks"><strong>备注：</strong></p>
              <p v-if="order.remarks" class="description-text">{{ order.remarks }}</p>
            </template>
            <!-- 品牌方订单详情（原版） -->
            <template v-else>
              <el-descriptions :column="2" border size="small" style="margin-bottom: 20px;">
                <el-descriptions-item label="品牌与产品关键词">{{ order.brand || '-' }}</el-descriptions-item>
                <el-descriptions-item label="目标受众">{{ order.target_group || '-' }}</el-descriptions-item>
                <el-descriptions-item label="品牌调性">{{ order.brand_tone || '-' }}</el-descriptions-item>
                <el-descriptions-item label="风格偏好">{{ order.style || '-' }}</el-descriptions-item>
                <el-descriptions-item label="投放城市/站点">{{ order.city || '-' }}</el-descriptions-item>
                <el-descriptions-item label="投放媒体尺寸">{{ order.media_size || '-' }}</el-descriptions-item>
                <el-descriptions-item label="投放时长数量">{{ order.time_number || '-' }}</el-descriptions-item>
                <el-descriptions-item label="技术需求">{{ order.technology || '-' }}</el-descriptions-item>
                <el-descriptions-item label="制作预算">{{ order.budget || '-' }}</el-descriptions-item>
                <el-descriptions-item label="预计上刊时间">{{ order.online_time || '-' }}</el-descriptions-item>
              </el-descriptions>
              
              <p><strong>项目背景：</strong></p>
              <p class="description-text">{{ order.background || '-' }}</p>
              <p><strong>内容需求：</strong></p>
              <p class="description-text">{{ order.content || '-' }}</p>
              <p><strong>品牌禁忌内容：</strong></p>
              <p class="description-text">{{ order.prohibited_content || '-' }}</p>
            </template>
            <div v-if="order.scenePhotos && order.scenePhotos.length > 0">
              <p><strong>现场实拍图（{{ order.scenePhotos.length }}张）：</strong></p>
              <div class="file-list">
                <div v-for="file in order.scenePhotos" :key="file.id" class="file-item">
                  <el-icon><Picture /></el-icon>
                  <span>{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="order.orderType === 'digital_art'">
            <p><strong>艺术方向：</strong>{{ getArtDirectionText() }}</p>
            <p><strong>说明文字：</strong></p>
            <p class="description-text">{{ order.description }}</p>
            <div v-if="order.materials.length > 0">
              <p><strong>相关材料（{{ order.materials.length }}个文件）：</strong></p>
              <div class="file-list">
                <div v-for="file in order.materials" :key="file.id" class="file-item">
                  <el-icon><Document /></el-icon>
                  <span>{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 预览审核记录 -->
        <div v-if="previewHistoryList.length" class="preview-history-section">
          <h3>预览审核记录</h3>
          <el-timeline>
            <el-timeline-item
              v-for="history in previewHistoryList"
              :key="history.id"
              :timestamp="formatTime(history.createdAt)"
              placement="top"
            >
              <el-card>
                <div class="preview-history-header">
                  <div class="preview-history-tags">
                    <el-tag type="info" size="small">
                      {{ history.previewType === 'final' ? '终稿预览' : '初稿预览' }}
                    </el-tag>
                    <el-tag :type="reviewTagType(history.reviewStatus)" size="small">
                      {{ reviewStatusText(history.reviewStatus) }}
                    </el-tag>
                  </div>
                  <span class="preview-history-user">{{ history.createdByName }}</span>
                </div>
                <div class="preview-files">
                  <div v-for="file in history.files" :key="file.id" class="file-item">
                    <a :href="file.url" target="_blank" class="file-link">
                      <el-icon><VideoPlay /></el-icon>
                      <span>{{ file.name }}</span>
                      <span class="file-size">{{ formatFileSize(file.size) }}</span>
                    </a>
                  </div>
                </div>
                <div v-if="history.note" class="preview-note-content">
                  <p class="note-text">{{ history.note }}</p>
                </div>
                <div v-if="history.reviewStatus !== 'pending'" class="review-info">
                  <p>
                    审核人：{{ history.reviewedByName || '管理员' }}
                    <span v-if="history.reviewedAt">（{{ formatTime(history.reviewedAt) }}）</span>
                  </p>
                  <p v-if="history.reviewNote">审核备注：{{ history.reviewNote }}</p>
                </div>
                <div v-else class="review-actions">
                  <el-button-group>
                    <el-button size="small" type="success" @click="handleReviewAction(history.id, 'approve')">
                      审核通过
                    </el-button>
                    <el-button size="small" type="danger" @click="handleReviewAction(history.id, 'reject')">
                      审核拒绝
                    </el-button>
                  </el-button-group>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
        
        <!-- 预览文件 -->
        <div v-if="hasPreviewFiles" class="preview-section">
          <h3>预览文件</h3>
          <div class="file-list">
            <div v-for="file in order.previewFiles" :key="file.id" class="file-item preview-file">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <span class="file-time">{{ formatTime(file.uploadTime) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 反馈记录 -->
        <div v-if="order.feedbacks.length > 0" class="feedback-section">
          <h3>客户反馈记录</h3>
          <el-timeline>
            <el-timeline-item
              v-for="feedback in order.feedbacks"
              :key="feedback.id"
              :timestamp="formatTime(feedback.createdAt)"
              placement="top"
            >
              <el-card>
                <div class="feedback-header">
                  <el-tag :type="feedback.type === 'approval' ? 'success' : 'warning'">
                    {{ feedback.type === 'approval' ? '确认通过' : '需要修改' }}
                  </el-tag>
                  <span class="feedback-user">{{ feedback.createdByName }}</span>
                </div>
                <p class="feedback-content">{{ feedback.content }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
      </el-card>

      <!-- 客户画像 Memory -->
      <el-card class="detail-card memory-card" style="margin-top: 20px;">
        <template #header>
          <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-icon><User /></el-icon>
              <h3 style="margin: 0;">客户画像</h3>
              <el-tag v-if="memoryData?.company_info?.crawl_status === 'success'" type="success" size="small">已分析</el-tag>
              <el-tag v-else-if="memoryData?.company_info?.crawl_status === 'pending'" type="warning" size="small">分析中</el-tag>
              <el-tag v-else-if="memoryData?.company_info?.crawl_status === 'failed'" type="danger" size="small">分析失败</el-tag>
              <el-tag v-else type="info" size="small">未分析</el-tag>
            </div>
            <div style="display: flex; gap: 8px;">
              <el-button size="small" @click="handleTriggerCrawl" :loading="crawlLoading">
                {{ memoryData?.company_info?.crawl_status === 'success' ? '重新分析' : '分析官网' }}
              </el-button>
              <el-button size="small" @click="showMemory = !showMemory">
                {{ showMemory ? '收起' : '展开' }}
              </el-button>
            </div>
          </div>
        </template>

        <div v-show="showMemory">
          <!-- 公司信息 -->
          <div v-if="memoryData?.company_info?.description" class="memory-section">
            <h4>公司信息</h4>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="公司名称">{{ memoryData.company_info.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="官网">
                <a v-if="memoryData.company_info.website" :href="memoryData.company_info.website" target="_blank" style="color: #409eff;">
                  {{ memoryData.company_info.website }}
                </a>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="简介">{{ memoryData.company_info.description }}</el-descriptions-item>
              <el-descriptions-item label="核心优势" v-if="memoryData.company_info.advantages?.length">
                <el-tag v-for="adv in memoryData.company_info.advantages" :key="adv" size="small" style="margin-right: 4px;">{{ adv }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="分析时间">{{ memoryData.company_info.crawled_at || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 屏幕资源 -->
          <div v-if="memoryData?.screen_resources?.length" class="memory-section">
            <h4>屏幕资源（{{ memoryData.screen_resources.length }} 块）</h4>
            <el-table :data="memoryData.screen_resources" size="small" border stripe>
              <el-table-column prop="city" label="城市" width="80" />
              <el-table-column prop="location" label="位置" min-width="120" />
              <el-table-column prop="type" label="类型" width="120" />
              <el-table-column prop="size" label="尺寸" width="80" />
              <el-table-column prop="resolution" label="分辨率" width="100" />
              <el-table-column prop="daily_traffic" label="日均客流" width="100" />
            </el-table>
          </div>

          <!-- 项目偏好 -->
          <div v-if="memoryData?.project_preferences && hasPreferences" class="memory-section">
            <h4>
              项目偏好
              <span v-if="memoryData.project_preferences.last_updated" style="font-weight: normal; font-size: 12px; color: #909399; margin-left: 8px;">
                更新于 {{ formatShortTime(memoryData.project_preferences.last_updated) }}
              </span>
            </h4>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="常用城市">{{ memoryData.project_preferences.common_cities?.join('、') || '-' }}</el-descriptions-item>
              <el-descriptions-item label="偏好风格">{{ memoryData.project_preferences.preferred_styles?.join('、') || '-' }}</el-descriptions-item>
              <el-descriptions-item label="预算范围">{{ memoryData.project_preferences.budget_range || '-' }}</el-descriptions-item>
              <el-descriptions-item label="典型时长">{{ memoryData.project_preferences.typical_duration || '-' }}</el-descriptions-item>
              <el-descriptions-item v-if="memoryData.project_preferences.notes" label="备注" :span="2">{{ memoryData.project_preferences.notes }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 历史项目 -->
          <div v-if="memoryData?.past_projects?.length" class="memory-section">
            <h4>历史项目（{{ memoryData.past_projects.length }} 个）</h4>
            <el-table :data="memoryData.past_projects" size="small" border stripe>
              <el-table-column prop="order_number" label="订单号" width="160" />
              <el-table-column prop="project_name" label="项目名称" min-width="120" />
              <el-table-column prop="city" label="城市" width="80" />
              <el-table-column prop="status" label="状态" width="80" />
              <el-table-column label="更新时间" width="110">
                <template #default="{ row }">{{ formatShortTime(row.updated_at) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 交互统计 -->
          <div v-if="memoryData?.interaction_stats?.total_sessions" class="memory-section">
            <h4>交互统计</h4>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="对话次数">{{ memoryData.interaction_stats.total_sessions }}</el-descriptions-item>
              <el-descriptions-item label="首次接触">{{ formatShortTime(memoryData.interaction_stats.first_contact) }}</el-descriptions-item>
              <el-descriptions-item label="最近接触">{{ formatShortTime(memoryData.interaction_stats.last_contact) }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- Agent 备忘 -->
          <div class="memory-section">
            <h4>Agent 备忘录</h4>
            <el-input
              v-model="agentNotes"
              type="textarea"
              :rows="3"
              placeholder="管理员可在此添加关于该客户的备注信息..."
            />
            <el-button size="small" type="primary" style="margin-top: 8px;" @click="handleSaveNotes" :loading="notesLoading">
              保存备忘
            </el-button>
          </div>

          <!-- 空状态 -->
          <div v-if="!memoryData?.company_info?.description && !memoryData?.screen_resources?.length && !memoryData?.past_projects?.length" style="text-align: center; padding: 20px; color: #999;">
            暂无画像数据。点击「分析官网」可自动爬取客户公司信息。
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 分配负责人对话框 -->
    <AssigneeDialog
      v-model="assignDialogVisible"
      :current-assignee-id="order?.assignees?.[0]?.id"
      @confirm="handleAssignConfirm"
    />
    
    <!-- 上传预览对话框 -->
    <UploadPreviewDialog
      v-model="uploadDialogVisible"
      :order="order"
      @confirm="handleUploadConfirm"
    />
    
    <!-- 合同与付款确认对话框 -->
    <el-dialog v-model="showContractDialog" title="确认合同与付款" width="520px" destroy-on-close>
      <el-form :model="contractForm" label-width="100px" label-position="top">
        <el-form-item label="合同编号" required>
          <el-input v-model="contractForm.contractNumber" placeholder="请输入合同编号" />
        </el-form-item>
        <el-form-item label="首付款金额（元）" required>
          <el-input-number v-model="contractForm.paymentAmount" :min="0" :precision="2" :step="1000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="contractForm.note" type="textarea" :rows="3" placeholder="选填，如合同签订日期、付款方式等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showContractDialog = false">取消</el-button>
        <el-button type="success" @click="handleContractAdvance" :loading="contractLoading"
          :disabled="!contractForm.contractNumber || !contractForm.paymentAmount">
          确认并推进到制作阶段
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 管理员取消订单对话框（SMS验证） -->
    <el-dialog v-model="showCancelDialog" title="取消订单" width="480px" destroy-on-close>
      <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
        取消订单需要进行手机验证码确认，此操作不可撤回。
      </el-alert>
      <el-form :model="cancelForm" label-width="100px" label-position="top">
        <el-form-item label="手机号">
          <el-input v-model="cancelForm.phone" placeholder="管理员手机号">
            <template #append>
              <el-button 
                :disabled="smsCooldown > 0" 
                @click="sendCancelSms"
                :loading="smsLoading"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s 后重试` : '发送验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="验证码">
          <el-input v-model="cancelForm.smsCode" placeholder="请输入短信验证码" maxlength="6" />
        </el-form-item>
        <el-form-item label="取消原因">
          <el-input v-model="cancelForm.reason" type="textarea" :rows="3" placeholder="选填，取消原因将通知客户" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCancelDialog = false">返回</el-button>
        <el-button type="danger" @click="handleAdminCancel" :loading="cancelLoading"
          :disabled="!cancelForm.phone || !cancelForm.smsCode">
          确认取消订单
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, User, Upload, ArrowDown, Picture, Document as DocumentIcon, VideoPlay, Download } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useOrderStore } from '@/stores/order'
import { orderApi, authApi } from '@/utils/api'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import AssigneeDialog from '@/components/AssigneeDialog.vue'
import UploadPreviewDialog from '@/components/UploadPreviewDialog.vue'
import type { Order, OrderStatus, VideoPurchaseOrder, DigitalArtOrder, UploadedFile } from '@/types'

const router = useRouter()
const route = useRoute()
const orderStore = useOrderStore()

const order = ref<Order | null>(null)
const loading = ref(true)
const assignDialogVisible = ref(false)
const uploadDialogVisible = ref(false)
const showContractDialog = ref(false)
const showCancelDialog = ref(false)
const contractLoading = ref(false)
const cancelLoading = ref(false)
const smsLoading = ref(false)
const smsCooldown = ref(0)

// Memory 相关状态
const memoryData = ref<any>(null)
const showMemory = ref(false)
const agentNotes = ref('')
const crawlLoading = ref(false)
const notesLoading = ref(false)

// 判断偏好是否有实质内容（排除内部时间戳字段）
const hasPreferences = computed(() => {
  const pp = memoryData.value?.project_preferences
  if (!pp) return false
  const dataKeys = Object.keys(pp).filter(k => !k.startsWith('_') && k !== 'last_updated')
  return dataKeys.length > 0
})

// ISO 时间格式化为简短显示
const formatShortTime = (iso: string | undefined) => {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hour = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${d.getFullYear()}-${month}-${day} ${hour}:${min}`
  } catch {
    return iso.slice(0, 16).replace('T', ' ')
  }
}

const contractForm = ref({
  contractNumber: '',
  paymentAmount: 0,
  note: ''
})

const cancelForm = ref({
  phone: '',
  smsCode: '',
  reason: ''
})

const orderTypeMap: Record<string, string> = {
  video_purchase: '裸眼3D成片购买适配',
  ai_3d_custom: 'AI裸眼3D内容定制',
  digital_art: '数字艺术内容定制'
}

const orderTypeText = computed(() => {
  return order.value ? orderTypeMap[order.value.orderType] || order.value.orderType : ''
})

const hasPreviewFiles = computed(() => {
  if (!order.value) return false
  if (order.value.orderType === 'ai_3d_custom' || order.value.orderType === 'digital_art') {
    return order.value.previewFiles && order.value.previewFiles.length > 0
  }
  return false
})

const previewHistoryList = computed(() => {
  if (!order.value?.previewHistory) return []
  return [...order.value.previewHistory].sort((a, b) => {
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })
})

const activeStep = computed(() => {
  if (!order.value) return 0
  const status = order.value.status
  switch(status) {
    case 'draft': return 0
    case 'pending_assign': return 0
    case 'pending_contract': return 1
    case 'in_production': return 2
    case 'pending_review': 
    case 'review_rejected':
    case 'preview_ready':
    case 'revision_needed':
      const isFinal = previewHistoryList.value.some(h => h.previewType === 'final')
      return isFinal ? 4 : 3
    case 'final_preview': return 4
    case 'completed': return 6
    case 'cancelled': return 0
    default: return 0
  }
})

onMounted(async () => {
  const orderId = route.params.id as string
  order.value = await orderStore.getOrderDetail(orderId)
  loading.value = false

  // 加载用户 Memory
  if (order.value?.userId) {
    await loadMemory(order.value.userId)
  }
})

const loadMemory = async (userId: string) => {
  try {
    const token = localStorage.getItem('admin_token')
    const resp = await fetch(`/api/admin/memory/${userId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (resp.ok) {
      memoryData.value = await resp.json()
      agentNotes.value = memoryData.value?.agent_notes || ''
    }
  } catch (e) {
    console.error('Memory 加载失败:', e)
  }
}

const handleTriggerCrawl = async () => {
  if (!order.value?.userId) return
  // 使用 memory 返回的 user_company，或发送空字符串让后端自动获取
  const companyName = memoryData.value?.user_company || ''
  crawlLoading.value = true
  try {
    const token = localStorage.getItem('admin_token')
    const resp = await fetch(`/api/admin/memory/${order.value.userId}/crawl`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ company_name: companyName })
    })
    if (resp.ok) {
      ElMessage.success('已触发官网分析，请稍后刷新查看结果')
      // 5 秒后自动刷新 memory
      setTimeout(async () => {
        if (order.value?.userId) {
          await loadMemory(order.value.userId)
        }
        crawlLoading.value = false
      }, 8000)
    } else {
      ElMessage.error('触发分析失败')
      crawlLoading.value = false
    }
  } catch (e) {
    ElMessage.error('触发分析失败')
    crawlLoading.value = false
  }
}

const handleSaveNotes = async () => {
  if (!order.value?.userId) return
  notesLoading.value = true
  try {
    const token = localStorage.getItem('admin_token')
    const resp = await fetch(`/api/admin/memory/${order.value.userId}/notes`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ agent_notes: agentNotes.value })
    })
    if (resp.ok) {
      ElMessage.success('备忘已保存')
    } else {
      ElMessage.error('保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    notesLoading.value = false
  }
}

const getIndustryText = () => {
  if (order.value && order.value.orderType === 'video_purchase') {
    const vOrder = order.value as VideoPurchaseOrder
    if (vOrder.industryType === 'custom') {
      return vOrder.customIndustry || '自定义'
    }
    const map: Record<string, string> = {
      movie: '电影',
      outdoor: '户外'
    }
    return map[vOrder.industryType] || vOrder.industryType
  }
  return '-'
}

const getStyleText = () => {
  if (order.value && order.value.orderType === 'video_purchase') {
    const vOrder = order.value as VideoPurchaseOrder
    if (vOrder.visualStyle === 'custom') {
      return vOrder.customStyle || '自定义'
    }
    const map: Record<string, string> = {
      scifi: '科幻',
      realistic: '写真'
    }
    return map[vOrder.visualStyle] || vOrder.visualStyle
  }
  return '-'
}

const getArtDirectionText = () => {
  if (order.value && order.value.orderType === 'digital_art') {
    const dOrder = order.value as DigitalArtOrder
    if (dOrder.artDirection === 'custom') {
      return dOrder.customDirection || '自定义'
    }
    const map: Record<string, string> = {
      abstract: '抽象',
      realistic: '写实',
      installation: '装置',
      dynamic: '动态艺术'
    }
    return map[dOrder.artDirection] || dOrder.artDirection
  }
  return '-'
}

const formatTime = (timeString: string) => {
  if (!timeString) return '-'
  const date = new Date(timeString)
  if (isNaN(date.getTime())) {
    return timeString
  }
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const handleAssign = () => {
  assignDialogVisible.value = true
}

const handleAssignConfirm = async (assignees: Array<{ id: string, name: string }>) => {
  if (!order.value) return
  
  if (assignees.length > 0) {
    await orderStore.assignOrder(order.value.id, assignees)
    order.value = await orderStore.getOrderDetail(order.value.id)
  }
}

const handleUploadPreview = () => {
  uploadDialogVisible.value = true
}

const handleUploadConfirm = async (files: UploadedFile[], previewType: string, note: string) => {
  if (!order.value) return
  
  await orderStore.uploadPreview(order.value.id, files, previewType === 'final' ? 'final' : 'initial', note)
  order.value = await orderStore.getOrderDetail(order.value.id)
}

const handleReviewAction = async (previewId: string, action: 'approve' | 'reject') => {
  if (!order.value) return
  
  try {
    if (action === 'reject') {
      const { value } = await ElMessageBox.prompt(
        '请输入拒绝原因（可选）',
        '审核拒绝',
        {
          confirmButtonText: '确认拒绝',
          cancelButtonText: '取消',
          inputType: 'textarea',
          inputPlaceholder: '请填写审核拒绝原因',
          inputValidator: (val: string) => val.length <= 500 || '拒绝原因长度不能超过500个字符'
        }
      )
      await orderStore.reviewPreview(order.value.id, { previewId, action, note: value })
    } else {
      await ElMessageBox.confirm(
        '确认通过该预览审核？',
        '确认审核',
        { type: 'success' }
      )
      await orderStore.reviewPreview(order.value.id, { previewId, action })
    }
  order.value = await orderStore.getOrderDetail(order.value.id)
  } catch {
    // 用户取消或审核失败
  }
}

const handleStatusChange = async (status: OrderStatus) => {
  if (!order.value) return
  
  try {
    await ElMessageBox.confirm(
      `确定要将订单状态更改为"${getStatusText(status)}"吗？`,
      '确认更改',
      {
        type: 'warning'
      }
    )
    
    await orderStore.updateOrderStatus(order.value.id, status)
    order.value = await orderStore.getOrderDetail(order.value.id)
  } catch {
    // 用户取消
  }
}

const getStatusText = (status: OrderStatus): string => {
  const map: Record<OrderStatus, string> = {
    pending_assign: '待分配',
    pending_contract: '合同与付款',
    in_production: '制作中',
    pending_review: '待审核',
    preview_ready: '初稿预览',
    review_rejected: '审核拒绝',
    revision_needed: '需要修改',
    final_preview: '终稿预览',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status
}

const reviewStatusText = (status: 'pending' | 'approved' | 'rejected') => {
  const map: Record<typeof status, string> = {
    pending: '待审核',
    approved: '审核通过',
    rejected: '审核拒绝'
  }
  return map[status]
}

const reviewTagType = (status: 'pending' | 'approved' | 'rejected') => {
  const map: Record<typeof status, 'warning' | 'success' | 'danger'> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  }
  return map[status]
}

const handlePdfDownload = async (type: string) => {
  if (!order.value) return
  try {
    if (type === 'confirmation') {
      await orderApi.downloadConfirmationPdf(order.value.id)
    } else {
      await orderApi.downloadDetailPdf(order.value.id)
    }
    ElMessage.success('PDF 下载成功')
  } catch (error) {
    console.error('下载 PDF 失败:', error)
    ElMessage.error('下载 PDF 失败')
  }
}

const goBack = () => {
  router.push('/admin')
}

// 合同推进
const handleContractAdvance = async () => {
  if (!order.value) return
  contractLoading.value = true
  try {
    await orderApi.advanceContract(order.value.id, {
      contractNumber: contractForm.value.contractNumber,
      paymentAmount: contractForm.value.paymentAmount,
      note: contractForm.value.note
    })
    ElMessage.success('合同确认成功，订单已进入制作阶段')
    showContractDialog.value = false
    order.value = await orderStore.getOrderDetail(order.value.id)
  } catch (error: any) {
    ElMessage.error(error?.message || '操作失败')
  } finally {
    contractLoading.value = false
  }
}

// 发送取消验证码
const sendCancelSms = async () => {
  if (!cancelForm.value.phone) {
    ElMessage.warning('请先输入手机号')
    return
  }
  smsLoading.value = true
  try {
    await authApi.sendSms(cancelForm.value.phone)
    ElMessage.success('验证码已发送')
    smsCooldown.value = 60
    const timer = setInterval(() => {
      smsCooldown.value--
      if (smsCooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (error: any) {
    ElMessage.error(error?.message || '发送失败')
  } finally {
    smsLoading.value = false
  }
}

// 管理员取消订单
const handleAdminCancel = async () => {
  if (!order.value) return
  cancelLoading.value = true
  try {
    await orderApi.adminCancelOrder(order.value.id, {
      phone: cancelForm.value.phone,
      smsCode: cancelForm.value.smsCode,
      reason: cancelForm.value.reason
    })
    ElMessage.success('订单已取消')
    showCancelDialog.value = false
    order.value = await orderStore.getOrderDetail(order.value.id)
  } catch (error: any) {
    ElMessage.error(error?.message || '取消失败')
  } finally {
    cancelLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.admin-order-detail-page {
  padding: 24px;
}

.loading-state,
.empty-state {
  padding: 60px 0;
  text-align: center;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.detail-card {
  border-radius: 12px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  .order-number {
    font-size: 24px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 0 0 4px 0;
  }
  
  .order-type-text {
    font-size: 14px;
    color: #86868B;
    margin: 0;
  }
}

.order-specific-info,
.preview-section,
.preview-history-section,
.feedback-section {
  margin-top: 32px;
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    color: #1D1D1F;
    margin: 0 0 16px 0;
  }
  
  p {
    margin: 8px 0;
    font-size: 14px;
    color: #515154;
    
    strong {
      color: #1D1D1F;
      font-weight: 500;
    }
  }
  
  .description-text {
    white-space: pre-wrap;
    line-height: 1.6;
    padding: 12px;
    background: #F5F5F7;
    border-radius: 8px;
  }
}

.preview-history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-history-tags {
  display: flex;
  gap: 8px;
}

.preview-history-user {
  font-size: 13px;
  color: #86868B;
}

.preview-note-content {
  margin-top: 12px;
  padding: 12px;
  background: #FFFBE6;
  border-radius: 8px;
  color: #8B7416;
  line-height: 1.6;
}

.review-info {
  margin-top: 12px;
  font-size: 13px;
  color: #515154;
  
  p {
    margin: 4px 0;
  }
}

.review-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #F5F5F7;
  border-radius: 8px;
  font-size: 14px;
  
  .el-icon {
    font-size: 20px;
    color: #667eea;
  }
  
  span:first-of-type {
    flex: 1;
    color: #1D1D1F;
  }
  
  .file-size,
  .file-time {
    color: #86868B;
    font-size: 13px;
  }
}

.file-link {
  display: flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
  flex: 1;
}

.preview-file {
  background: #E8F5E9;
  
  .el-icon {
    color: #4CAF50;
  }
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.feedback-user {
  font-size: 13px;
  color: #86868B;
}

.feedback-content {
  margin: 0;
  font-size: 14px;
  color: #515154;
  line-height: 1.6;
}

.assignees-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.assignee-tag {
  margin: 0;
}

/* Memory 面板样式 */
.memory-section {
  margin-bottom: 24px;
}

.memory-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.memory-card .el-descriptions {
  margin-bottom: 0;
}
</style>

