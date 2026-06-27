<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

interface Classroom {
  id: number
  teacher_id: number
  teacher_name: string
  teacher_username: string
  course_id: number | null
  name: string
  description: string
  invite_code: string
  status: string
  student_count: number
  assignment_count: number
}

interface ClassroomStudent {
  id: number
  username: string
  email: string
  display_name: string
  enrollment_status: string
  joined_at: string
}

interface Assignment {
  id: number
  classroom_id: number
  title: string
  description: string
  instructions: string
  status: string
  submission_status: string | null
  score: number | null
  feedback: string
}

interface Submission {
  id: number
  assignment_id: number
  student_id: number
  student_name: string
  content: string
  status: string
  score: number | null
  feedback: string
}

const auth = useAuthStore()
const canCreateClasses = computed(() => auth.user?.permissions.includes('class:manage') ?? false)
const canViewClassManagementData = computed(() =>
  Boolean(
    auth.user?.permissions.includes('class:manage') ||
      auth.user?.permissions.includes('class:view_all') ||
      auth.user?.permissions.includes('class:manage_all'),
  ),
)
const canJoinClasses = computed(() => auth.user?.permissions.includes('class:join') ?? false)
const canGrade = computed(() => auth.user?.permissions.includes('assignment:grade') ?? false)

const classes = ref<Classroom[]>([])
const selectedClassId = ref<number | null>(null)
const students = ref<ClassroomStudent[]>([])
const assignments = ref<Assignment[]>([])
const submissions = ref<Submission[]>([])
const myAssignments = ref<Assignment[]>([])
const loading = ref('')
const error = ref('')
const notice = ref('')

const className = ref('')
const classDescription = ref('')
const inviteCode = ref('')
const assignmentTitle = ref('')
const assignmentDescription = ref('')
const assignmentInstructions = ref('')
const submissionContent = ref<Record<number, string>>({})
const gradeScores = ref<Record<number, number>>({})
const gradeFeedback = ref<Record<number, string>>({})

const selectedClass = computed(() => classes.value.find((item) => item.id === selectedClassId.value) ?? null)
const canManageSelectedClass = computed(() =>
  Boolean(selectedClass.value && canManageClass(selectedClass.value)),
)
const canCreateAssignments = computed(() =>
  Boolean(auth.user?.permissions.includes('assignment:manage') && canManageSelectedClass.value),
)
const canReadSubmissions = computed(() =>
  Boolean(
    selectedClass.value &&
      (auth.user?.permissions.includes('assignment:view_all') || canManageSelectedClass.value),
  ),
)
const canGradeSelectedClass = computed(() => canGrade.value && canManageSelectedClass.value)
const visibleAssignments = computed(() =>
  canViewClassManagementData.value ? assignments.value : myAssignments.value,
)

function setError(err: unknown, fallback: string) {
  error.value = err instanceof Error ? err.message : fallback
  notice.value = ''
}

function canManageClass(classroom: Classroom): boolean {
  return Boolean(
    auth.user?.permissions.includes('class:manage_all') ||
      (auth.user?.permissions.includes('class:manage') && classroom.teacher_id === auth.user.id),
  )
}

async function loadClasses() {
  loading.value = 'classes'
  error.value = ''
  try {
    classes.value = await api<Classroom[]>('/api/classrooms')
    if (!selectedClassId.value && classes.value.length) {
      selectedClassId.value = classes.value[0].id
      await loadClassDetail(classes.value[0])
    }
  } catch (err) {
    setError(err, '班级列表加载失败')
  } finally {
    loading.value = ''
  }
}

async function loadMyAssignments() {
  if (!canJoinClasses.value) return
  try {
    myAssignments.value = await api<Assignment[]>('/api/assignments/my')
  } catch {
    myAssignments.value = []
  }
}

async function createClassroom() {
  loading.value = 'create-class'
  error.value = ''
  notice.value = ''
  try {
    const classroom = await api<Classroom>('/api/classrooms', {
      method: 'POST',
      body: JSON.stringify({
        name: className.value,
        description: classDescription.value,
      }),
    })
    className.value = ''
    classDescription.value = ''
    notice.value = `班级已创建，邀请码：${classroom.invite_code}`
    await loadClasses()
  } catch (err) {
    setError(err, '创建班级失败')
  } finally {
    loading.value = ''
  }
}

async function joinClassroom() {
  loading.value = 'join'
  error.value = ''
  notice.value = ''
  try {
    const classroom = await api<Classroom>('/api/classrooms/join', {
      method: 'POST',
      body: JSON.stringify({ invite_code: inviteCode.value }),
    })
    inviteCode.value = ''
    notice.value = `已加入班级：${classroom.name}`
    await loadClasses()
    await loadMyAssignments()
  } catch (err) {
    setError(err, '加入班级失败')
  } finally {
    loading.value = ''
  }
}

