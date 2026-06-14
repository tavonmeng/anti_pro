<template>
  <div class="creative-agent-page">
    <div class="page-header">
      <div>
        <h2>创意 Agent</h2>
        <p>把订单 brief、设计方向和团队经验交给 Hermes，生成并迭代创意方案。</p>
      </div>
      <div class="header-actions">
        <div class="provider-switch" aria-label="创意 Agent 后端">
          <span>后端</span>
          <el-radio-group v-model="agentProvider" size="small" @change="persistAgentProvider">
            <el-radio-button label="hermes" :disabled="!isProviderAvailable('hermes')">Hermes</el-radio-button>
            <el-radio-button label="direct_ai" :disabled="!isProviderAvailable('direct_ai')">Direct</el-radio-button>
          </el-radio-group>
        </div>
        <el-tag :type="hermesStatus.enabled ? 'success' : 'info'" effect="plain">
          {{ agentStatusLabel }}
        </el-tag>
        <el-button @click="openAgentConfig">Agent 配置</el-button>
        <el-button :icon="Refresh" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <div class="workspace-grid">
      <aside class="session-panel">
        <div class="panel-head">
          <h3>会话</h3>
          <el-button type="primary" :icon="Plus" @click="createSession" :loading="creating">新建</el-button>
        </div>

        <el-input
          v-model="keyword"
          placeholder="搜索创意会话"
          clearable
          @keyup.enter="loadSessions"
          @clear="loadSessions"
        />

        <div v-loading="sessionsLoading" class="session-list">
          <div
            v-for="session in sessions"
            :key="session.id"
            :class="['session-item', activeSession?.id === session.id ? 'active' : '']"
            role="button"
            tabindex="0"
            @click="openSession(session.id)"
            @keyup.enter="openSession(session.id)"
          >
            <div class="session-item-main">
              <strong>{{ session.title }}</strong>
              <span>{{ statusLabel(session.status) }} · {{ session.source_type === 'order' ? '订单' : '手动' }}</span>
            </div>
            <el-button
              class="session-delete"
              :icon="Delete"
              text
              type="danger"
              aria-label="删除会话"
              title="删除会话"
              :loading="deletingSessionId === session.id"
              @click.stop="confirmDeleteSession(session)"
            />
          </div>
          <el-empty v-if="!sessionsLoading && sessions.length === 0" description="暂无创意会话" :image-size="90" />
        </div>
      </aside>

      <main class="detail-panel">
        <div v-if="!activeSession" class="empty-state">
          <h3>创建一个创意会话</h3>
          <p>可以从订单读取 brief，也可以手动输入项目背景后启动 Agent。</p>
        </div>

        <template v-else>
          <div class="detail-head">
            <div>
              <h3>{{ activeSession.title }}</h3>
              <p>{{ activeSession.source_order_id ? `订单 ${activeSession.source_order_id}` : '手动创建' }}</p>
            </div>
          </div>

          <div class="mobile-tab-nav" aria-label="创意 Agent 页面切换">
            <button :class="{ active: activeTab === 'feedback' }" type="button" @click="activeTab = 'feedback'">对话</button>
            <button :class="{ active: activeTab === 'ideas' }" type="button" @click="activeTab = 'ideas'">方案</button>
            <button :class="{ active: activeTab === 'runs' }" type="button" @click="activeTab = 'runs'">运行</button>
            <button :class="{ active: activeTab === 'brief' }" type="button" @click="activeTab = 'brief'">Brief</button>
          </div>

          <el-tabs v-model="activeTab" class="agent-conversation-tabs">
            <el-tab-pane label="Brief" name="brief">
              <div class="form-grid">
                <el-form label-position="top">
                  <el-form-item label="项目名称">
                    <el-input v-model="briefForm.project_name" placeholder="例如：裸眼 3D 开业传播视频" />
                  </el-form-item>
                  <el-form-item label="客户/品牌">
                    <el-input v-model="briefForm.brand" placeholder="客户或品牌名称" />
                  </el-form-item>
                  <el-form-item label="业务目标">
                    <el-input v-model="briefForm.objective" type="textarea" :rows="4" placeholder="传播目标、核心卖点、投放场景" />
                  </el-form-item>
                  <el-form-item label="项目背景 & 媒体简介">
                    <el-input v-model="briefForm.resource_background" type="textarea" :rows="4" placeholder="订单中的项目背景、媒体资源简介、位置特点等" />
                  </el-form-item>
                  <el-form-item label="媒体定位 & 品牌调性">
                    <el-input v-model="briefForm.media_positioning" type="textarea" :rows="3" placeholder="媒体定位、品牌调性或品牌资产特点" />
                  </el-form-item>
                  <el-form-item label="主题内容">
                    <el-input v-model="briefForm.theme_concept" type="textarea" :rows="3" placeholder="订单主题、内容方向、核心信息" />
                  </el-form-item>
                  <el-form-item label="受众和场景">
                    <el-input v-model="briefForm.audience" type="textarea" :rows="3" placeholder="目标人群、观看设备、屏幕环境" />
                  </el-form-item>
                  <el-form-item label="观看动线说明">
                    <el-input v-model="briefForm.viewing_path" type="textarea" :rows="3" placeholder="观看距离、方向、人流动线、最佳观看点" />
                  </el-form-item>
                  <el-form-item label="投放位置">
                    <el-input v-model="briefForm.media_location" placeholder="城市、商圈、屏幕位置" />
                  </el-form-item>
                  <el-form-item label="屏幕资源">
                    <el-input v-model="briefForm.screen_resource_summary" type="textarea" :rows="3" placeholder="屏幕类型、尺寸、分辨率、形状" />
                  </el-form-item>
                  <el-form-item label="艺术方向 & 风格偏好">
                    <el-input v-model="briefForm.art_direction" type="textarea" :rows="3" placeholder="艺术方向、风格偏好、视觉气质" />
                  </el-form-item>
                  <el-form-item label="硬性限制">
                    <el-input v-model="briefForm.constraints" type="textarea" :rows="3" placeholder="时长、品牌禁忌、交付格式等，不含预算和交付时间" />
                  </el-form-item>
                  <el-form-item label="素材审核规范 & 周期">
                    <el-input v-model="briefForm.content_review" type="textarea" :rows="3" placeholder="素材审核规范、报审流程、禁忌要求等" />
                  </el-form-item>
                  <el-form-item label="特殊合作要求 / 备注">
                    <el-input v-model="briefForm.special_notes" type="textarea" :rows="3" placeholder="特殊合作要求、备注等设计相关信息" />
                  </el-form-item>
                </el-form>

                <el-form label-position="top">
                  <el-form-item label="设计方向">
                    <el-input v-model="activeSession.designer_direction" type="textarea" :rows="8" placeholder="设计师想保留、加强或避免的方向" />
                  </el-form-item>
                  <el-form-item label="从订单读取">
                    <div class="inline-row">
                      <el-select
                        v-model="orderId"
                        placeholder="选择订单"
                        filterable
                        clearable
                        :loading="ordersLoading"
                        @change="handleOrderSelect"
                      >
                        <el-option
                          v-for="order in orderOptions"
                          :key="order.id"
                          :label="orderOptionLabel(order)"
                          :value="order.id"
                        />
                      </el-select>
                      <el-button :icon="Document" @click="loadOrderBrief" :loading="briefLoading">读取</el-button>
                    </div>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="saveSession" :loading="saving">保存 Brief</el-button>
                  </el-form-item>
                </el-form>
              </div>
            </el-tab-pane>

            <el-tab-pane :label="`方案 ${activeSession.ideas?.length || 0}`" name="ideas">
              <div class="section-actions">
                <el-button :icon="Plus" @click="ideaDialogVisible = true">添加人工方案</el-button>
              </div>
              <div class="idea-grid">
                <article v-for="idea in activeSession.ideas" :key="idea.id" class="idea-card">
                  <div class="idea-head">
                    <h4>{{ idea.title || `方案 V${idea.version}` }}</h4>
                    <el-tag v-if="idea.score !== null && idea.score !== undefined" type="success">{{ idea.score }} 分</el-tag>
                  </div>
                  <dl>
                    <dt>创意概念 · 15%</dt>
                    <dd>{{ idea.core_concept || '-' }}</dd>
                    <dt>灵感来源 · 15%</dt>
                    <dd>{{ idea.spatial_mechanism || '-' }}</dd>
                    <dt>方案脚本 · 35%</dt>
                    <dd>{{ idea.story_outline || '-' }}</dd>
                    <dt>风格参考 · 15%</dt>
                    <dd>{{ idea.production_notes || '-' }}</dd>
                  </dl>
                  <div class="idea-actions">
                    <el-button size="small" plain @click="openFeedbackForIdea(idea)">反馈迭代</el-button>
                    <el-button size="small" @click="runIdea(idea.id, 'evaluate')">打分</el-button>
                    <el-button size="small" type="primary" plain @click="runIdea(idea.id, 'iterate')">迭代</el-button>
                  </div>
                </article>
              </div>
              <el-empty v-if="!activeSession.ideas?.length" description="还没有方案" :image-size="90" />
            </el-tab-pane>

            <el-tab-pane :label="`运行 ${activeSession.runs?.length || 0}`" name="runs">
              <div class="run-list">
                <article v-for="run in activeSession.runs" :key="run.id" class="run-card">
                  <div class="run-card-head">
                    <div>
                      <h4>{{ runTypeLabel(run.run_type) }}</h4>
                      <p>{{ run.created_at || '-' }}</p>
                    </div>
                    <div class="run-meta">
                      <el-tag effect="plain">{{ run.provider === 'direct_ai' ? 'Direct' : 'Hermes' }}</el-tag>
                      <el-tag :type="runStatusType(run.status)">{{ statusLabel(run.status) }}</el-tag>
                    </div>
                  </div>
                  <div v-if="runEventItems(run).length" class="run-event-stream">
                    <div v-for="event in runEventItems(run)" :key="event.id" class="run-event-item">
                      <span class="event-dot" />
                      <div class="event-copy">
                        <div class="event-line">
                          <strong>{{ eventLabel(event.event_type) }}</strong>
                          <span>{{ event.created_at || '-' }}</span>
                        </div>
                        <p>{{ event.message || event.event_type }}</p>
                        <small v-if="eventBrief(event)">{{ eventBrief(event) }}</small>
                        <details v-if="hasEventDetails(event, run)" class="detail-disclosure">
                          <summary>详情</summary>
                          <dl v-if="eventDetailRows(event, run).length" class="detail-kv">
                            <template v-for="row in eventDetailRows(event, run)" :key="row.label">
                              <dt>{{ row.label }}</dt>
                              <dd>{{ row.value }}</dd>
                            </template>
                          </dl>
                          <div v-if="eventNarrative(event, run)" class="agent-narrative">
                            <p v-if="eventNarrative(event, run)?.summary" class="agent-summary">
                              {{ eventNarrative(event, run)?.summary }}
                            </p>
                            <div v-if="eventNarrative(event, run)?.steps?.length" class="agent-flow">
                              <div v-for="item in eventNarrative(event, run)?.steps" :key="`event-step-${item.step}-${item.title}`" class="agent-flow-item">
                                <span class="agent-flow-index">{{ item.step || '·' }}</span>
                                <div>
                                  <div class="agent-flow-head">
                                    <strong>{{ item.title }}</strong>
                                    <el-tag v-if="item.phase" size="small" effect="plain">{{ item.phase }}</el-tag>
                                  </div>
                                  <p v-if="item.body">{{ item.body }}</p>
                                  <dl v-if="item.rows?.length" class="agent-mini-kv">
                                    <template v-for="row in item.rows" :key="row.label">
                                      <dt>{{ row.label }}</dt>
                                      <dd>{{ row.value }}</dd>
                                    </template>
                                  </dl>
                                </div>
                              </div>
                            </div>
                            <div v-if="eventNarrative(event, run)?.iterations?.length" class="agent-card-grid">
                              <article v-for="item in eventNarrative(event, run)?.iterations" :key="`event-iteration-${item.round}`" class="agent-mini-card">
                                <strong>第 {{ item.round }} 轮</strong>
                                <span>{{ item.score_before }} → {{ item.score_after }} 分</span>
                                <p>{{ item.summary || item.focus }}</p>
                                <small v-if="item.agent_explanation">{{ item.agent_explanation }}</small>
                              </article>
                            </div>
                            <div v-if="eventNarrative(event, run)?.ideas?.length" class="agent-card-grid">
                              <article v-for="idea in eventNarrative(event, run)?.ideas" :key="`event-idea-${idea.title}`" class="agent-mini-card">
                                <strong>{{ idea.title || '方案' }}</strong>
                                <span v-if="idea.score !== undefined && idea.score !== null">{{ idea.score }} 分</span>
                                <p>{{ idea.core_concept || idea.story_outline }}</p>
                                <small v-if="idea.spatial_mechanism">{{ idea.spatial_mechanism }}</small>
                              </article>
                            </div>
                            <div v-if="eventNarrative(event, run)?.scores?.length" class="score-matrix">
                              <div v-for="score in eventNarrative(event, run)?.scores" :key="`score-${score.idea_index}`" class="score-row">
                                <strong>方案 {{ Number(score.idea_index || 0) + 1 }}</strong>
                                <span>{{ score.total_score }} 分</span>
                                <small>目标匹配 {{ score.goal_fit }} · 视觉冲击 {{ score.visual_impact }} · 裸眼3D {{ score.naked_eye_3d_fit }}</small>
                              </div>
                            </div>
                          </div>
                          <pre v-else-if="eventDetailJson(event, run)" class="detail-json">{{ eventDetailJson(event, run) }}</pre>
                        </details>
                      </div>
                    </div>
                  </div>
                </article>
              </div>

              <el-empty v-if="!activeSession.runs?.length" description="还没有运行记录" :image-size="90" />
            </el-tab-pane>

            <el-tab-pane label="对话" name="feedback">
              <section class="agent-chat">
                <div ref="chatBodyRef" class="chat-thread">
                  <article
                    v-for="message in chatMessages"
                    :key="message.id"
                    :class="['chat-message', message.role === 'user' ? 'user' : 'agent', message.kind]"
                  >
                    <div v-if="message.kind === 'event'" class="chat-stream-line">
                      <div>
                        <details v-if="hasEventDetails(message.event, message.run)" class="stream-disclosure">
                          <summary class="stream-summary">
                            <div class="stream-head">
                              <div class="stream-title">
                                <strong>{{ eventLabel(message.event?.event_type) }}</strong>
                                <span class="stream-caret" aria-hidden="true" />
                              </div>
                              <span>{{ message.created_at || '-' }}</span>
                            </div>
                            <p>{{ message.text }}</p>
                            <small v-if="streamTagText(message)">{{ streamTagText(message) }}</small>
                          </summary>
                          <div class="stream-detail">
                            <dl v-if="eventDetailRows(message.event, message.run).length" class="detail-kv">
                              <template v-for="row in eventDetailRows(message.event, message.run)" :key="row.label">
                                <dt>{{ row.label }}</dt>
                                <dd>{{ row.value }}</dd>
                              </template>
                            </dl>
                            <div v-if="eventNarrative(message.event, message.run)" class="agent-narrative">
                              <p v-if="eventNarrative(message.event, message.run)?.summary" class="agent-summary">
                                {{ eventNarrative(message.event, message.run)?.summary }}
                              </p>
                              <div v-if="eventNarrative(message.event, message.run)?.steps?.length" class="agent-flow">
                                <div v-for="item in eventNarrative(message.event, message.run)?.steps" :key="`stream-step-${message.id}-${item.step}-${item.title}`" class="agent-flow-item">
                                  <span class="agent-flow-index">{{ item.step || '·' }}</span>
                                  <div>
                                    <div class="agent-flow-head">
                                      <strong>{{ item.title }}</strong>
                                      <el-tag v-if="item.phase" size="small" effect="plain">{{ item.phase }}</el-tag>
                                    </div>
                                    <p v-if="item.body">{{ item.body }}</p>
                                    <dl v-if="item.rows?.length" class="agent-mini-kv">
                                      <template v-for="row in item.rows" :key="row.label">
                                        <dt>{{ row.label }}</dt>
                                        <dd>{{ row.value }}</dd>
                                      </template>
                                    </dl>
                                  </div>
                                </div>
                              </div>
                              <div v-if="eventNarrative(message.event, message.run)?.iterations?.length" class="agent-card-grid">
                                <article v-for="item in eventNarrative(message.event, message.run)?.iterations" :key="`stream-iteration-${message.id}-${item.round}`" class="agent-mini-card">
                                  <strong>第 {{ item.round }} 轮</strong>
                                  <span>{{ item.score_before }} → {{ item.score_after }} 分</span>
                                  <p>{{ item.summary || item.focus }}</p>
                                  <small v-if="item.agent_explanation">{{ item.agent_explanation }}</small>
                                </article>
                              </div>
                              <div v-if="eventNarrative(message.event, message.run)?.ideas?.length" class="agent-card-grid">
                                <article v-for="idea in eventNarrative(message.event, message.run)?.ideas" :key="`stream-idea-${message.id}-${idea.title}`" class="agent-mini-card">
                                  <strong>{{ idea.title || '方案' }}</strong>
                                  <span v-if="idea.score !== undefined && idea.score !== null">{{ idea.score }} 分</span>
                                  <p>{{ idea.core_concept || idea.story_outline }}</p>
                                  <small v-if="idea.spatial_mechanism">{{ idea.spatial_mechanism }}</small>
                                </article>
                              </div>
                              <div v-if="eventNarrative(message.event, message.run)?.scores?.length" class="score-matrix">
                                <div v-for="score in eventNarrative(message.event, message.run)?.scores" :key="`stream-score-${message.id}-${score.idea_index}`" class="score-row">
                                  <strong>方案 {{ Number(score.idea_index || 0) + 1 }}</strong>
                                  <span>{{ score.total_score }} 分</span>
                                  <small>目标匹配 {{ score.goal_fit }} · 视觉冲击 {{ score.visual_impact }} · 裸眼3D {{ score.naked_eye_3d_fit }}</small>
                                </div>
                              </div>
                            </div>
                            <pre v-else-if="eventDetailJson(message.event, message.run)" class="detail-json">{{ eventDetailJson(message.event, message.run) }}</pre>
                          </div>
                        </details>
                        <template v-else>
                          <div class="stream-head">
                            <div class="stream-title">
                              <strong>{{ eventLabel(message.event?.event_type) }}</strong>
                            </div>
                            <span>{{ message.created_at || '-' }}</span>
                          </div>
                          <p>{{ message.text }}</p>
                          <small v-if="streamTagText(message)">{{ streamTagText(message) }}</small>
                        </template>
                      </div>
                    </div>

                    <div v-else class="chat-bubble">
                      <div class="chat-meta">
                        <strong>{{ message.role === 'user' ? '你' : 'Agent' }}</strong>
                        <span>{{ message.created_at || '-' }}</span>
                      </div>
                      <p>{{ message.text }}</p>
                      <div v-if="message.tags?.length" class="chat-tags">
                        <el-tag v-for="tag in message.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                      </div>
                      <div v-if="message.run" class="chat-run">
                        <div class="chat-run-head">
                          <el-tag size="small" effect="plain">{{ message.run.provider === 'direct_ai' ? 'Direct' : 'Hermes' }}</el-tag>
                          <el-tag size="small" :type="runStatusType(message.run.status)">{{ statusLabel(message.run.status) }}</el-tag>
                        </div>
                        <div v-if="message.ideas?.length" class="chat-result-ideas">
                          <article v-for="idea in message.ideas" :key="idea.id || idea.title" class="chat-result-idea" @click="openIdeaDetail(idea)">
                            <div class="chat-result-head">
                              <strong>{{ idea.title || '方案' }}</strong>
                              <el-tag v-if="idea.score !== undefined && idea.score !== null" size="small" type="success">{{ idea.score }} 分</el-tag>
                            </div>
                            <p>{{ ideaSummary(idea) }}</p>
                            <small v-if="idea.spatial_mechanism">{{ idea.spatial_mechanism }}</small>
                            <div class="chat-result-actions">
                              <el-button size="small" plain @click.stop="openFeedbackForIdea(idea)">围绕它聊</el-button>
                              <el-button size="small" @click.stop="runIdea(idea.id, 'evaluate')">打分</el-button>
                              <el-button size="small" type="primary" plain @click.stop="runIdea(idea.id, 'iterate')">直接迭代</el-button>
                            </div>
                          </article>
                        </div>
                        <div v-if="message.events?.length" class="chat-event-list">
                          <small v-for="event in message.events" :key="event.id || `${message.id}-${event.event_type}`">
                            {{ eventLabel(event.event_type) }}：{{ event.message || event.event_type }}
                          </small>
                        </div>
                      </div>
                    </div>
                  </article>
                  <el-empty v-if="!chatMessages.length" description="还没有对话，可以直接在下方启动 Agent 或发送消息" :image-size="90" />
                </div>

                <div class="chat-composer">
                  <div v-if="selectedFeedbackIdea" class="composer-context">
                    <span>当前方案：{{ selectedFeedbackIdea.title || selectedFeedbackIdea.id }}</span>
                    <el-button text size="small" @click="clearFeedbackIdea">取消关联</el-button>
                  </div>
                  <el-input
                    ref="chatInputRef"
                    v-model="feedbackForm.feedback_text"
                    type="textarea"
                    :rows="3"
                    resize="none"
                    :placeholder="composerPlaceholder"
                    @keydown.meta.enter.prevent="submitFeedback"
                    @keydown.ctrl.enter.prevent="submitFeedback"
                  />
                  <div class="composer-actions">
                    <div class="composer-controls">
                      <el-select v-model="feedbackForm.target_idea_id" clearable placeholder="当前方案" size="small">
                        <el-option v-for="idea in activeSession.ideas" :key="idea.id" :label="idea.title || idea.id" :value="idea.id" />
                      </el-select>
                      <el-select v-model="feedbackForm.priority" placeholder="优先级" size="small">
                        <el-option label="普通" value="normal" />
                        <el-option label="高" value="high" />
                        <el-option label="低" value="low" />
                      </el-select>
                    </div>
                    <el-button type="primary" @click="submitFeedback" :loading="feedbackSaving || running" :disabled="Boolean(activeRun)">
                      {{ composerActionLabel }}
                    </el-button>
                  </div>
                </div>
              </section>
            </el-tab-pane>

          </el-tabs>
        </template>
      </main>
    </div>

    <el-dialog v-model="agentConfigVisible" title="Agent 配置" width="900px" class="creative-dialog agent-config-dialog">
      <el-tabs v-model="agentConfigTab">
        <el-tab-pane :label="`Memory ${creativeMemory.length}`" name="memory">
          <div class="config-note">
            待审核 Memory 是 Agent 沉淀出的候选经验；只有启用后的 Memory 会进入后续自动创意。Memory 内容和标签请使用中文。
          </div>
          <div class="section-actions">
            <el-button :icon="Refresh" @click="loadMemory" :loading="memoryLoading">刷新 Memory</el-button>
          </div>
          <div v-loading="memoryLoading" class="memory-grid">
            <article v-for="item in creativeMemory" :key="item.id" class="memory-card">
              <div class="memory-card-head">
                <strong>{{ memoryKindLabel(item.kind) }}</strong>
                <div class="run-meta">
                  <el-tag size="small" effect="plain">{{ item.scope === 'team' ? '团队' : '个人' }}</el-tag>
                  <el-tag size="small" :type="memoryStatusType(item.status)">{{ memoryStatusLabel(item.status) }}</el-tag>
                </div>
              </div>
              <p>{{ item.content }}</p>
              <div v-if="item.tags?.length" class="memory-tags">
                <el-tag v-for="tag in item.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
              </div>
              <small>{{ item.updated_at || item.created_at || '-' }}</small>
              <div class="card-actions">
                <el-button v-if="item.status !== 'approved'" size="small" type="success" plain @click="setMemoryStatus(item, 'approved')">启用</el-button>
                <el-button v-if="item.status !== 'archived'" size="small" plain @click="setMemoryStatus(item, 'archived')">归档</el-button>
                <el-button size="small" plain @click="openMemoryEditor(item)">编辑</el-button>
              </div>
            </article>
          </div>
          <el-empty v-if="!memoryLoading && !creativeMemory.length" description="还没有沉淀 Memory" :image-size="90" />
        </el-tab-pane>

        <el-tab-pane :label="`Skills ${skillItems.length}`" name="skills">
          <div class="config-note">
            Skill 是创意 Agent 的行为说明。当前 Direct 与 Hermes 后端 tool 流程都会读取这些 Skill 内容。新增或编辑 Skill 时请使用中文。
          </div>
          <div class="section-actions">
            <el-button :icon="Refresh" @click="loadSkills" :loading="skillLoading">刷新 Skills</el-button>
          </div>
          <div class="skill-summary">
            <div>
              <strong>{{ hermesStatus.creative_profile || 'creative-orchestrator' }}</strong>
              <span>Profile</span>
            </div>
            <div>
              <strong>{{ hermesStatus.skills_dir || '-' }}</strong>
              <span>Skills 目录</span>
            </div>
            <div>
              <strong>{{ (hermesStatus.required_toolsets || []).join(', ') || '-' }}</strong>
              <span>Toolsets</span>
            </div>
          </div>
          <div v-loading="skillLoading" class="skill-grid">
            <article v-for="skill in skillItems" :key="skill.name" class="skill-card">
              <div class="skill-card-head">
                <strong>{{ skill.name }}</strong>
                <el-tag size="small" effect="plain">{{ skill.source }}</el-tag>
              </div>
              <p>{{ skill.description }}</p>
              <div class="card-actions">
                <el-button size="small" plain @click="openSkillEditor(skill)">编辑</el-button>
              </div>
            </article>
          </div>
          <details v-if="hermesStatus.capabilities && Object.keys(hermesStatus.capabilities).length" class="detail-disclosure status-disclosure">
            <summary>Hermes capabilities</summary>
            <pre class="detail-json">{{ formatJson(hermesStatus.capabilities) }}</pre>
          </details>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <el-dialog v-model="createDialogVisible" title="新建创意会话" width="520px" class="creative-dialog">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="createForm.title" placeholder="创意会话标题" />
        </el-form-item>
        <el-form-item label="关联订单（可选）">
          <el-select
            v-model="createForm.source_order_id"
            placeholder="选择订单后自动生成 brief"
            filterable
            clearable
            :loading="ordersLoading"
            style="width: 100%"
          >
            <el-option
              v-for="order in orderOptions"
              :key="order.id"
              :label="orderOptionLabel(order)"
              :value="order.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="初始 brief">
          <el-input v-model="createForm.objective" type="textarea" :rows="4" placeholder="项目目标、客户背景、投放场景" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreateSession" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ideaDialogVisible" title="添加人工方案" width="640px" class="creative-dialog">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="ideaForm.title" />
        </el-form-item>
        <el-form-item label="创意概念 · 15%">
          <el-input v-model="ideaForm.core_concept" type="textarea" :rows="2" placeholder="约45字" />
        </el-form-item>
        <el-form-item label="灵感来源 · 15%">
          <el-input v-model="ideaForm.spatial_mechanism" type="textarea" :rows="2" placeholder="约45字" />
        </el-form-item>
        <el-form-item label="方案脚本 · 35%">
          <el-input v-model="ideaForm.story_outline" type="textarea" :rows="5" placeholder="约105字，按连续时间段写画面，可用0.5秒或0.1秒精度" />
        </el-form-item>
        <el-form-item label="风格参考 · 15%">
          <el-input v-model="ideaForm.production_notes" type="textarea" :rows="2" placeholder="约45字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ideaDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createIdea" :loading="ideaSaving">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ideaDetailVisible" :title="ideaDetail.title || '方案详情'" width="760px" class="creative-dialog idea-detail-dialog">
      <div class="idea-detail">
        <div class="idea-detail-head">
          <el-tag v-if="ideaDetail.score !== undefined && ideaDetail.score !== null" type="success">{{ ideaDetail.score }} 分</el-tag>
          <el-tag v-for="tag in ideaDetail.tags || []" :key="tag" effect="plain">{{ tag }}</el-tag>
        </div>
        <dl>
          <dt>创意概念</dt>
          <dd>{{ ideaDetail.core_concept || '-' }}</dd>
          <dt>灵感来源</dt>
          <dd>{{ ideaDetail.spatial_mechanism || '-' }}</dd>
          <dt>方案脚本</dt>
          <dd>{{ ideaDetail.story_outline || '-' }}</dd>
          <dt>风格参考</dt>
          <dd>{{ ideaDetail.production_notes || '-' }}</dd>
          <dt>风险与规避</dt>
          <dd>{{ ideaDetail.risk_notes || '-' }}</dd>
        </dl>
      </div>
      <template #footer>
        <el-button @click="ideaDetailVisible = false">关闭</el-button>
        <el-button v-if="ideaDetail.id" plain @click="chatAboutIdeaFromDialog">围绕它聊</el-button>
        <el-button v-if="ideaDetail.id" type="primary" plain @click="runIdea(ideaDetail.id, 'iterate'); ideaDetailVisible = false">迭代</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="memoryDialogVisible" title="编辑 Memory" width="640px" class="creative-dialog">
      <el-form label-position="top">
        <div class="inline-row">
          <el-form-item label="类型">
            <el-input v-model="memoryForm.kind" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="memoryForm.status">
              <el-option label="已启用" value="approved" />
              <el-option label="待审核" value="proposed" />
              <el-option label="已归档" value="archived" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="内容">
          <el-input v-model="memoryForm.content" type="textarea" :rows="8" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="memoryForm.tagsText" placeholder="用逗号分隔，例如 裸眼3D, 分镜, 品牌资产" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveMemoryEdit" :loading="memorySaving">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="skillDialogVisible" :title="`编辑 Skill：${skillForm.name || ''}`" width="760px" class="creative-dialog skill-edit-dialog">
      <el-form label-position="top">
        <el-form-item label="SKILL.md">
          <el-input v-model="skillForm.content" type="textarea" :rows="22" spellcheck="false" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="skillDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSkillEdit" :loading="skillSaving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Document, Plus, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { orderApi } from '@/utils/api'

