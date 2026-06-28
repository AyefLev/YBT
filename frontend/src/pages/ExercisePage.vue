<template>
  <section class="page-shell">
    <header class="page-hero">
      <div class="hero-content">
        <p class="eyebrow">练习题</p>
        <h1>{{ pageMode === 'records' ? recordsTitle : '生成练习' }}</h1>
        <p class="hero-desc">{{ pageMode === 'records' ? recordsDescription : '按知识点、题型与难度生成练习，支持公式、矩阵、表格和可渲染示意图。' }}</p>
      </div>
      <button v-if="canExportExercises" type="button" class="btn-secondary outline" :disabled="!selectedExerciseId || loading === 'export'" @click="exportExercise()">
        {{ loading === 'export' ? '导出中...' : '导出 DOCX' }}
      </button>
    </header>

    <div v-if="error" class="alert error" role="alert">{{ error }}</div>
    <div v-if="notice" class="alert success">{{ notice }}</div>
    <div v-if="draftAvailable && showGenerator" class="draft-banner">
      <span>当前页面有未保存草稿，切换页面后会自动保留。</span>
      <button type="button" class="btn-text" @click="discardDraft">清除草稿</button>
    </div>

    <section v-if="showGenerator" class="card summary-card">
      <div class="summary-info">
        <h3>模型状态</h3>
        <p>{{ capabilityText() }}</p>
      </div>
      <span class="badge large" :class="providerClass(providerStatus)">
        {{ providerLabel(providerStatus) }}
      </span>
    </section>

    <div v-if="showGenerator" class="editor-layout">
      <form class="card form-container" @submit.prevent="generateExercise">
        <div class="form-section-title">课程绑定</div>
        <div class="form-grid-2">
          <label class="form-field">
            <span>课程</span>
            <select v-model.number="form.course_id" @change="selectCourse" class="ui-input">
              <option :value="0">不绑定课程</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.title }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>章节</span>
            <select v-model.number="form.chapter_id" :disabled="!selectedCourse" class="ui-input">
              <option :value="0">不绑定章节</option>
              <option v-for="chapter in selectedCourse?.chapters ?? []" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>课次</span>
            <select v-model.number="form.session_id" :disabled="!form.chapter_id" class="ui-input">
              <option :value="0">不绑定课次</option>
              <option v-for="session in availableSessions" :key="session.id" :value="session.id">{{ session.title }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>知识点</span>
            <select v-model.number="form.knowledge_point_id" :disabled="!selectedCourse" class="ui-input">
              <option :value="0">不绑定知识点</option>
              <option v-for="point in availableKnowledgePoints" :key="point.id" :value="point.id">{{ point.name }}</option>
            </select>
          </label>
        </div>
        
        <label class="form-field wide mt-2">
          <span>关联教案</span>
          <select v-model.number="form.lesson_id" class="ui-input">
            <option :value="0">不绑定教案</option>
            <option v-for="lesson in availableLessons" :key="lesson.id" :value="lesson.id">{{ lesson.title }}</option>
          </select>
        </label>

        <div class="form-divider"></div>
        <div class="form-section-title">习题参数</div>
        
        <label class="form-field wide">
          <span>练习标题</span>
          <input v-model.trim="form.title" required class="ui-input" />
        </label>

        <div class="form-grid-2">
          <label class="form-field">
            <span>学科</span>
            <input v-model.trim="form.subject" required class="ui-input" />
          </label>
          <label class="form-field">
            <span>核心知识点</span>
            <input v-model.trim="form.knowledge_point" required class="ui-input" />
          </label>
          <label class="form-field">
            <span>题型</span>
            <select v-model="form.question_type" class="ui-input">
              <option>选择题</option>
              <option>填空题</option>
              <option>判断题</option>
              <option>简答题</option>
              <option>计算题</option>
              <option>证明题</option>
              <option>综合题</option>
            </select>
          </label>
          <label class="form-field">
            <span>难度</span>
            <select v-model="form.difficulty" class="ui-input">
              <option>基础</option>
              <option>中等</option>
              <option>提高</option>
            </select>
          </label>
          <label class="form-field wide">
            <span>题量</span>
            <input v-model.number="form.count" type="number" min="1" required class="ui-input" />
          </label>
        </div>

        <div class="form-divider"></div>
        
        <label class="checkbox-field wide">
          <input v-model="form.use_materials" type="checkbox" class="ui-checkbox" />
          <span>使用机构知识库材料</span>
        </label>
        
        <div v-if="form.use_materials" class="materials-zone wide">
          <MaterialPicker v-model="selectedMaterialIds" :materials="materials" :context-ids="contextIds" />
          <div class="retrieval-grid">
            <label class="form-field">
              <span>参考资料数量</span>
              <input v-model.number="form.reference_count" type="number" min="1" max="20" class="ui-input" />
            </label>
            <label class="form-field">
              <span>检索侧重点</span>
              <select v-model="form.retrieval_focus" class="ui-input">
                <option value="precise">更精准</option>
                <option value="balanced">均衡</option>
                <option value="broad">更宽泛</option>
              </select>
            </label>
          </div>
          <RouterLink class="action-link" :to="{ path: '/dashboard/materials/upload', query: { ...buildTeachingContextQuery(contextIds), return_to: '/dashboard/exercise/generate' } }">
            + 上传当前课程资料
          </RouterLink>
        </div>

        <div class="flex-options wide mt-2">
          <label class="checkbox-field">
            <input v-model="form.multi_agent_review" type="checkbox" class="ui-checkbox" />
            <span>多 AI 核验</span>
          </label>
          <label class="checkbox-field">
            <input v-model="form.auto_revise" type="checkbox" class="ui-checkbox" />
            <span>有风险时自动修订</span>
          </label>
        </div>

        <label class="form-field wide mt-4">
          <span>教师补充提示词</span>
          <textarea v-model.trim="form.prompt_template" rows="2" class="ui-input textarea" placeholder="例如：贴合本节课例题，答案解析分步骤"></textarea>
        </label>
        <label class="form-field wide">
          <span>输出格式要求</span>
          <textarea v-model.trim="form.output_format" rows="2" class="ui-input textarea" placeholder="例如：每题包含题干、答案、解析、知识点标签"></textarea>
        </label>

        <button class="btn-primary wide mt-4" type="submit" :disabled="loading === 'generate'">
          <span v-if="loading === 'generate'" class="spinner"></span>
          {{ loading === 'generate' ? '生成中...' : '生成习题' }}
        </button>
      </form>

      <div class="workspace-column stack">
        <section class="card content-area">
          <div class="split-pane">
            <div class="pane-section editor-section">
              <label class="pane-title">习题源码 (可编辑)</label>
              <textarea v-model="content" class="ui-input editor-textarea" placeholder="生成或粘贴习题内容后保存。"></textarea>
            </div>
            
            <div class="pane-section preview-section">
              <strong class="pane-title">富文本预览</strong>
              <div class="preview-container">
                <p v-if="!content" class="empty-state">生成内容后会在这里预览公式、矩阵和示意图。</p>
                <div v-else class="preview-blocks">
                  <template v-for="(block, index) in visiblePreviewBlocks" :key="index">
                    <MarkdownPreview v-if="block.type === 'text'" :content="block.content" />
                    
                    <div v-else-if="block.type === 'formula'" class="formula-block">
                      <table v-if="block.matrixRows" class="matrix-preview">
                        <tbody>
                          <tr v-for="(row, rowIndex) in block.matrixRows" :key="rowIndex">
                            <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                          </tr>
                        </tbody>
                      </table>
                      <pre v-else>{{ block.content }}</pre>
                    </div>
                    
                    <div v-else class="svg-block" v-html="block.content" />
                  </template>
                  
                  <div v-if="hiddenPreviewCount" class="preview-more-banner">
                    已折叠 {{ hiddenPreviewCount }} 个后续片段，完整内容请在左侧编辑区查看。
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="action-footer">
            <label class="form-field inline-field">
              <span>版本说明:</span>
              <input v-model.trim="form.change_note" class="ui-input small-input" />
            </label>
            <div class="action-buttons">
              <button class="btn-secondary" type="button" :disabled="!selectedExerciseId || loading === `question-bank-${selectedExerciseId}`" @click="saveToQuestionBank()">
                {{ loading === `question-bank-${selectedExerciseId}` ? '转存中...' : '保存到题库草稿' }}
              </button>
              <button class="btn-primary" type="button" :disabled="!content || loading === 'save'" @click="saveExercise">
                {{ loading === 'save' ? '保存中...' : '保存习题' }}
              </button>
            </div>
          </div>
        </section>

        <div class="insights-stack">
          <div v-if="compliance" class="insight-card warning">
            <div class="card-header">合规风险：{{ riskLabel(compliance.risk_level) }}</div>
            <div class="card-body">
              <p v-if="compliance.matched_terms.length"><strong>命中词：</strong>{{ compliance.matched_terms.join('、') }}</p>
              <p v-if="compliance.suggestions.length"><strong>建议：</strong>{{ compliance.suggestions.join('；') }}</p>
            </div>
          </div>

          <div v-if="review?.enabled" class="insight-card info">
            <div class="card-header">AI 复核：{{ review.status }} ({{ review.reviewer_model }})</div>
            <div class="card-body">
              <p v-if="review.warnings.length"><strong>风险：</strong>{{ review.warnings.join('；') }}</p>
              <p v-if="review.suggestions.length"><strong>建议：</strong>{{ review.suggestions.join('；') }}</p>
            </div>
          </div>

          <div v-if="revisedPreviewContent" class="insight-card success">
            <div class="card-header flex-between">
              <span>AI 修订建议稿</span>
              <button type="button" class="btn-text small" @click="adoptRevisedContent">采纳修订</button>
            </div>
            <div class="card-body scrollable">
              <MarkdownPreview :content="revisedPreviewContent" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <section v-if="showRecords" class="card stack">
      <div class="records-header">
        <div class="header-text">
          <h2>{{ recordsTitle }}</h2>
          <p class="subtitle">{{ showManagementRecords ? '全局记录会标注所属教师，管理员默认只查看和运维。' : '只显示当前账号创建的练习。' }}</p>
        </div>
        <label v-if="showManagementRecords && exerciseOwnerOptions.length" class="form-field inline-field">
          <span>所属教师</span>
          <select v-model="ownerFilter" class="ui-input">
            <option value="all">全部教师</option>
            <option v-for="owner in exerciseOwnerOptions" :key="owner.id" :value="String(owner.id)">{{ owner.name }}</option>
          </select>
        </label>
      </div>
      
      <div v-if="!visibleExercises.length" class="empty-state large">暂无习题记录。</div>
      <ul v-else class="record-list">
        <li v-for="exercise in visibleExercises" :key="exercise.id" class="record-item" :class="{ active: exercise.id === selectedExerciseId }">
          <div class="record-info">
            <strong class="title">{{ exercise.title }}</strong>
            <div class="meta">
              <span class="tag">{{ exercise.subject }}</span>
              <span class="tag">{{ exercise.knowledge_point }}</span>
              <template v-if="showManagementRecords">
                <span class="divider">•</span>
                <span>教师: {{ exercise.owner_name || exercise.owner_username || `用户 ${exercise.owner_id}` }}</span>
              </template>
              <span class="divider">•</span>
              <span>{{ formatDate(exercise.updated_at) }}</span>
              <span class="status-pill mini" :class="exercise.compliance_level">{{ riskLabel(exercise.compliance_level) }}</span>
            </div>
          </div>
          <div class="record-actions">
            <button v-if="canReuseExercise(exercise)" type="button" class="btn-text" @click="reuseExercise(exercise)">{{ reuseExerciseLabel(exercise) }}</button>
            <button type="button" class="btn-text" @click="loadVersions(exercise)">历史版本</button>
            <button v-if="canCreateExercises" type="button" class="btn-secondary" :disabled="loading === `question-bank-${exercise.id}`" @click="saveToQuestionBank(exercise.id)">题库草稿</button>
            <button v-if="canExportExercises" type="button" class="btn-text" @click="exportExercise(exercise.id)">导出</button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="selectedExercise && versions.length" class="card stack mt-4">
      <h2>{{ selectedExercise.title }} - 历史版本</h2>
      <div class="timeline">
        <div v-for="version in versions" :key="version.id" class="timeline-item">
          <div class="timeline-header">
            <strong class="version-badge">V{{ version.version_no }}</strong>
            <span class="note">{{ version.change_note || '无版本说明' }}</span>
            <span class="date">{{ formatDate(version.created_at) }}</span>
          </div>
          <div class="timeline-content">
            <MarkdownPreview :content="version.content" />
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<style scoped>
/* Core Layout (Matches LessonPage mostly, avoiding redundancy where possible, but keeping scoped encapsulation) */
.page-shell { display: flex; flex-direction: column; gap: 24px; }
.page-hero { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid #e2e8f0; padding-bottom: 20px; }
.eyebrow { color: #2563eb; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
h1 { font-size: 1.8rem; color: #0f172a; margin: 0 0 8px 0; }
.hero-desc { color: #64748b; margin: 0; font-size: 0.95rem; }

.card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02), 0 10px 15px -3px rgba(15, 23, 42, 0.02); }
.stack { display: flex; flex-direction: column; gap: 24px; }

.summary-card {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 24px;
}
.summary-info h3 { margin: 0 0 4px 0; font-size: 1rem; color: #0f172a; }
.summary-info p { margin: 0; color: #64748b; font-size: 0.9rem; }
.badge { display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 99px; font-weight: 600; font-size: 0.85rem; }
.badge.large { padding: 6px 16px; font-size: 0.9rem; }
.badge.success { background: #dcfce7; color: #166534; }
.badge.warning { background: #fef3c7; color: #92400e; }

.editor-layout { display: grid; grid-template-columns: minmax(320px, 400px) minmax(0, 1fr); gap: 24px; align-items: start; }

/* Form Styles */
.form-container { display: flex; flex-direction: column; gap: 16px; position: sticky; top: 24px; max-height: calc(100vh - 48px); overflow-y: auto; }
.form-container::-webkit-scrollbar { width: 4px; }
.form-container::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
.form-section-title { font-size: 0.9rem; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.02em; }
.form-divider { height: 1px; background: #f1f5f9; margin: 8px 0; }
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-field { display: flex; flex-direction: column; gap: 6px; }
.form-field span { font-size: 0.85rem; font-weight: 600; color: #475569; }
.form-field.wide, .wide { grid-column: 1 / -1; }
.inline-field { flex-direction: row; align-items: center; gap: 12px; }
.inline-field span { flex-shrink: 0; }

.ui-input {
  width: 100%; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px;
  font-size: 0.95rem; color: #0f172a; background: #ffffff; transition: all 0.2s ease; font-family: inherit;
}
.ui-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15); }
.ui-input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
.ui-input.textarea { resize: vertical; min-height: 80px; }

.flex-options { display: flex; gap: 20px; }
.checkbox-field { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.ui-checkbox { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #cbd5e1; cursor: pointer; }
.materials-zone { background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 16px; margin-top: 8px; }
.retrieval-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.action-link { display: inline-block; margin-top: 12px; font-size: 0.85rem; font-weight: 600; color: #2563eb; text-decoration: none; }
.action-link:hover { text-decoration: underline; }
.mt-2 { margin-top: 8px; } .mt-4 { margin-top: 16px; }

/* Buttons */
button { font-family: inherit; }
.btn-primary, .btn-secondary, .btn-text {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 0.95rem; cursor: pointer; transition: all 0.2s; border: none;
}
.btn-primary { background: #2563eb; color: white; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary.outline { background: transparent; color: #2563eb; border: 1px solid #2563eb; }
.btn-primary.outline:hover:not(:disabled) { background: #eff6ff; }
.btn-primary:disabled { background: #93c5fd; cursor: not-allowed; }
.btn-secondary { background: #f1f5f9; color: #334155; }
.btn-secondary:hover:not(:disabled) { background: #e2e8f0; }
.btn-text { background: transparent; color: #64748b; padding: 6px 12px; }
.btn-text:hover { color: #0f172a; background: #f1f5f9; }
.btn-text.small { font-size: 0.85rem; padding: 4px 8px; }

.spinner {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: white; animation: spin 1s ease-in-out infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Workspace Column */
.workspace-column { min-width: 0; }
.content-area { display: flex; flex-direction: column; gap: 16px; padding: 20px; }
.split-pane { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; min-height: 500px; }
.pane-section { display: flex; flex-direction: column; gap: 8px; }
.pane-title { font-size: 0.9rem; font-weight: 700; color: #334155; }

.editor-textarea { flex: 1; min-height: 400px; font-family: 'Menlo', 'Monaco', 'Courier New', monospace; font-size: 0.9rem; line-height: 1.6; background: #fafafa; }
.preview-container { flex: 1; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; background: #ffffff; overflow-y: auto; max-height: 600px; }

.action-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 8px; }
.action-buttons { display: flex; gap: 12px; }
.small-input { width: 300px; }

/* Advanced Formula Previews (Refined color palette) */
.preview-blocks { display: flex; flex-direction: column; gap: 16px; }
.formula-block {
  overflow: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px;
  background: #f8fafc; color: #334155; font-family: 'Cambria Math', 'Times New Roman', serif;
}
.formula-block pre { margin: 0; font-family: inherit; font-size: 1.05rem; }
.matrix-preview { position: relative; border-collapse: separate; border-spacing: 12px 6px; margin: 0 auto; font-size: 1.1rem; }
.matrix-preview::before, .matrix-preview::after {
  content: ""; position: absolute; top: -4px; bottom: -4px; width: 6px; border: 2px solid #475569; border-radius: 2px;
}
.matrix-preview::before { left: -6px; border-right: 0; border-top-right-radius: 0; border-bottom-right-radius: 0; }
.matrix-preview::after { right: -6px; border-left: 0; border-top-left-radius: 0; border-bottom-left-radius: 0; }
.matrix-preview td { min-width: 24px; text-align: center; }

.svg-block { overflow: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; background: #ffffff; text-align: center; }
.svg-block :deep(svg) { max-width: 100%; max-height: 280px; height: auto; display: inline-block; }

.preview-more-banner { margin: 0; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 12px 16px; color: #475569; background: #f8fafc; font-size: 0.9rem; text-align: center; }

/* Insights / Alerts */
.alerts-wrapper, .draft-banner { padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; }
.alert { padding: 12px 16px; border-radius: 8px; font-weight: 500; }
.alert.error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; }
.alert.success, .draft-banner { background: #ecfdf5; border: 1px solid #a7f3d0; color: #047857; }

.insight-card { border-radius: 8px; border: 1px solid; overflow: hidden; }
.insight-card .card-header { padding: 10px 16px; font-weight: 700; font-size: 0.9rem; }
.insight-card .card-body { padding: 12px 16px; background: #ffffff; font-size: 0.9rem; line-height: 1.5; }
.insight-card .card-body p { margin: 0 0 8px 0; }
.insight-card .card-body p:last-child { margin: 0; }
.insight-card.warning { border-color: #fde047; } .insight-card.warning .card-header { background: #fef9c3; color: #854d0e; }
.insight-card.info { border-color: #bfdbfe; } .insight-card.info .card-header { background: #eff6ff; color: #1e40af; }
.insight-card.success { border-color: #bbf7d0; } .insight-card.success .card-header { background: #f0fdf4; color: #166534; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }

/* Records List */
.records-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-text h2 { margin: 0 0 4px 0; font-size: 1.4rem; color: #0f172a; }
.subtitle { margin: 0; color: #64748b; font-size: 0.9rem; }

.record-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }
.record-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; border: 1px solid #e2e8f0; border-radius: 10px; background: #ffffff; transition: border-color 0.2s, box-shadow 0.2s; }
.record-item:hover { border-color: #cbd5e1; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.record-item.active { border-color: #3b82f6; background: #eff6ff; }
.record-info { display: flex; flex-direction: column; gap: 8px; }
.record-info .title { font-size: 1.05rem; color: #0f172a; }
.record-info .meta { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #64748b; }
.tag { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #475569; }
.divider { color: #cbd5e1; }
.record-actions { display: flex; gap: 8px; }
.status-pill { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; text-align: center; }
.status-pill.low { background: #dcfce7; color: #166534; } .status-pill.medium { background: #fef3c7; color: #92400e; } .status-pill.high { background: #fee2e2; color: #b91c1c; }

/* Timeline */
.timeline { display: flex; flex-direction: column; gap: 20px; border-left: 2px solid #e2e8f0; margin-left: 12px; padding-left: 24px; }
.timeline-item { position: relative; }
.timeline-item::before { content: ''; position: absolute; left: -31px; top: 0; width: 14px; height: 14px; background: #ffffff; border: 2px solid #3b82f6; border-radius: 50%; }
.timeline-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.version-badge { background: #1e293b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.timeline-header .note { font-weight: 600; color: #334155; }
.timeline-header .date { color: #94a3b8; font-size: 0.85rem; }
.timeline-content { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }

@media (max-width: 1200px) { .editor-layout { grid-template-columns: 1fr; } .form-container { position: static; max-height: none; } }
@media (max-width: 900px) { .split-pane { grid-template-columns: 1fr; min-height: auto; } .form-grid-2 { grid-template-columns: 1fr; } .record-item { flex-direction: column; align-items: flex-start; gap: 16px; } .record-actions { width: 100%; justify-content: flex-end; border-top: 1px solid #f1f5f9; padding-top: 12px; } .action-footer { flex-direction: column; align-items: flex-start; gap: 16px; } .small-input { width: 100%; } }
</style>