async function loadClassDetail(classroom: Classroom) {
  selectedClassId.value = classroom.id
  submissions.value = []
  try {
    assignments.value = await api<Assignment[]>(`/api/classrooms/${classroom.id}/assignments`)
    if (canViewClassManagementData.value) {
      students.value = await api<ClassroomStudent[]>(`/api/classrooms/${classroom.id}/students`)
    }
  } catch (err) {
    setError(err, '班级详情加载失败')
  }
}

async function createAssignment() {
  if (!selectedClass.value) return
  loading.value = 'assignment'
  error.value = ''
  notice.value = ''
  try {
    await api<Assignment>(`/api/classrooms/${selectedClass.value.id}/assignments`, {
      method: 'POST',
      body: JSON.stringify({
        title: assignmentTitle.value,
        description: assignmentDescription.value,
        instructions: assignmentInstructions.value,
      }),
    })
    assignmentTitle.value = ''
    assignmentDescription.value = ''
    assignmentInstructions.value = ''
    notice.value = '作业已发布。'
    await loadClassDetail(selectedClass.value)
  } catch (err) {
    setError(err, '发布作业失败')
  } finally {
    loading.value = ''
  }
}

async function submitAssignment(assignment: Assignment) {
  loading.value = `submit-${assignment.id}`
  error.value = ''
  notice.value = ''
  try {
    await api<Submission>(`/api/assignments/${assignment.id}/submit`, {
      method: 'POST',
      body: JSON.stringify({ content: submissionContent.value[assignment.id] || '' }),
    })
    submissionContent.value[assignment.id] = ''
    notice.value = '作业已提交。'
    await loadMyAssignments()
    if (selectedClass.value) await loadClassDetail(selectedClass.value)
  } catch (err) {
    setError(err, '提交作业失败')
  } finally {
    loading.value = ''
  }
}

async function loadSubmissions(assignment: Assignment) {
  loading.value = `submissions-${assignment.id}`
  error.value = ''
  try {
    submissions.value = await api<Submission[]>(`/api/assignments/${assignment.id}/submissions`)
  } catch (err) {
    setError(err, '提交记录加载失败')
  } finally {
    loading.value = ''
  }
}

async function gradeSubmission(submission: Submission) {
  loading.value = `grade-${submission.id}`
  error.value = ''
  notice.value = ''
  try {
    const score = Number(gradeScores.value[submission.id] ?? 0)
    await api<Submission>(`/api/submissions/${submission.id}/grade`, {
      method: 'POST',
      body: JSON.stringify({
        score,
        feedback: gradeFeedback.value[submission.id] || '',
      }),
    })
    notice.value = '批改结果已保存。'
    const assignment = assignments.value.find((item) => item.id === submission.assignment_id)
    if (assignment) await loadSubmissions(assignment)
  } catch (err) {
    setError(err, '批改失败')
  } finally {
    loading.value = ''
  }
}

onMounted(async () => {
  await loadClasses()
  await loadMyAssignments()
})
</script>