const sessions = ref<any[]>([])
const activeSession = ref<any>(null)
const runEvents = reactive<Record<string, any[]>>({})
const creativeMemory = ref<any[]>([])
const skillCatalog = ref<any[]>([])
const keyword = ref('')
const activeTab = ref('feedback')
const orderId = ref('')
const orderOptions = ref<any[]>([])
const providerDefaultVersion = 'hermes-v1'
const agentProvider = ref(localStorage.getItem('creative-agent-provider') || 'hermes')

const sessionsLoading = ref(false)
const ordersLoading = ref(false)
const creating = ref(false)
const saving = ref(false)
const running = ref(false)
const briefLoading = ref(false)
const feedbackSaving = ref(false)
const ideaSaving = ref(false)
const memoryLoading = ref(false)
const memorySaving = ref(false)
const skillLoading = ref(false)
const skillSaving = ref(false)
const deletingSessionId = ref('')

const createDialogVisible = ref(false)
const ideaDialogVisible = ref(false)
const ideaDetailVisible = ref(false)
const agentConfigVisible = ref(false)
const agentConfigTab = ref('memory')
const memoryDialogVisible = ref(false)
const skillDialogVisible = ref(false)
const chatBodyRef = ref<HTMLElement | null>(null)
const chatInputRef = ref<any>(null)
const pendingChatMessages = ref<any[]>([])
const selectedIdeaContext = ref<any | null>(null)
let runPollTimer: ReturnType<typeof window.setInterval> | null = null

const hermesStatus = reactive<any>({
  enabled: false,
  healthy: false,
})

const createForm = reactive({
  title: '',
  source_order_id: '',
  objective: '',
})

const briefForm = reactive<Record<string, string>>({
  project_name: '',
  brand: '',
  objective: '',
  resource_background: '',
  media_positioning: '',
  theme_concept: '',
  audience: '',
  viewing_path: '',
  media_location: '',
  screen_resource_summary: '',
  art_direction: '',
  constraints: '',
  content_review: '',
  special_notes: '',
})

const feedbackForm = reactive({
  target_idea_id: '',
  feedback_text: '',
  priority: 'normal',
})

const ideaForm = reactive({
  title: '',
  core_concept: '',
  spatial_mechanism: '',
  story_outline: '',
  production_notes: '',
  risk_notes: '',
  tags: [] as string[],
})

const ideaDetail = reactive<any>({
  id: '',
  title: '',
  score: null,
  core_concept: '',
  spatial_mechanism: '',
  story_outline: '',
  production_notes: '',
  risk_notes: '',
  tags: [],
})

const memoryForm = reactive({
  id: '',
  kind: '',
  status: 'approved',
  content: '',
  tagsText: '',
})

const skillForm = reactive({
  name: '',
  content: '',
})

const currentBrief = computed(() => ({
  ...sanitizeBrief(activeSession.value?.brief || {}),
  ...Object.fromEntries(Object.entries(briefForm).filter(([, value]) => String(value || '').trim())),
}))

const activeRun = computed(() => {
  return activeSession.value?.runs?.find((run: any) => ['queued', 'running', 'stopping'].includes(run.status))
})

const findIdea = (ideaId: string) => {
  if (!ideaId) return null
  const ideas = Array.isArray(activeSession.value?.ideas) ? activeSession.value.ideas : []
  return ideas.find((idea: any) => idea.id === ideaId) || null
}

const selectedFeedbackIdea = computed(() => {
  const ideaId = feedbackForm.target_idea_id
  return findIdea(ideaId) || (selectedIdeaContext.value?.id === ideaId ? selectedIdeaContext.value : null)
})

const composerPlaceholder = computed(() => {
  const idea = selectedFeedbackIdea.value
  if (idea) {
    return `正在围绕「${idea.title || '当前方案'}」沟通：告诉 Agent 想保留、删掉、加强或改成什么方向...`
  }
  return '像聊天一样告诉 Agent：保留什么、删掉什么、换什么风格、继续探索哪个方向...'
})

const composerActionLabel = computed(() => {
  if (feedbackForm.feedback_text.trim()) return '发送给 Agent'
  return activeSession.value?.runs?.length ? '再生成一轮创意' : '启动 Agent'
})

const chatMessages = computed(() => {
  if (!activeSession.value) return []
  const feedbacks = Array.isArray(activeSession.value.designer_feedbacks) ? activeSession.value.designer_feedbacks : []
  const runs = Array.isArray(activeSession.value.runs) ? activeSession.value.runs : []
  const messages = [
    ...pendingChatMessages.value,
    ...runs.flatMap((run: any) => {
      const ideas = runIdeaItems(run).map(summarizeIdea)
      const events = runEventItems(run)
      const eventMessages = events.map((event: any) => ({
        id: `event-${event.id || `${run.id}-${event.event_type}-${event.created_at}`}`,
        role: 'agent',
        kind: 'event',
        created_at: event.created_at || run.created_at,
        timestamp: messageTimestamp(event.created_at || run.created_at),
        text: event.message || event.event_type,
        tags: [
          eventLabel(event.event_type),
          eventBrief(event),
        ].filter(Boolean),
        event,
        run,
      }))
      const resultMessage = {
        id: `run-result-${run.id}`,
        role: 'agent',
        kind: 'result',
        created_at: run.finished_at || run.updated_at || run.created_at,
        timestamp: messageTimestamp(run.finished_at || run.updated_at || run.created_at) + 1,
        text: chatRunSummary(run, ideas),
        tags: [
          runTypeLabel(run.run_type),
          statusLabel(run.status),
        ].filter(Boolean),
        run,
        ideas,
        events: [],
      }
      return run.status === 'completed' || ideas.length || run.status === 'failed'
        ? [...eventMessages, resultMessage]
        : eventMessages
    }),
    ...feedbacks.map((item: any) => ({
      id: `feedback-${item.id}`,
      role: 'user',
      kind: 'feedback',
      created_at: item.created_at || item.updated_at,
      timestamp: messageTimestamp(item.created_at || item.updated_at),
      text: item.feedback_text || '',
      tags: [
        priorityLabel(item.priority),
        feedbackIdeaTitle(item.target_idea_id),
      ].filter(Boolean),
    })),
  ]
  return messages.sort((a: any, b: any) => a.timestamp - b.timestamp)
})

const skillItems = computed(() => {
  if (skillCatalog.value.length) {
    return skillCatalog.value.map((item: any) => ({
      ...item,
      source: item.source || 'local',
      description: item.description || 'Skill 文件',
    }))
  }
  const capabilitySkills = extractCapabilitySkills(hermesStatus.capabilities)
  if (capabilitySkills.length) return capabilitySkills
  return [
    {
      name: 'creative-orchestrator',
      source: 'local',
      description: '编排裸眼3D商业创意生成、评分、迭代和输出结构。',
    },
    {
      name: 'creative-concept-generator',
      source: 'local',
      description: '根据 brief 生成差异化商业创意概念，明确视觉钩子、品牌/场景连接和核心3D机制。',
    },
    {
      name: 'naked-eye-3d-scriptwriter',
      source: 'local',
      description: '把创意概念写成具体到秒的裸眼3D分镜脚本，明确空间层次、破框/遮挡/透视和品牌落点。',
    },
    {
      name: 'creative-rubric-evaluator',
      source: 'local',
      description: '定义目标匹配度、视觉冲击力、裸眼3D适配度等评分口径。',
    },
    {
      name: 'creative-iteration-loop',
      source: 'local',
      description: '根据评分和设计师方向组织下一轮精修。',
    },
    {
      name: 'china-outdoor-led-compliance',
      source: 'local',
      description: '补充中国户外LED内容合规、投放风险和审核注意点。',
    },
  ]
})

const agentStatusLabel = computed(() => {
  if (!hermesStatus.enabled) return '创意 Agent 未启用'
  if (agentProvider.value === 'direct_ai') return `Direct 已选择 · ${hermesStatus.model || '后台模型'}`
  return hermesStatus.mode === 'direct_ai' ? 'Direct 已启用' : `Hermes 已选择 · ${hermesStatus.model || '后台模型'}`
})

const isProviderAvailable = (provider: string) => {
  const providers = hermesStatus.providers || []
  const item = providers.find((entry: any) => entry.value === provider)
  if (!item) return provider === 'hermes' ? Boolean(hermesStatus.enabled && hermesStatus.healthy) : Boolean(hermesStatus.enabled)
  return Boolean(item.available)
}

const defaultProviderFromStatus = () => {
  const providers = hermesStatus.providers || []
  const item = providers.find((entry: any) => entry.default && entry.available)
  return item?.value || (isProviderAvailable('hermes') ? 'hermes' : 'direct_ai')
}