<template>
  <section class="page-shell">
    <header class="page-hero">
      <div>
        <p class="eyebrow">班级</p>
        <h1>班级与作业</h1>
        <p>教师创建班级并布置作业，学生通过邀请码加入班级、查看作业、提交答案和查看批改结果。</p>
      </div>
      <div class="hero-actions">
        <button type="button" class="btn-secondary" @click="loadClasses">刷新</button>
      </div>
    </header>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="two-column-grid">
      <form v-if="canCreateClasses" class="panel stack" @submit.prevent="createClassroom">
        <h2>创建班级</h2>
        <label>
          班级名称
          <input v-model.trim="className" required />
        </label>
        <label>
          班级说明
          <textarea v-model.trim="classDescription" rows="3" />
        </label>
        <button class="btn-primary" type="submit" :disabled="loading === 'create-class'">
          {{ loading === 'create-class' ? '创建中...' : '创建班级' }}
        </button>
      </form>

      <form v-if="canJoinClasses" class="panel stack" @submit.prevent="joinClassroom">
        <h2>加入班级</h2>
        <label>
          邀请码 / 班级号
          <input v-model.trim="inviteCode" required />
        </label>
        <button class="btn-primary" type="submit" :disabled="loading === 'join'">
          {{ loading === 'join' ? '加入中...' : '加入班级' }}
        </button>
      </form>
    </div>

    <section class="panel stack">
      <div class="panel-title">
        <h2>{{ canViewClassManagementData ? '班级列表' : '我的班级' }}</h2>
        <small>{{ loading === 'classes' ? '加载中...' : `${classes.length} 个班级` }}</small>
      </div>
      <p v-if="!classes.length" class="empty-state">暂无班级。</p>
      <ul v-else class="class-list">
        <li v-for="classroom in classes" :key="classroom.id" :class="{ selected: classroom.id === selectedClassId }">
          <button type="button" @click="loadClassDetail(classroom)">
            <strong>{{ classroom.name }}</strong>
            <small>
              邀请码 {{ classroom.invite_code }} · 学生 {{ classroom.student_count }} · 作业
              {{ classroom.assignment_count }}
            </small>
            <small>教师：{{ classroom.teacher_name || classroom.teacher_username || `用户 ${classroom.teacher_id}` }}</small>
          </button>
        </li>
      </ul>
    </section>

    <section v-if="selectedClass" class="panel stack">
      <div class="panel-title">
        <h2>{{ selectedClass.name }}</h2>
        <span class="status-pill">{{ selectedClass.invite_code }}</span>
      </div>
      <p class="muted">{{ selectedClass.description || '暂无班级说明' }}</p>
      <p class="muted">
        负责教师：{{ selectedClass.teacher_name || selectedClass.teacher_username || `用户 ${selectedClass.teacher_id}` }}
      </p>

      <div v-if="canViewClassManagementData" class="two-column-grid">
        <section class="stack">
          <h3>学生名单</h3>
          <p v-if="!students.length" class="empty-state">暂无学生加入。</p>
          <ul v-else class="clean-list">
            <li v-for="student in students" :key="student.id">
              <strong>{{ student.display_name }}</strong>
              <small>{{ student.username }} · {{ student.email }}</small>
            </li>
          </ul>
        </section>

        <form v-if="canCreateAssignments" class="stack" @submit.prevent="createAssignment">
          <h3>发布作业</h3>
          <label>
            标题
            <input v-model.trim="assignmentTitle" required />
          </label>
          <label>
            说明
            <textarea v-model.trim="assignmentDescription" rows="2" />
          </label>
          <label>
            作业要求
            <textarea v-model.trim="assignmentInstructions" rows="3" />
          </label>
          <button class="btn-primary" type="submit" :disabled="loading === 'assignment'">
            {{ loading === 'assignment' ? '发布中...' : '发布作业' }}
          </button>
        </form>
      </div>
    </section>

    <section class="panel stack">
      <h2>{{ canViewClassManagementData ? '班级作业' : '我的作业' }}</h2>
      <p v-if="!visibleAssignments.length" class="empty-state">暂无作业。</p>
      <ul v-else class="clean-list">
        <li v-for="assignment in visibleAssignments" :key="assignment.id">
          <div class="assignment-row">
            <div>
              <strong>{{ assignment.title }}</strong>
              <p>{{ assignment.description || assignment.instructions || '暂无说明' }}</p>
              <small v-if="assignment.submission_status">
                {{ assignment.submission_status === 'graded' ? `已批改，得分 ${assignment.score}` : '已提交' }}
                <span v-if="assignment.feedback"> · {{ assignment.feedback }}</span>
              </small>
            </div>
            <button
              v-if="canReadSubmissions"
              type="button"
              class="btn-secondary"
              @click="loadSubmissions(assignment)"
            >
              提交记录
            </button>
          </div>

          <form v-if="canJoinClasses" class="submit-box" @submit.prevent="submitAssignment(assignment)">
            <textarea v-model.trim="submissionContent[assignment.id]" rows="3" placeholder="填写作业答案" required />
            <button class="btn-primary" type="submit" :disabled="loading === `submit-${assignment.id}`">
              {{ loading === `submit-${assignment.id}` ? '提交中...' : '提交作业' }}
            </button>
          </form>
        </li>
      </ul>
    </section>

    <section v-if="canReadSubmissions && submissions.length" class="panel stack">
      <h2>提交记录</h2>
      <ul class="clean-list">
        <li v-for="submission in submissions" :key="submission.id">
          <strong>{{ submission.student_name || `学生 ${submission.student_id}` }}</strong>
          <p>{{ submission.content }}</p>
          <small>
            {{ submission.status === 'graded' ? `已批改，得分 ${submission.score}` : '待批改' }}
            <span v-if="submission.feedback"> · {{ submission.feedback }}</span>
          </small>
          <div v-if="canGradeSelectedClass" class="grade-grid">
            <label>
              分数
              <input v-model.number="gradeScores[submission.id]" type="number" min="0" max="100" />
            </label>
            <label>
              反馈
              <input v-model.trim="gradeFeedback[submission.id]" />
            </label>
            <button type="button" class="btn-primary" @click="gradeSubmission(submission)">保存批改</button>
          </div>
          <small v-else class="muted">只读查看提交记录。</small>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.class-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.class-list button {
  display: grid;
  width: 100%;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  color: var(--text);
  background: #ffffff;
  text-align: left;
}

.class-list .selected button {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.assignment-row {
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

p {
  margin: 0;
  white-space: pre-wrap;
}

.submit-box {
  display: grid;
  gap: 10px;
  margin-top: 8px;
}

.grade-grid {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: end;
}

@media (max-width: 900px) {
  .class-list,
  .grade-grid {
    grid-template-columns: 1fr;
  }

  .assignment-row {
    display: grid;
  }
}
</style>