const persistAgentProvider = () => {
  if (!isProviderAvailable(agentProvider.value)) {
    agentProvider.value = defaultProviderFromStatus()
  }
  localStorage.setItem('creative-agent-provider', agentProvider.value)
  localStorage.setItem('creative-agent-provider-default-version', providerDefaultVersion)
}

const loadHermesStatus = async () => {
  try {
    const data: any = await request.get('/admin/creative-agent/hermes/status', { silent: true })
    Object.assign(hermesStatus, data || {})
    if (localStorage.getItem('creative-agent-provider-default-version') !== providerDefaultVersion) {
      agentProvider.value = defaultProviderFromStatus()
      persistAgentProvider()
      return
    }
    if (!isProviderAvailable(agentProvider.value)) {
      agentProvider.value = defaultProviderFromStatus()
      persistAgentProvider()
    }
  } catch (error) {
    Object.assign(hermesStatus, { enabled: false, healthy: false })
  }
}

const loadMemory = async () => {
  memoryLoading.value = true
  try {
    const data: any = await request.get('/admin/creative-agent/memory', { silent: true })
    creativeMemory.value = Array.isArray(data) ? data : []
  } finally {
    memoryLoading.value = false
  }
}

const loadSkills = async () => {
  skillLoading.value = true
  try {
    const data: any = await request.get('/admin/creative-agent/skills', { silent: true })
    skillCatalog.value = Array.isArray(data) ? data : []
  } catch {
    skillCatalog.value = []
  } finally {
    skillLoading.value = false
  }
}

const loadSessions = async () => {
  sessionsLoading.value = true
  try {
    const data: any = await request.get('/admin/creative-agent/sessions', {
      params: { page: 1, pageSize: 50, keyword: keyword.value || undefined },
    })
    sessions.value = data?.data || []
    if (!activeSession.value && sessions.value[0]) {
      await openSession(sessions.value[0].id)
    }
  } finally {
    sessionsLoading.value = false
  }
}

const loadAll = async () => {
  await Promise.all([loadHermesStatus(), loadSessions(), loadOrderOptions(), loadMemory(), loadSkills()])
  if (activeSession.value?.id) {
    await openSession(activeSession.value.id)
  }
}

const openAgentConfig = async () => {
  agentConfigVisible.value = true
  await Promise.all([loadHermesStatus(), loadMemory(), loadSkills()])
}

const loadOrderOptions = async () => {
  ordersLoading.value = true
  try {
    const orders = await orderApi.getOrders()
    orderOptions.value = (orders || []).filter((order: any) => order.status !== 'cancelled')
  } finally {
    ordersLoading.value = false
  }
}

const openSession = async (id: string) => {
  const data: any = await request.get(`/admin/creative-agent/sessions/${id}`)
  activeSession.value = data
  fillBriefForm(data.brief || {})
  orderId.value = data.source_order_id || ''
  await loadRunEventsForSession(data)
  syncRunPolling()
}

const createSession = () => {
  createDialogVisible.value = true
}

const confirmCreateSession = async () => {
  creating.value = true
  try {
    const payload: any = {
      title: createForm.title || undefined,
      visibility: 'team',
      source_type: createForm.source_order_id ? 'order' : 'manual',
      source_order_id: createForm.source_order_id || undefined,
      brief: createForm.objective ? { objective: createForm.objective } : {},
    }
    const data: any = await request.post('/admin/creative-agent/sessions', payload)
    createDialogVisible.value = false
    createForm.title = ''
    createForm.source_order_id = ''
    createForm.objective = ''
    await loadSessions()
    await openSession(data.id)
    ElMessage.success('创意会话已创建')
  } finally {
    creating.value = false
  }
}

const confirmDeleteSession = async (session: any) => {
  if (!session?.id) return
  try {
    await ElMessageBox.confirm(
      `确认删除“${session.title || '创意会话'}”？删除后该会话下的方案、运行记录和反馈都会删除，但不会影响订单。`,
      '删除创意会话',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return
  }

  deletingSessionId.value = session.id
  try {
    await request.delete(`/admin/creative-agent/sessions/${session.id}`)
    if (activeSession.value?.id === session.id) {
      activeSession.value = null
      activeTab.value = 'feedback'
    }
    await loadSessions()
    if (!activeSession.value && sessions.value[0]) {
      await openSession(sessions.value[0].id)
    }
    ElMessage.success('创意会话已删除')
  } finally {
    deletingSessionId.value = ''
  }
}

const loadOrderBrief = async () => {
  if (!orderId.value.trim()) {
    ElMessage.warning('请先选择订单')
    return
  }
  briefLoading.value = true
  try {
    const data: any = await request.get(`/admin/creative-agent/orders/${orderId.value.trim()}/brief`)
    const sanitizedBrief = sanitizeBrief(data || {})
    if (activeSession.value) {
      activeSession.value.brief = sanitizedBrief
    }
    fillBriefForm(sanitizedBrief)
    if (activeSession.value?.id) {
      await saveSession()
    }
    ElMessage.success('已读取订单 brief')
  } finally {
    briefLoading.value = false
  }
}

const handleOrderSelect = async (value: string) => {
  if (value) {
    await loadOrderBrief()
  }
}

const saveSession = async () => {
  if (!activeSession.value?.id) return
  saving.value = true
  try {
    const data: any = await request.patch(`/admin/creative-agent/sessions/${activeSession.value.id}`, {
      title: briefForm.project_name || activeSession.value.title,
      brief: currentBrief.value,
      designer_direction: activeSession.value.designer_direction || '',
    })
    activeSession.value = data
    fillBriefForm(data.brief || {})
    await loadSessions()
    ElMessage.success('Brief 已保存')
  } finally {
    saving.value = false
  }
}

const startAutoRun = async () => {
  if (!activeSession.value?.id) return
  if (!ensureNoActiveRun()) return
  running.value = true
  try {
    await saveSession()
    await request.post(`/admin/creative-agent/sessions/${activeSession.value.id}/auto-run`, {
      max_rounds: 4,
      target_score: 85,
      idea_count: 3,
      provider: agentProvider.value,
      strategy: 'balanced',
      use_parallel_evaluators: true,
      use_team_memory: true,
      use_personal_memory: true,
      save_memory_candidates: true,
      wait_for_completion: false,
      designer_direction: activeSession.value.designer_direction || '',
    })
    await openSession(activeSession.value.id)
    activeTab.value = 'feedback'
    syncRunPolling()
    scrollChatToBottom()
    ElMessage.success(`${agentProviderLabel()} 创意 Agent 已启动`)
  } finally {
    running.value = false
  }
}

const createIdea = async () => {
  if (!activeSession.value?.id || !ideaForm.title.trim()) {
    ElMessage.warning('请填写方案标题')
    return
  }
  ideaSaving.value = true
  try {
    await request.post(`/admin/creative-agent/sessions/${activeSession.value.id}/ideas`, ideaForm)
    ideaDialogVisible.value = false
    Object.assign(ideaForm, {
      title: '',
      core_concept: '',
      spatial_mechanism: '',
      story_outline: '',
      production_notes: '',
      risk_notes: '',
      tags: [],
    })
    await openSession(activeSession.value.id)
    ElMessage.success('方案已保存')
  } finally {
    ideaSaving.value = false
  }
}

const openMemoryEditor = (item: any) => {
  Object.assign(memoryForm, {
    id: item.id || '',
    kind: item.kind || '',
    status: item.status || 'approved',
    content: item.content || '',
    tagsText: (item.tags || []).join(', '),
  })
  memoryDialogVisible.value = true
}

const saveMemoryEdit = async () => {
  if (!memoryForm.id || !memoryForm.content.trim()) {
    ElMessage.warning('Memory 内容不能为空')
    return
  }
  memorySaving.value = true
  try {
    await request.patch(`/admin/creative-agent/memory/${memoryForm.id}`, {
      kind: memoryForm.kind || 'principle',
      status: memoryForm.status,
      content: memoryForm.content,
      tags: splitTags(memoryForm.tagsText),
    })
    memoryDialogVisible.value = false
    await loadMemory()
    ElMessage.success('Memory 已更新')
  } finally {
    memorySaving.value = false
  }
}

const setMemoryStatus = async (item: any, status: 'approved' | 'archived') => {
  if (!item?.id || item.status === status) return
  memorySaving.value = true
  try {
    await request.patch(`/admin/creative-agent/memory/${item.id}`, { status })
    await loadMemory()
    ElMessage.success(status === 'approved' ? 'Memory 已启用' : 'Memory 已归档')
  } finally {
    memorySaving.value = false
  }
}

const openSkillEditor = async (skill: any) => {
  if (!skill?.name) return
  skillSaving.value = false
  try {
    const data: any = await request.get(`/admin/creative-agent/skills/${skill.name}`)
    Object.assign(skillForm, {
      name: data.name || skill.name,
      content: data.content || '',
    })
    skillDialogVisible.value = true
  } catch {
    ElMessage.error('读取 Skill 失败')
  }
}

const saveSkillEdit = async () => {
  if (!skillForm.name || !skillForm.content.trim()) {
    ElMessage.warning('Skill 内容不能为空')
    return
  }
  skillSaving.value = true
  try {
    await request.patch(`/admin/creative-agent/skills/${skillForm.name}`, {
      content: skillForm.content,
    })
    skillDialogVisible.value = false
    await loadSkills()
    ElMessage.success('Skill 已更新')
  } finally {
    skillSaving.value = false
  }
}

const runIdea = async (ideaId: string, mode: 'evaluate' | 'iterate') => {
  if (!ensureNoActiveRun()) return
  await request.post(`/admin/creative-agent/ideas/${ideaId}/${mode}`, {
    max_rounds: mode === 'iterate' ? 2 : 1,
    target_score: 85,
    provider: agentProvider.value,
    wait_for_completion: false,
    designer_direction: activeSession.value?.designer_direction || '',
  })
  await openSession(activeSession.value.id)
  activeTab.value = 'feedback'
  syncRunPolling()
  scrollChatToBottom()
  ElMessage.success(mode === 'evaluate' ? '已启动打分' : '已启动迭代')
}

const openFeedbackForIdea = async (idea: any) => {
  if (!idea?.id) {
    feedbackForm.target_idea_id = ''
    selectedIdeaContext.value = null
    ElMessage.warning('这个方案还没有可关联的会话记录')
    return
  }
  feedbackForm.target_idea_id = idea.id
  selectedIdeaContext.value = summarizeIdea(findIdea(idea.id) || idea)
  activeTab.value = 'feedback'
  pendingChatMessages.value = pendingChatMessages.value.filter((item: any) => !String(item.id).startsWith('idea-context-'))
  pendingChatMessages.value.push({
    id: `idea-context-${idea.id}-${Date.now()}`,
    role: 'agent',
    kind: 'event',
    created_at: new Date().toISOString(),
    timestamp: Date.now(),
    text: `已切换到「${idea.title || '这个方案'}」。接下来发送的消息会围绕它继续沟通。`,
    tags: ['方案上下文'],
    event: { event_type: 'ui.idea_selected' },
  })
  await scrollChatToBottom()
  await focusChatInput()
}

const chatAboutIdeaFromDialog = async () => {
  const idea = { ...ideaDetail }
  ideaDetailVisible.value = false
  await nextTick()
  await openFeedbackForIdea(idea)
}

const clearFeedbackIdea = () => {
  feedbackForm.target_idea_id = ''
  selectedIdeaContext.value = null
  pendingChatMessages.value = pendingChatMessages.value.filter((item: any) => !String(item.id).startsWith('idea-context-'))
}

const openIdeaDetail = (idea: any) => {
  Object.assign(ideaDetail, {
    id: idea?.id || '',
    title: idea?.title || '方案',
    score: idea?.score ?? null,
    core_concept: idea?.core_concept || '',
    spatial_mechanism: idea?.spatial_mechanism || '',
    story_outline: idea?.story_outline || '',
    production_notes: idea?.production_notes || '',
    risk_notes: idea?.risk_notes || '',
    tags: Array.isArray(idea?.tags) ? idea.tags : [],
  })
  ideaDetailVisible.value = true
}

const ideaSummary = (idea: any) => {
  const text = idea?.core_concept || idea?.story_outline || ''
  if (!text) return '-'
  return text.length > 96 ? `${text.slice(0, 96).trim()}...` : text
}

const submitFeedback = async () => {
  if (!activeSession.value?.id) return
  if (!feedbackForm.feedback_text.trim()) {
    await startAutoRun()
    return
  }
  if (feedbackForm.target_idea_id && !findIdea(feedbackForm.target_idea_id)) {
    const contextMatches = selectedIdeaContext.value?.id === feedbackForm.target_idea_id
    if (!contextMatches) {
      feedbackForm.target_idea_id = ''
      selectedIdeaContext.value = null
    }
  }
  if (!ensureNoActiveRun()) return
  const sessionId = activeSession.value.id
  const submittedText = feedbackForm.feedback_text.trim()
  const submittedAt = new Date().toISOString()
  const pendingId = `pending-${Date.now()}`
  pendingChatMessages.value.push(
    {
      id: `${pendingId}-user`,
      role: 'user',
      kind: 'feedback',
      created_at: submittedAt,
      timestamp: Date.now(),
      text: submittedText,
      tags: [
        priorityLabel(feedbackForm.priority),
        feedbackIdeaTitle(feedbackForm.target_idea_id),
      ].filter(Boolean),
    },
    {
      id: `${pendingId}-agent`,
      role: 'agent',
      kind: 'event',
      created_at: submittedAt,
      timestamp: Date.now() + 1,
      text: 'Agent 已收到反馈，正在创建下一轮迭代。',
      tags: ['准备中'],
      event: { event_type: 'backend.queued' },
    },
  )
  scrollChatToBottom()
  feedbackSaving.value = true
  try {
    await request.post(`/admin/creative-agent/sessions/${sessionId}/continue-run`, {
      ...feedbackForm,
      target_idea_id: feedbackForm.target_idea_id || undefined,
      max_rounds: 2,
      target_score: 85,
      provider: agentProvider.value,
      wait_for_completion: false,
    })
    feedbackForm.feedback_text = ''
    feedbackForm.target_idea_id = ''
    selectedIdeaContext.value = null
    feedbackForm.priority = 'normal'
    pendingChatMessages.value = pendingChatMessages.value.filter((item: any) => {
      const id = String(item.id)
      return !id.startsWith(pendingId) && !id.startsWith('idea-context-')
    })
    await openSession(sessionId)
    activeTab.value = 'feedback'
    syncRunPolling()
    if (activeRun.value?.id) {
      await loadRunEvents(activeRun.value.id)
    }
    scrollChatToBottom()
    ElMessage.success('反馈已提交，Agent 将继续迭代')
  } catch (error) {
    pendingChatMessages.value = pendingChatMessages.value.filter((item: any) => item.id !== `${pendingId}-agent`)
    pendingChatMessages.value.push({
      id: `${pendingId}-failed`,
      role: 'agent',
      kind: 'event',
      created_at: new Date().toISOString(),
      timestamp: Date.now() + 2,
      text: '发送失败，请稍后重试。',
      tags: ['失败'],
      event: { event_type: 'backend.failed' },
    })
    throw error
  } finally {
    feedbackSaving.value = false
  }
}

const ensureNoActiveRun = () => {
  if (!activeRun.value) return true
  activeTab.value = 'feedback'
  ElMessage.warning('当前会话还有运行中的 Agent，请先等待完成或点击页面刷新')
  return false
}

const agentProviderLabel = () => agentProvider.value === 'direct_ai' ? 'Direct' : 'Hermes'

const fillBriefForm = (brief: Record<string, any>) => {
  const safeBrief = sanitizeBrief(brief)
  const screenResource = safeBrief.screen_resource || {}
  briefForm.project_name = brief.project_name || brief.campaign_name || ''
  briefForm.brand = safeBrief.brand || safeBrief.brand_or_customer || safeBrief.company_name || safeBrief.customer_name || ''
  briefForm.objective = safeBrief.objective || safeBrief.target_goal || safeBrief.goal || safeBrief.requirement || ''
  briefForm.resource_background = safeBrief.resource_background || safeBrief.background || ''
  briefForm.media_positioning = safeBrief.media_positioning || safeBrief.brand_tone || ''
  briefForm.theme_concept = safeBrief.theme_concept || safeBrief.content || ''
  briefForm.audience = safeBrief.audience_scene || safeBrief.audience || safeBrief.scene || safeBrief.target_audience || safeBrief.target_group || ''
  briefForm.viewing_path = safeBrief.viewing_path || ''
  briefForm.media_location = safeBrief.city_location || safeBrief.media_location || safeBrief.location || safeBrief.city || ''
  briefForm.screen_resource_summary = safeBrief.media_specs || safeBrief.media_size || formatScreenResource(screenResource)
  briefForm.art_direction = safeBrief.art_direction || safeBrief.style || ''
  briefForm.constraints = Array.isArray(safeBrief.constraints) ? safeBrief.constraints.join('\n') : (safeBrief.constraints || safeBrief.prohibited_content || '')
  briefForm.content_review = safeBrief.content_review || ''
  briefForm.special_notes = [safeBrief.special_requirements, safeBrief.remarks].filter(Boolean).join('\n')
}

const sanitizeBrief = (brief: Record<string, any>) => {
  const excludedKeys = new Set([
    'technology',
    'tech_delivery',
    'techDelivery',
    'budget',
    'budget_range',
    'budgetRange',
    'online_time',
    'onlineTime',
    'timeline',
    'deadline',
    'delivery_time',
    'deliveryTime',
  ])
  const { raw_order_data, ...briefFields } = brief || {}
  const rest = Object.fromEntries(Object.entries(briefFields).filter(([key]) => !excludedKeys.has(key)))
  const sanitizedRawOrderData = raw_order_data && typeof raw_order_data === 'object'
    ? Object.fromEntries(Object.entries(raw_order_data).filter(([key]) => !excludedKeys.has(key)))
    : undefined
  return sanitizedRawOrderData ? { ...rest, raw_order_data: sanitizedRawOrderData } : rest
}

const formatScreenResource = (screenResource: Record<string, any>) => {
  if (!screenResource || typeof screenResource !== 'object') return ''
  return [
    screenResource.type ? `类型：${screenResource.type}` : '',
    screenResource.size ? `尺寸：${screenResource.size}` : '',
    screenResource.resolution ? `分辨率：${screenResource.resolution}` : '',
    screenResource.shape ? `形状：${screenResource.shape}` : '',
  ].filter(Boolean).join('；')
}

const orderOptionLabel = (order: any) => {
  const title = order.project_name || order.brand || order.theme_concept || order.orderNumber || order.id
  const customer = order.userName ? ` · ${order.userName}` : ''
  return `${order.orderNumber || order.id} · ${title}${customer}`
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: '草稿',
    queued: '排队中',
    running: '运行中',
    succeeded: '已完成',
    completed: '已完成',
    failed: '失败',
    stopping: '停止中',
    stopped: '已停止',
  }
  return map[status] || status || '-'
}

const runStatusType = (status: string) => {
  if (['succeeded', 'completed'].includes(status)) return 'success'
  if (['failed', 'stopped'].includes(status)) return 'danger'
  if (['running', 'queued', 'stopping'].includes(status)) return 'warning'
  return 'info'
}

const runTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    auto_optimize: '自动创意',
    evaluate: '创意打分',
    iterate: '创意迭代',
    continue: '反馈续写',
    continue_with_feedback: '反馈迭代',
  }
  return map[type] || type || '运行'
}

const priorityLabel = (priority: string) => {
  const map: Record<string, string> = { high: '高优先级', normal: '普通反馈', low: '低优先级' }
  return map[priority] || priority
}

const memoryKindLabel = (kind: string) => {
  const map: Record<string, string> = {
    pattern: '方法论',
    preference: '偏好',
    constraint: '约束',
    case: '案例经验',
    risk: '风险经验',
  }
  return map[kind] || kind || '经验'
}

const memoryStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    proposed: '待审核',
    approved: '已启用',
    archived: '已归档',
  }
  return map[status] || status || '-'
}

const memoryStatusType = (status: string) => {
  if (status === 'approved') return 'success'
  if (status === 'archived') return 'info'
  return 'warning'
}

const splitTags = (value: string) => {
  return String(value || '')
    .split(/[,，\n]/)
    .map(item => item.trim())
    .filter(Boolean)
}

const extractCapabilitySkills = (capabilities: any) => {
  const raw = capabilities?.skills || capabilities?.skill_registry || capabilities?.available_skills || []
  const items = Array.isArray(raw)
    ? raw
    : Object.entries(raw || {}).map(([name, value]: [string, any]) => ({ name, ...(typeof value === 'object' ? value : {}) }))
  return items
    .map((item: any) => ({
      name: item.name || item.id || item.key || '',
      source: item.source || 'hermes',
      description: item.description || item.summary || item.title || 'Hermes 可用 skill',
    }))
    .filter((item: any) => item.name)
}

const loadRunEvents = async (runId: string) => {
  if (!runId) return
  try {
    const data: any = await request.get(`/admin/creative-agent/runs/${runId}/events`, { silent: true })
    runEvents[runId] = Array.isArray(data) ? data : []
  } catch {
    runEvents[runId] = runEvents[runId] || []
  }
}

const loadRunEventsForSession = async (session: any) => {
  const runs = Array.isArray(session?.runs) ? session.runs.slice(0, 5) : []
  await Promise.all(runs.map((run: any) => loadRunEvents(run.id)))
}

const refreshActiveRun = async () => {
  if (!activeSession.value?.id || !activeRun.value?.id) {
    stopRunPolling()
    return
  }
  const runId = activeRun.value.id
  try {
    await request.get(`/admin/creative-agent/runs/${runId}`, {
      params: { refresh: true },
      silent: true,
    })
    await loadRunEvents(runId)
    const data: any = await request.get(`/admin/creative-agent/sessions/${activeSession.value.id}`, { silent: true })
    activeSession.value = data
    fillBriefForm(data.brief || {})
    orderId.value = data.source_order_id || ''
    await loadRunEventsForSession(data)
    if (!data.runs?.some((run: any) => ['queued', 'running', 'stopping'].includes(run.status))) {
      stopRunPolling()
    }
  } catch {
    // Keep polling best-effort; transient refresh failures should not disrupt the page.
  }
}

const syncRunPolling = () => {
  if (!activeRun.value?.id) {
    stopRunPolling()
    return
  }
  if (runPollTimer) return
  runPollTimer = window.setInterval(refreshActiveRun, 3000)
}

const stopRunPolling = () => {
  if (!runPollTimer) return
  window.clearInterval(runPollTimer)
  runPollTimer = null
}

const runEventItems = (run: any) => {
  return (runEvents[run.id] || []).slice(-30)
}

const runIterationItems = (run: any) => {
  const iterations = Array.isArray(activeSession.value?.iterations) ? activeSession.value.iterations : []
  return iterations
    .filter((item: any) => item.run_id === run.id)
    .sort((a: any, b: any) => Number(a.round_index || 0) - Number(b.round_index || 0))
}

const runIdeaItems = (run: any) => {
  const ideas = Array.isArray(activeSession.value?.ideas) ? activeSession.value.ideas : []
  return ideas
    .filter((item: any) => item.run_id === run.id)
    .sort((a: any, b: any) => Number(a.version || 0) - Number(b.version || 0))
}

const messageTimestamp = (value: string) => {
  const time = Date.parse(value || '')
  return Number.isFinite(time) ? time : 0
}

const feedbackIdeaTitle = (ideaId: string) => {
  if (!ideaId) return ''
  const idea = findIdea(ideaId)
  return idea ? `关联：${idea.title || idea.id}` : ''
}

const chatRunSummary = (run: any, ideas: any[] = []) => {
  const parsed = run?.output?.parsed_output || {}
  const latestEvent = runEventItems(run).slice(-1)[0]
  if (run?.status === 'queued' || run?.status === 'running') {
    return latestEvent?.message || 'Agent 正在处理这轮请求。'
  }
  if (run?.status === 'failed') {
    return run?.error || latestEvent?.message || '这轮运行失败了。'
  }
  const summary = parsed.session_summary || run?.output?.raw_output?.session_summary
  if (summary) return summary
  if (ideas.length) return `已生成并保存 ${ideas.length} 个候选方案。`
  return latestEvent?.message || statusLabel(run?.status)
}

const scrollChatToBottom = async () => {
  await nextTick()
  const el = chatBodyRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

const focusChatInput = async () => {
  await nextTick()
  chatInputRef.value?.focus?.()
  const textarea = chatInputRef.value?.textarea || chatInputRef.value?.$el?.querySelector?.('textarea')
  textarea?.focus?.()
  window.setTimeout(() => {
    chatInputRef.value?.focus?.()
    const delayedTextarea = chatInputRef.value?.textarea || chatInputRef.value?.$el?.querySelector?.('textarea')
    delayedTextarea?.focus?.()
  }, 60)
}

const eventLabel = (type: string) => {
  const map: Record<string, string> = {
    'backend.queued': '排队',
    'hermes.started': 'Hermes 启动',
    'hermes.status': 'Hermes 状态',
    'hermes.tool_flow_started': '评分流程',
    'hermes.generate_ideas': '生成方案',
    'hermes.ideas_generated': '生成完成',
    'hermes.refine_ideas': '精修方案',
    'hermes.completed': '完成',
    'hermes.failed': '失败',
    'hermes.parse_failed': '解析失败',
    'direct_ai.started': 'Direct 启动',
    'direct_ai.tool_flow_started': '评分流程',
    'direct_ai.generate_ideas': '生成方案',
    'direct_ai.ideas_generated': '生成完成',
    'direct_ai.refine_ideas': '精修方案',
    'tool.score_ideas': '评分工具',
    'backend.agent_steps_persisted': '保存步骤',
    'backend.iterations_persisted': '保存迭代',
    'backend.memory_candidates_persisted': '沉淀经验',
    'backend.persisted': '保存方案',
    'backend.completed': '完成',
    'backend.parse_failed': '解析失败',
    'direct_ai.completed': '完成',
    'direct_ai.failed': '失败',
    'backend.timeout': '超时',
    'ui.idea_selected': '已选方案',
  }
  return map[type] || type || '事件'
}

const eventBrief = (event: any) => {
  const payload = event?.payload || {}
  const parts = [
    payload.round ? `第 ${payload.round} 轮` : '',
    payload.prompt_chars ? `输入 ${payload.prompt_chars} 字符` : '',
    payload.duration_ms ? `${Math.round(Number(payload.duration_ms) / 1000)} 秒` : '',
    payload.idea_count ? `${payload.idea_count} 个方案` : '',
    payload.best_score !== undefined && payload.best_score !== null ? `最佳 ${payload.best_score} 分` : '',
    payload.target_reached !== undefined && payload.target_reached !== null ? (payload.target_reached ? '已达标' : '未达标') : '',
    payload.idea_ids?.length ? `${payload.idea_ids.length} 个方案` : '',
  ].filter(Boolean)
  return parts.join(' · ')
}

const streamTagText = (message: any) => {
  const tags = Array.isArray(message?.tags) ? message.tags : []
  const label = eventLabel(message?.event?.event_type)
  return tags.filter((tag: string) => tag && tag !== label).join(' · ')
}

const hasEventDetails = (event: any, run?: any) => {
  const payload = event?.payload
  return Boolean(
    (payload && typeof payload === 'object' && Object.keys(payload).length > 0) ||
    eventRelatedPayload(event, run)
  )
}

const eventDetailRows = (event: any, run?: any) => {
  const payload = event?.payload || {}
  const related = eventRelatedPayload(event, run)
  return [
    ['轮次', payload.round ? `第 ${payload.round} 轮` : ''],
    ['工具', payload.tool_name],
    ['模型', payload.model],
    ['耗时', payload.duration_ms ? `${Math.round(Number(payload.duration_ms) / 1000)} 秒` : ''],
    ['最佳方案', payload.best_index !== undefined && payload.best_index !== null ? String(payload.best_index) : ''],
    ['最佳分数', payload.best_score !== undefined && payload.best_score !== null ? String(payload.best_score) : ''],
    ['目标分数', payload.target_score !== undefined && payload.target_score !== null ? String(payload.target_score) : ''],
    ['达标', payload.target_reached !== undefined && payload.target_reached !== null ? (payload.target_reached ? '是' : '否') : ''],
    ['输出字符', payload.output_chars !== undefined && payload.output_chars !== null ? String(payload.output_chars) : ''],
    ['下一步', payload.next_action],
    ['方案数', payload.idea_ids?.length ? String(payload.idea_ids.length) : ''],
    ['步骤数', payload.agent_step_ids?.length ? String(payload.agent_step_ids.length) : ''],
    ['迭代数', payload.iteration_ids?.length ? String(payload.iteration_ids.length) : ''],
    ['Memory 数', payload.memory_entry_ids?.length ? String(payload.memory_entry_ids.length) : ''],
    ['关联详情', related?.label],
  ]
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([label, value]) => ({ label, value: String(value) }))
}

const eventDetailJson = (event: any, run?: any) => {
  const related = eventRelatedPayload(event, run)
  if (related?.data) return formatJson(related.data)
  const payload = event?.payload
  if (!payload || typeof payload !== 'object') return ''
  return formatJson(payload)
}

const asArray = (value: any) => Array.isArray(value) ? value : []

const actualSkillGuidanceForEvent = (event?: any) => {
  const type = event?.event_type || ''
  if (type.includes('generate_ideas') || type.includes('ideas_generated')) {
    return ['creative-concept-generator', 'naked-eye-3d-scriptwriter']
  }
  if (type.includes('refine_ideas')) {
    return ['creative-iteration-loop', 'naked-eye-3d-scriptwriter']
  }
  return []
}

const actualCallText = (event?: any, run?: any) => {
  const type = event?.event_type || ''
  const toolName = event?.payload?.tool_name
  if (type === 'tool.score_ideas') return 'backend tool：score_ideas'
  if (type.includes('ideas_generated') || type.includes('generate_ideas')) {
    return `${run?.provider === 'direct_ai' ? 'Direct' : 'Hermes'} 创意生成模型调用`
  }
  if (type.includes('refine_ideas')) return `${run?.provider === 'direct_ai' ? 'Direct' : 'Hermes'} 创意精修模型调用`
  if (type.includes('tool_flow_started')) return 'backend tool 流程编排'
  if (toolName) return String(toolName)
  return ''
}

const inputContextText = (run?: any) => {
  const parts = [
    run?.input?.brief ? 'brief' : '',
    run?.input?.designer_direction ? '设计方向' : '',
    asArray(run?.input?.seed_ideas).length ? `${run.input.seed_ideas.length} 个种子方案` : '',
    run?.input?.team_memory_count ? `团队 Memory ${run.input.team_memory_count} 条` : '',
    run?.input?.personal_memory_count ? `个人 Memory ${run.input.personal_memory_count} 条` : '',
  ].filter(Boolean)
  return parts.join(' / ')
}

const runAgentStepItems = (run?: any) => {
  const steps = asArray(activeSession.value?.agent_steps)
  if (!run?.id) return []
  return steps
    .filter((step: any) => step.run_id === run.id)
    .sort((a: any, b: any) => Number(a.step_index || 0) - Number(b.step_index || 0))
}

const eventNarrative = (event: any, run?: any) => {
  const related = eventRelatedPayload(event, run)
  const data = related?.data || {}
  const payload = event?.payload || {}
  const parsed = run?.output?.parsed_output || {}
  const steps = data.agent_steps || data.react_trace || data.react_steps || []
  const iterations = data.iterations || data.iteration_summary || []
  const ideas = data.ideas || []
  const evaluatorResults = eventCanShowScores(event)
    ? (data.evaluator_tool_results || parsed.evaluator_tool_results || [])
    : []
  const scores = scoreRowsFromEvent(payload, evaluatorResults)

  if (['hermes.generate_ideas', 'direct_ai.generate_ideas', 'hermes.refine_ideas', 'direct_ai.refine_ideas'].includes(event?.event_type)) {
    const generatedIdeas = fallbackGeneratedIdeasForEvent(run)
    const request = run?.input?.request || {}
    return {
      summary: generatedIdeas.length
        ? `这一轮已进入候选方案生成；当前运行已保存 ${generatedIdeas.length} 个候选方案，评分会在后续 score_ideas 事件里展示。`
        : '这一轮正在准备生成候选方案，生成完成后会进入 score_ideas 评分。',
      steps: [
        {
          step: payload.round || 1,
          phase: 'action',
          title: event?.event_type?.includes('refine') ? '基于评分精修方案' : '生成候选方案',
          body: event?.event_type?.includes('refine')
            ? 'Agent 读取上一轮评分建议，围绕低分维度重写候选方案。'
            : '本步输入包含 brief、设计方向、Skill 指南和已启用 Memory；实际调用为创意生成模型，本事件不包含评分。',
          rows: [
            { label: '实际调用', value: actualCallText(event, run) },
            { label: 'Skill 指南', value: actualSkillGuidanceForEvent(event).join('\n') },
            { label: '输入上下文', value: inputContextText(run) },
            { label: '输入规模', value: payload.prompt_chars ? `${payload.prompt_chars} 字符` : '' },
            { label: '策略', value: request.strategy },
            { label: '目标方案数', value: request.idea_count ? `${request.idea_count} 个` : '' },
            { label: '目标分数', value: request.target_score ? `${request.target_score} 分` : '' },
            { label: '设计方向', value: run?.input?.designer_direction || request.designer_direction },
            { label: '种子方案', value: Array.isArray(run?.input?.seed_ideas) && run.input.seed_ideas.length ? `${run.input.seed_ideas.length} 个` : '' },
            { label: '下一步', value: '调用 score_ideas 评分工具' },
          ].filter(row => row.value !== undefined && row.value !== null && row.value !== ''),
        },
      ],
      ideas: generatedIdeas.map(toIdeaCard),
      scores: [],
    }
  }

  if (['hermes.ideas_generated', 'direct_ai.ideas_generated'].includes(event?.event_type)) {
    const ideasFromPayload = Array.isArray(payload.ideas) ? payload.ideas : []
    return {
      summary: `第 ${payload.round || 1} 轮生成了 ${payload.idea_count || ideasFromPayload.length || 0} 个候选方案，下一步交给 score_ideas 做结构化评分。`,
      steps: [
        {
          step: payload.round || 1,
          phase: 'action',
          title: '生成候选方案',
          body: '本步输入包含 brief、设计方向、Skill 指南和已启用 Memory；实际调用为创意生成模型，本阶段不打分。',
          rows: [
            { label: '实际调用', value: actualCallText(event, run) },
            { label: 'Skill 指南', value: actualSkillGuidanceForEvent(event).join('\n') },
            { label: '输入上下文', value: inputContextText(run) },
            { label: '模型耗时', value: payload.duration_ms ? `${Math.round(Number(payload.duration_ms) / 1000)} 秒` : '' },
            { label: '候选标题', value: Array.isArray(payload.idea_titles) ? payload.idea_titles.join(' / ') : '' },
            { label: '下一步', value: payload.next_action === 'score_ideas' ? '调用 score_ideas 评分工具' : payload.next_action },
            { label: 'Token', value: usageText(payload.response_usage) },
          ].filter(row => row.value),
        },
      ],
      ideas: ideasFromPayload.map(toIdeaCard),
      scores: [],
    }
  }

  if (event?.event_type === 'tool.score_ideas') {
    const scoreSummaries = Array.isArray(payload.score_summaries) && payload.score_summaries.length
      ? payload.score_summaries
      : scoreSummariesFromScores(payload.scores)
    return {
      summary: `评分工具完成本轮评估，最佳分数 ${payload.best_score ?? '-'}，${payload.target_reached ? '已达到目标' : '还需要继续优化'}。`,
      steps: [
        {
          step: payload.round || 1,
          phase: 'observation',
          title: 'score_ideas 评分',
          body: `对当前候选方案按目标匹配度、视觉冲击力、裸眼3D适配度三项打分。`,
          rows: [
            { label: '实际调用', value: actualCallText(event, run) },
            { label: '输入上下文', value: payload.compact_input ? '候选方案 + 压缩 brief + 核心评分目标' : '' },
            { label: '耗时', value: payload.duration_ms ? `${Math.round(Number(payload.duration_ms) / 1000)} 秒` : '-' },
            { label: '最佳方案', value: payload.best_index !== undefined ? `方案 ${Number(payload.best_index) + 1}` : '-' },
            { label: '最佳分数', value: payload.best_score !== undefined ? `${payload.best_score} 分` : '-' },
            { label: '结论', value: payload.target_reached ? '达到目标，准备收束' : '未达目标，进入下一轮精修' },
            { label: '下一步', value: payload.next_action === 'finalize' ? '保存方案并结束' : payload.next_action },
          ],
        },
        ...scoreSummaries.map(toScoreFlowItem),
      ],
      scores,
    }
  }

  if (steps.length || iterations.length || ideas.length || scores.length || data.session_summary) {
    return {
      summary: data.session_summary || narrativeSummary(event, related),
      steps: steps.map(toFlowItem),
      iterations: iterations.map(toIterationCard),
      ideas: ideas.map(toIdeaCard),
      scores,
    }
  }

  if (event?.event_type === 'hermes.started') {
    return {
      summary: 'Hermes 运行已启动，本步只是创建远端 run，还没有产生创意处理结果。',
      steps: [
        {
          step: 1,
          phase: 'start',
          title: '创建运行',
          body: '后端把 brief、设计师方向、目标分数和运行配置提交给 Agent。',
          rows: [
            { label: '运行类型', value: runTypeLabel(run?.run_type) },
            { label: 'Provider', value: run?.provider === 'direct_ai' ? 'Direct' : 'Hermes' },
            { label: 'Hermes Run', value: run?.hermes_run_id || payload.run_id || '-' },
          ],
        },
      ],
    }
  }

  return null
}

const narrativeSummary = (event: any, related: any) => {
  if (related?.label) return `已关联展示 ${related.label}。`
  return event?.message || eventLabel(event?.event_type)
}

const toFlowItem = (step: any) => ({
  step: step.step || step.step_index || '',
  phase: step.phase || '',
  title: step.tool_name || step.role || '处理步骤',
  body: step.output_summary || step.observation || step.decision || step.input_summary || '',
  rows: [
    { label: '实际调用', value: step.tool_name },
    { label: '执行者', value: step.role },
    { label: '输入', value: step.input_summary },
    { label: '观察', value: step.observation },
    { label: '反思摘要', value: step.reflection_summary },
    { label: '决策', value: step.decision },
    { label: '下一步', value: step.next_action },
    { label: '分数', value: step.score_snapshot && Object.keys(step.score_snapshot).length ? scoreSnapshotText(step.score_snapshot) : '' },
    { label: '维度变化', value: dimensionDeltasText(step.dimension_deltas) },
  ].filter(row => row.value !== undefined && row.value !== null && row.value !== ''),
})

const toIterationCard = (item: any) => ({
  round: item.round || item.round_index || '-',
  score_before: item.score_before ?? 0,
  score_after: item.score_after ?? 0,
  score_delta: item.score_delta,
  focus: item.focus,
  summary: item.summary,
  agent_explanation: item.agent_explanation,
})

const toIdeaCard = (idea: any) => ({
  title: idea.title || idea.name || '方案',
  score: idea.score ?? idea.review?.total_score ?? idea.reviews?.[0]?.total_score,
  core_concept: idea.core_concept || idea.creative_concept || idea.concept,
  spatial_mechanism: idea.spatial_mechanism || idea.naked_eye_3d_mechanism,
  story_outline: idea.story_outline || idea.script,
  production_notes: idea.production_notes || idea.style_reference,
})

const toScoreFlowItem = (item: any) => ({
  step: Number(item.idea_index ?? 0) + 1,
  phase: item.grade || 'score',
  title: `方案 ${Number(item.idea_index ?? 0) + 1} 评分`,
  body: item.summary || '',
  rows: [
    { label: '总分', value: item.total_score !== undefined ? `${item.total_score} 分` : '' },
    { label: '目标匹配', value: scoreDimensionText(item.goal_fit) },
    { label: '视觉冲击', value: scoreDimensionText(item.visual_impact) },
    { label: '裸眼3D', value: scoreDimensionText(item.naked_eye_3d_fit) },
    { label: '核心问题', value: Array.isArray(item.core_issues) ? item.core_issues.join('\n') : '' },
    { label: '优化建议', value: Array.isArray(item.recommendations) ? item.recommendations.join('\n') : '' },
    { label: '风险提示', value: Array.isArray(item.risk_flags) ? item.risk_flags.join('\n') : '' },
  ].filter(row => row.value !== undefined && row.value !== null && row.value !== ''),
})

const scoreSummariesFromScores = (scores: any[] = []) => {
  if (!Array.isArray(scores)) return []
  return scores.map((item: any) => {
    const scoreMap = item?.scores && typeof item.scores === 'object' ? item.scores : {}
    return {
      idea_index: item?.idea_index,
      total_score: item?.total_score,
      grade: item?.grade,
      summary: item?.summary,
      goal_fit: scoreMap.goal_fit,
      visual_impact: scoreMap.visual_impact,
      naked_eye_3d_fit: scoreMap.naked_eye_3d_fit,
      core_issues: item?.core_issues,
      recommendations: item?.recommendations,
      risk_flags: item?.risk_flags,
    }
  })
}

const scoreDimensionText = (item: any) => {
  if (!item || typeof item !== 'object') return ''
  const score = item.score !== undefined ? `${item.score}/${item.max ?? '-'}` : ''
  const reason = item.reason ? `：${item.reason}` : ''
  return `${score}${reason}`
}

const usageText = (usage: any) => {
  if (!usage || typeof usage !== 'object') return ''
  const parts = [
    usage.prompt_tokens !== undefined ? `输入 ${usage.prompt_tokens}` : '',
    usage.completion_tokens !== undefined ? `输出 ${usage.completion_tokens}` : '',
    usage.total_tokens !== undefined ? `总计 ${usage.total_tokens}` : '',
  ].filter(Boolean)
  return parts.join(' · ')
}

const eventCanShowScores = (event: any) => {
  return ['tool.score_ideas', 'backend.completed', 'hermes.status', 'hermes.completed', 'direct_ai.completed'].includes(event?.event_type)
}

const fallbackGeneratedIdeasForEvent = (run?: any) => {
  if (!run) return []
  const persisted = runIdeaItems(run).map(summarizeIdea)
  if (persisted.length) return persisted
  const parsedIdeas = run.output?.parsed_output?.ideas || run.output?.parsed_output?.final_ideas || []
  return Array.isArray(parsedIdeas) ? parsedIdeas.map(summarizeIdea) : []
}

const scoreRowsFromEvent = (payload: any, evaluatorResults: any[] = []) => {
  const lastEvaluator = evaluatorResults.length ? evaluatorResults[evaluatorResults.length - 1] : null
  const matrix = payload?.compact_score_matrix || lastEvaluator?.compact_score_matrix || []
  return Array.isArray(matrix) ? matrix.map((item: any) => ({
    idea_index: item.idea_index,
    total_score: item.total_score,
    goal_fit: item.goal_fit,
    visual_impact: item.visual_impact,
    naked_eye_3d_fit: item.naked_eye_3d_fit,
  })) : []
}

const scoreSnapshotText = (snapshot: any) => {
  const parts = [
    snapshot.total_score !== undefined ? `总分 ${snapshot.total_score}` : '',
    snapshot.best_index !== undefined ? `最佳方案 ${Number(snapshot.best_index) + 1}` : '',
    snapshot.target_score !== undefined ? `目标 ${snapshot.target_score}` : '',
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : formatCompact(snapshot)
}

const dimensionDeltasText = (items: any[] = []) => {
  if (!Array.isArray(items) || !items.length) return ''
  return items.map((item: any) => {
    const name = item.name || item.key || '维度'
    const before = item.score_before ?? '-'
    const after = item.score_after ?? '-'
    const why = item.why ? `：${item.why}` : ''
    return `${name} ${before}→${after}${why}`
  }).join('\n')
}

const eventRelatedPayload = (event: any, run?: any) => {
  if (!event || !run) return null
  const payload = event.payload || {}
  if (event.event_type === 'backend.agent_steps_persisted') {
    const ids = new Set(payload.agent_step_ids || [])
    const steps = runAgentStepItems(run)
      .filter((step: any) => !ids.size || ids.has(step.id))
      .map((step: any) => ({
        step: step.step_index,
        phase: step.phase,
        role: step.role,
        tool_name: step.tool_name,
        input_summary: step.input_summary,
        output_summary: step.output_summary,
        observation: step.observation,
        reflection_summary: step.reflection_summary,
        decision: step.decision,
        next_action: step.next_action,
        score_snapshot: step.score_snapshot,
        dimension_deltas: step.dimension_deltas,
      }))
    const count = payload.agent_step_ids?.length || steps.length
    return count ? { label: `${count} 条实际步骤记录`, data: { agent_steps: steps } } : null
  }
  if (event.event_type === 'backend.iterations_persisted') {
    const ids = new Set(payload.iteration_ids || [])
    const items = runIterationItems(run)
      .filter((item: any) => !ids.size || ids.has(item.id))
      .map(summarizeIteration)
    return items.length ? { label: `${items.length} 轮迭代`, data: { iterations: items } } : null
  }
  if (event.event_type === 'backend.persisted') {
    const ids = new Set(payload.idea_ids || [])
    const items = runIdeaItems(run)
      .filter((idea: any) => !ids.size || ids.has(idea.id))
      .map(summarizeIdea)
    return items.length ? { label: `${items.length} 个方案`, data: { ideas: items } } : null
  }
  if (event.event_type === 'backend.memory_candidates_persisted') {
    const candidates = run.output?.parsed_output?.team_memory_candidates || []
    return candidates.length ? { label: `${candidates.length} 条 Memory 候选`, data: { team_memory_candidates: candidates } } : null
  }
  if (['backend.completed', 'hermes.status', 'hermes.completed', 'direct_ai.completed'].includes(event.event_type)) {
    const parsed = run.output?.parsed_output
    if (!parsed || typeof parsed !== 'object') return null
    return {
      label: '解析后的运行结果',
      data: {
        session_summary: parsed.session_summary,
        selected_idea_index: parsed.selected_idea_index,
        iteration_summary: (parsed.iteration_summary || []).map(summarizeIteration),
        ideas: (parsed.ideas || parsed.final_ideas || []).map(summarizeIdea),
        evaluator_tool_results: parsed.evaluator_tool_results,
        team_memory_candidates: parsed.team_memory_candidates,
      },
    }
  }
  if (event.event_type === 'hermes.started') {
    return {
      label: '启动配置',
      data: {
        provider: run.provider,
        run_type: run.run_type,
        hermes_run_id: run.hermes_run_id,
        request: run.input?.request,
        brief: run.input?.brief,
        designer_direction: run.input?.designer_direction,
        seed_ideas: run.input?.seed_ideas,
      },
    }
  }
  return null
}

const summarizeIteration = (item: any) => ({
  round: item.round_index || item.round,
  action: item.action,
  score_before: item.score_before,
  score_after: item.score_after,
  score_delta: item.score_delta,
  focus: item.focus,
  summary: item.summary,
  agent_explanation: item.agent_explanation,
  dimension_deltas: item.dimension_deltas,
  key_improvements: item.key_improvements,
})

const summarizeIdea = (idea: any) => ({
  id: idea.id,
  title: idea.title || idea.name,
  score: idea.score,
  core_concept: idea.core_concept,
  spatial_mechanism: idea.spatial_mechanism,
  story_outline: idea.story_outline,
  production_notes: idea.production_notes,
  risk_notes: idea.risk_notes,
  tags: idea.tags,
  reviews: idea.reviews,
  review: idea.review,
})

const formatCompact = (value: any) => {
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

const formatJson = (value: any) => {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

onMounted(async () => {
  await loadAll()
  syncRunPolling()
  scrollChatToBottom()
})
watch(
  () => [activeTab.value, activeSession.value?.id, chatMessages.value.length, activeRun.value?.status],
  () => {
    if (activeTab.value === 'feedback') scrollChatToBottom()
  },
)
onBeforeUnmount(stopRunPolling)
</script>

<style scoped>
.creative-agent-page {
  padding: 24px;
  min-height: 100%;
  background: #f6f7f9;
}

.page-header,
.detail-head,
.panel-head,
.run-card,
.idea-head,
.inline-row,
.header-actions,
.section-actions {
  display: flex;
  align-items: center;
}

.page-header {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.page-header h2,
.detail-head h3,
.panel-head h3 {
  margin: 0;
  color: #1d1d1f;
}

.page-header p,
.detail-head p,
.run-card p,
.empty-state p {
  margin: 6px 0 0;
  color: #6b7280;
}

.header-actions,
.run-actions,
.inline-row {
  gap: 10px;
}

.provider-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.provider-switch span {
  color: #6b7280;
  font-size: 13px;
  white-space: nowrap;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
}

.session-panel,
.detail-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.session-panel {
  padding: 16px;
  min-height: 620px;
}

.panel-head {
  justify-content: space-between;
  margin-bottom: 14px;
}

.session-list {
  margin-top: 14px;
  display: grid;
  gap: 8px;
}

.session-item {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: space-between;
  overflow: hidden;
}

.session-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.session-item strong,
.session-item span {
  display: block;
}

.session-item-main {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
}

.session-item strong {
  color: #111827;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item span {
  color: #6b7280;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-delete {
  flex: 0 0 32px;
  width: 32px;
  min-width: 32px;
  height: 32px;
  padding: 0;
  justify-content: center;
}

.session-delete :deep(.el-icon) {
  margin: 0;
}

.detail-panel {
  padding: 18px;
  min-width: 0;
}

.detail-head {
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 8px;
}

.agent-conversation-tabs :deep(.el-tabs__header) {
  display: none;
}

.agent-conversation-tabs :deep(.el-tabs__content) {
  overflow: visible;
}

.mobile-tab-nav {
  display: none;
}

.empty-state {
  min-height: 460px;
  display: grid;
  place-content: center;
  text-align: center;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.8fr);
  gap: 18px;
}

.inline-row {
  width: 100%;
}

.inline-row .el-input,
.inline-row .el-select {
  flex: 1;
}

.section-actions {
  justify-content: flex-end;
  margin-bottom: 12px;
}

.idea-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.idea-card,
.run-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.idea-head,
.run-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.run-card {
  display: block;
}

.run-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.run-event-stream {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #eef0f3;
  display: grid;
  gap: 8px;
}

.run-event-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.event-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #2563eb;
  margin-top: 7px;
}

.event-copy {
  min-width: 0;
}

.event-line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.event-line strong {
  color: #111827;
  font-size: 12px;
  font-weight: 600;
}

.event-line span,
.event-copy small {
  color: #8a94a6;
  font-size: 11px;
}

.event-copy p {
  margin: 2px 0 0;
  color: #374151;
  font-size: 12px;
  line-height: 1.45;
}

.event-copy small {
  display: block;
  margin-top: 2px;
}

.detail-disclosure {
  margin-top: 8px;
  border: 1px solid #eef0f3;
  border-radius: 8px;
  background: #fafbfc;
}

.detail-disclosure summary {
  cursor: pointer;
  list-style-position: inside;
  padding: 8px 10px;
  color: #374151;
  font-size: 12px;
  font-weight: 600;
}

.detail-kv {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 6px 10px;
  margin: 0;
  padding: 0 10px 10px;
}

.detail-kv dt,
.detail-kv dd {
  min-width: 0;
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
}

.detail-kv dt {
  color: #6b7280;
}

.detail-kv dd {
  color: #1f2937;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.detail-json {
  margin: 0 10px 10px;
  max-height: 320px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
  color: #111827;
  font-size: 11px;
  line-height: 1.5;
  white-space: pre;
}

.agent-narrative {
  padding: 0 10px 10px;
}

.agent-summary {
  margin: 0 0 10px;
  color: #374151;
  font-size: 12px;
  line-height: 1.6;
}

.agent-flow {
  display: grid;
  gap: 10px;
}

.agent-flow.single {
  margin-top: 2px;
}

.agent-flow-item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 10px;
}

.agent-flow-index {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #111827;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.agent-flow-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.agent-flow-head strong,
.agent-mini-card strong,
.score-row strong {
  color: #111827;
  font-size: 12px;
}

.agent-flow-item p,
.agent-mini-card p {
  margin: 0 0 8px;
  color: #374151;
  font-size: 12px;
  line-height: 1.6;
}

.agent-mini-kv {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 4px 8px;
  margin: 0;
}

.agent-mini-kv dt,
.agent-mini-kv dd {
  margin: 0;
  min-width: 0;
  font-size: 11px;
  line-height: 1.5;
}

.agent-mini-kv dt {
  color: #8a94a6;
}

.agent-mini-kv dd {
  color: #374151;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.agent-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.agent-mini-card,
.score-row {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}

.agent-mini-card span,
.score-row span {
  display: block;
  margin-top: 4px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.agent-mini-card small,
.score-row small {
  display: block;
  margin-top: 6px;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.5;
}

.score-matrix {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.idea-card h4,
.run-card h4 {
  margin: 0;
  color: #111827;
}

.idea-card p {
  color: #374151;
  line-height: 1.6;
}

.idea-card dl {
  margin: 12px 0;
}

.idea-card dt {
  color: #6b7280;
  font-size: 12px;
  margin-top: 8px;
}

.idea-card dd {
  margin: 4px 0 0;
  color: #1f2937;
  line-height: 1.5;
}

.idea-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.run-list,
.memory-grid,
.skill-grid {
  display: grid;
  gap: 10px;
}

.memory-grid,
.skill-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.memory-card,
.skill-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.memory-card-head,
.skill-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.memory-card strong,
.skill-card strong,
.skill-summary strong {
  color: #111827;
}

.memory-card p,
.skill-card p {
  margin: 0;
  color: #374151;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.memory-card small {
  display: block;
  margin-top: 10px;
  color: #8a94a6;
  font-size: 11px;
}

.memory-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 12px;
}

.config-note {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.5;
}

.skill-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.skill-summary > div {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  min-width: 0;
}

.skill-summary strong,
.skill-summary span {
  display: block;
  min-width: 0;
  overflow-wrap: anywhere;
}

.skill-summary span {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.status-disclosure {
  margin-top: 12px;
}

.agent-chat {
  height: min(720px, calc(100vh - 260px));
  min-height: 520px;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  overflow: hidden;
}

.chat-thread {
  min-height: 0;
  overflow: auto;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chat-message {
  display: flex;
}

.chat-message.user {
  justify-content: flex-end;
}

.chat-message.agent {
  justify-content: flex-start;
}

.chat-message.event {
  justify-content: flex-start;
}

.chat-stream-line {
  width: min(720px, 86%);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.stream-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.stream-disclosure {
  min-width: 0;
}

.stream-disclosure summary {
  cursor: pointer;
  list-style: none;
}

.stream-disclosure summary::marker {
  content: '';
}

.stream-disclosure summary::-webkit-details-marker {
  display: none;
}

.stream-title {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.stream-caret {
  width: 0;
  height: 0;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  border-left: 5px solid #6b7280;
  transition: transform 0.16s ease;
  transform-origin: 45% 50%;
}

.stream-disclosure[open] .stream-caret {
  transform: rotate(90deg);
}

.stream-detail {
  margin-top: 8px;
  margin-left: 0;
  border-left: 1px solid #e5e7eb;
  padding-left: 12px;
}

.stream-detail .detail-kv,
.stream-detail .agent-narrative {
  padding-left: 0;
  padding-right: 0;
}

.stream-detail .detail-json {
  margin-left: 0;
  margin-right: 0;
}

.stream-head strong {
  color: #111827;
  font-size: 12px;
  font-weight: 600;
}

.stream-head span,
.chat-stream-line small {
  color: #8a94a6;
  font-size: 11px;
}

.chat-stream-line p {
  margin: 2px 0 0;
  color: #374151;
  font-size: 13px;
  line-height: 1.5;
}

.chat-bubble {
  width: min(720px, 86%);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.chat-message.user .chat-bubble {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.chat-meta,
.chat-run-head,
.composer-actions,
.composer-context,
.composer-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-meta {
  justify-content: space-between;
  margin-bottom: 6px;
}

.chat-meta strong {
  color: #111827;
  font-size: 13px;
}

.chat-meta span {
  color: #8a94a6;
  font-size: 11px;
}

.chat-bubble p {
  margin: 0;
  color: #1f2937;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.chat-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.chat-run {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.chat-result-ideas {
  display: grid;
  gap: 8px;
}

.chat-result-idea {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.chat-result-idea:hover {
  border-color: #93c5fd;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
}

.chat-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.chat-result-head strong {
  color: #111827;
  font-size: 13px;
}

.chat-result-idea p {
  margin: 0;
  color: #374151;
  font-size: 12px;
  line-height: 1.6;
}

.chat-result-idea small {
  display: block;
  margin-top: 6px;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.5;
}

.chat-result-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.idea-detail-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.idea-detail dl {
  margin: 0;
  display: grid;
  gap: 10px;
}

.idea-detail dt {
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}

.idea-detail dd {
  margin: 2px 0 0;
  color: #1f2937;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.chat-event-list {
  display: grid;
  gap: 4px;
}

.chat-event-list small {
  color: #6b7280;
  font-size: 11px;
  line-height: 1.5;
}

.chat-composer {
  border-top: 1px solid #e5e7eb;
  background: #fff;
  padding: 12px;
}

.composer-context {
  justify-content: space-between;
  margin-bottom: 8px;
  color: #2563eb;
  font-size: 12px;
}

.composer-actions {
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.composer-controls {
  flex: 1;
  min-width: 0;
}

.composer-controls .el-select {
  max-width: 180px;
}

@media (max-width: 900px) {
  .creative-agent-page {
    padding: 12px;
  }

  .page-header {
    gap: 12px;
    margin-bottom: 12px;
  }

  .page-header h2 {
    font-size: 20px;
  }

  .page-header p {
    font-size: 13px;
    line-height: 1.45;
  }

  .page-header,
  .detail-head {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions,
  .run-actions {
    width: 100%;
  }

  .header-actions {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .header-actions > .el-button {
    min-width: 0;
  }

  .provider-switch {
    width: 100%;
    justify-content: space-between;
  }

  .provider-switch :deep(.el-radio-group) {
    flex-shrink: 0;
  }

  .header-actions .el-button,
  .run-actions .el-button {
    flex: 1;
  }

  .workspace-grid,
  .form-grid,
  .skill-summary {
    grid-template-columns: 1fr;
  }

  .workspace-grid {
    gap: 12px;
  }

  .detail-panel,
  .session-panel {
    padding: 12px;
  }

  .session-panel {
    min-height: auto;
  }

  .panel-head {
    margin-bottom: 10px;
  }

  .session-list {
    max-height: 220px;
    overflow: auto;
    padding-right: 2px;
  }

  .session-item {
    padding: 10px;
  }

  .detail-head {
    margin-bottom: 10px;
  }

  .mobile-tab-nav {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 6px;
    margin-bottom: 10px;
    padding: 4px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #f9fafb;
  }

  .mobile-tab-nav button {
    min-width: 0;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: #6b7280;
    font-size: 13px;
    line-height: 1;
    padding: 9px 6px;
  }

  .mobile-tab-nav button.active {
    background: #fff;
    color: #2563eb;
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  }

  .inline-row {
    align-items: stretch;
    flex-direction: column;
  }

  .section-actions {
    align-items: stretch;
    justify-content: stretch;
  }

  .section-actions .el-button,
  .idea-actions .el-button,
  .chat-result-actions .el-button,
  .composer-actions > .el-button {
    width: 100%;
  }

  .idea-grid,
  .memory-grid,
  .skill-grid,
  .agent-card-grid {
    grid-template-columns: 1fr;
  }

  .idea-head,
  .run-card-head,
  .memory-card-head,
  .skill-card-head,
  .chat-result-head,
  .event-line,
  .stream-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .idea-actions,
  .chat-result-actions,
  .card-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .run-meta {
    flex-wrap: wrap;
  }

  .run-event-item {
    grid-template-columns: minmax(0, 1fr);
  }

  .event-dot {
    display: none;
  }

  .detail-kv {
    grid-template-columns: 76px minmax(0, 1fr);
    padding: 0 8px 8px;
  }

  .agent-flow-item {
    grid-template-columns: 22px minmax(0, 1fr);
    gap: 8px;
  }

  .agent-flow-index {
    width: 22px;
    height: 22px;
  }

  .agent-mini-kv {
    grid-template-columns: 64px minmax(0, 1fr);
  }

  .agent-chat {
    height: calc(100vh - 190px);
    min-height: 520px;
  }

  .chat-thread {
    padding: 10px;
  }

  .chat-bubble,
  .chat-stream-line {
    width: 100%;
    box-sizing: border-box;
  }

  .stream-detail {
    padding-left: 8px;
  }

  .chat-meta {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }

  .composer-actions,
  .composer-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .composer-controls .el-select {
    width: 100%;
    max-width: none;
  }

  .composer-context {
    align-items: flex-start;
    flex-direction: column;
  }

  .creative-dialog :deep(.el-dialog) {
    width: calc(100vw - 24px) !important;
    max-height: calc(100vh - 24px);
    margin: 12px auto !important;
    display: flex;
    flex-direction: column;
  }

  .creative-dialog :deep(.el-dialog__header) {
    padding: 14px 16px 8px;
    margin-right: 0;
  }

  .creative-dialog :deep(.el-dialog__body) {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 10px 16px;
  }

  .creative-dialog :deep(.el-dialog__footer) {
    padding: 10px 16px 14px;
  }

  .agent-config-dialog :deep(.el-tabs__nav-wrap) {
    overflow-x: auto;
  }

  .agent-config-dialog :deep(.el-tabs__nav-scroll) {
    overflow: visible;
  }

  :global(.creative-dialog.el-dialog),
  :global(.creative-dialog .el-dialog) {
    width: calc(100vw - 24px) !important;
    max-height: calc(100vh - 24px);
    margin: 12px auto !important;
    display: flex;
    flex-direction: column;
  }

  :global(.creative-dialog.el-dialog .el-dialog__header),
  :global(.creative-dialog .el-dialog__header) {
    padding: 14px 16px 8px;
    margin-right: 0;
  }

  :global(.creative-dialog.el-dialog .el-dialog__body),
  :global(.creative-dialog .el-dialog__body) {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 10px 16px;
  }

  :global(.creative-dialog.el-dialog .el-dialog__footer),
  :global(.creative-dialog .el-dialog__footer) {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
    padding: 10px 16px 14px;
  }

  :global(.agent-config-dialog.el-dialog .el-tabs__nav-wrap),
  :global(.agent-config-dialog .el-tabs__nav-wrap) {
    overflow-x: auto;
  }

  :global(.agent-config-dialog.el-dialog .el-tabs__nav-scroll),
  :global(.agent-config-dialog .el-tabs__nav-scroll) {
    overflow: visible;
  }

  :global(.skill-edit-dialog.el-dialog .el-textarea__inner),
  :global(.skill-edit-dialog .el-textarea__inner) {
    min-height: 340px !important;
    max-height: 52vh;
  }
}

@media (max-width: 480px) {
  .creative-agent-page {
    padding: 10px;
  }

  .header-actions .el-button {
    flex-basis: calc(50% - 5px);
  }

  .header-actions > .el-tag {
    width: 100%;
    justify-content: center;
  }

  .provider-switch {
    align-items: stretch;
    flex-direction: column;
  }

  .provider-switch :deep(.el-radio-group) {
    width: 100%;
  }

  .provider-switch :deep(.el-radio-button) {
    flex: 1;
  }

  .provider-switch :deep(.el-radio-button__inner) {
    width: 100%;
  }

  .mobile-tab-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .agent-chat {
    height: calc(100vh - 170px);
    min-height: 500px;
  }

  .chat-composer {
    padding: 10px;
  }

  .detail-kv,
  .agent-mini-kv {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .detail-json {
    max-height: 240px;
  }

  :global(.creative-dialog.el-dialog .el-dialog__footer),
  :global(.creative-dialog .el-dialog__footer) {
    flex-direction: column-reverse;
  }

  :global(.creative-dialog.el-dialog .el-dialog__footer .el-button),
  :global(.creative-dialog .el-dialog__footer .el-button) {
    width: 100%;
    margin-left: 0;
  }
}
</style>
