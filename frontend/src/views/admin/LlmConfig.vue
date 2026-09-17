<template>
  <div class="llm-config" v-loading="loading">
    <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />

    <template v-else>
      <!-- 生效状态：库里存了什么是一回事，运行时实际用的是什么是另一回事，分开显示便于排错 -->
      <div class="card status-card">
        <div class="status-main">
          <el-tag :type="runtime.available ? 'success' : 'info'" size="large" effect="dark">
            {{ runtime.available ? 'AI 增强已生效' : 'AI 增强未生效' }}
          </el-tag>
          <div class="status-text">
            <p v-if="!data.module_present" class="status-warn">
              未检测到 <code>llm/</code> 模块目录，系统按原方案（纯图谱 + 权威原文）运行。
            </p>
            <p v-else-if="runtime.available">
              当前模型 <b>{{ runtime.model }}</b>，超时 {{ runtime.timeout }} 秒；配置来源：{{ SOURCE_ZH[runtime.source] }}。
              用户可在问答页右上角自行开启「AI 增强回答」。
            </p>
            <p v-else-if="data.enabled">
              已勾选启用，但端点 / 密钥 / 模型尚未填全，系统层仍判定为不可用。
            </p>
            <p v-else>
              未启用。问答页不会出现「AI 增强回答」开关，界面与原方案完全一致。
            </p>
          </div>
        </div>
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>

      <div class="card">
        <h3 class="block-title">模型服务配置</h3>
        <el-form :model="form" label-width="120px" class="config-form">
          <el-form-item label="启用 AI 增强">
            <el-switch v-model="form.enabled" />
            <span class="field-tip">关闭后立即回到原方案行为，无需重启</span>
          </el-form-item>

          <el-form-item label="模型厂商" :error="errors.provider">
            <el-select v-model="form.provider" placeholder="请选择厂商" class="field" @change="onProviderChange">
              <el-option v-for="p in data.providers" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <a v-if="providerDoc" :href="providerDoc" target="_blank" rel="noopener" class="field-tip link">
              获取密钥 →
            </a>
          </el-form-item>

          <el-form-item label="接口端点" :error="errors.base_url">
            <el-input v-model="form.base_url" placeholder="https://…/v1" class="field" />
            <span class="field-tip">OpenAI 兼容端点，系统会自动追加 /chat/completions</span>
          </el-form-item>

          <el-form-item label="API Key" :error="errors.api_key">
            <el-input
              v-model="form.api_key"
              type="password"
              show-password
              class="field"
              :placeholder="data.has_key ? `已配置（${data.api_key_masked}），留空表示不修改` : '请输入密钥'"
            />
            <span class="field-tip">密钥仅存服务端，接口一律只回显掩码，不会明文下发</span>
          </el-form-item>

          <el-form-item label="模型" :error="errors.model">
            <!-- 预设厂商给下拉，同时允许自填，便于厂商上新模型时无需改代码 -->
            <el-select
              v-model="form.model"
              class="field"
              filterable
              allow-create
              default-first-option
              placeholder="请选择或输入模型名"
            >
              <el-option v-for="m in modelOptions" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
          </el-form-item>

          <el-form-item label="超时（秒）" :error="errors.timeout">
            <el-input-number v-model="form.timeout" :min="1" :max="60" class="field-sm" />
            <span class="field-tip">兜底生成的硬超时；追问改写固定取 min(3, 该值)，超时即无感降级</span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
            <el-button :loading="testing" @click="test">测试连通性</el-button>
          </el-form-item>

          <el-form-item v-if="testResult" label=" ">
            <el-alert
              :type="testResult.ok ? 'success' : 'error'"
              :closable="false"
              show-icon
              :title="testResult.message"
              :description="testResult.latency_ms != null ? `耗时 ${testResult.latency_ms} ms` : ''"
            />
          </el-form-item>
        </el-form>
      </div>

      <div class="card tip-card">
        <h3 class="block-title">模块边界（三条红线）</h3>
        <ul class="rule-list">
          <li><b>图谱优先</b>：命中知识图谱的答案一律按原模板生成，<b>永不经过 AI 改写或润色</b>。</li>
          <li><b>受约束生成</b>：AI 只能依据系统检索到的权威语料段落作答，并经年份 / 实体 / 引用三项忠实度校验，任一不过即降级为原文段落。</li>
          <li><b>恒可降级</b>：未配置、用户关闭、超时、报错、校验不过——五种情况一律无感回落原方案，用户最多感知「这次是原文段落」。</li>
        </ul>
        <p class="text-light">
          每次 AI 生成的全文、所引段落与校验结果都会写入问答日志，可在
          <el-button link type="primary" @click="router.push('/admin/qalog')">问答日志</el-button>
          按「回答来源 = AI 生成」筛选查证；调用量与成功率见
          <el-button link type="primary" @click="router.push('/admin/stats')">热点统计</el-button>。
        </p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getLlmConfig, saveLlmConfig, testLlmConfig } from '@/api/adminLlm'

// AI 增强配置（FR-L06）：系统层开关 + 厂商/模型/密钥/超时，保存后即时生效无需重启
const SOURCE_ZH = { db: '后台配置', env: '.env 文件', none: '模块缺失' }

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const error = ref('')
const testResult = ref(null)

const data = reactive({ providers: [], has_key: false, api_key_masked: '', module_present: true, enabled: 0 })
const runtime = reactive({ available: false, source: 'env', model: '', timeout: 5 })
const form = reactive({ enabled: false, provider: '', base_url: '', api_key: '', model: '', timeout: 5 })
const errors = reactive({ provider: '', base_url: '', api_key: '', model: '', timeout: '' })

const currentProvider = computed(() => (data.providers || []).find((p) => p.id === form.provider))
const providerDoc = computed(() => (currentProvider.value || {}).doc || '')
const modelOptions = computed(() => (currentProvider.value || {}).models || [])

function clearErrors() {
  Object.keys(errors).forEach((k) => (errors[k] = ''))
}

function apply(payload) {
  Object.assign(data, payload)
  Object.assign(runtime, payload.runtime || {})
  form.enabled = !!payload.enabled
  form.provider = payload.provider || ''
  form.base_url = payload.base_url || ''
  form.model = payload.model || ''
  form.timeout = payload.timeout || 5
  form.api_key = '' // 永远不回填密钥：后端只下发掩码，留空即表示不修改
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    apply(await getLlmConfig())
  } catch (err) {
    error.value = (err && err.msg) || 'AI 增强配置加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 切换厂商时带出预设端点与首个模型，减少手工输入出错
function onProviderChange(id) {
  const p = (data.providers || []).find((x) => x.id === id)
  if (!p) return
  if (p.base_url) form.base_url = p.base_url
  form.model = (p.models && p.models[0] && p.models[0].id) || ''
  testResult.value = null
}

function payload() {
  const body = {
    enabled: form.enabled,
    provider: form.provider,
    base_url: form.base_url.trim(),
    model: form.model.trim(),
    timeout: form.timeout,
  }
  // 只有真正填了才提交密钥；留空 = 沿用后端已存的那把
  if (form.api_key.trim()) body.api_key = form.api_key.trim()
  return body
}

async function save() {
  clearErrors()
  saving.value = true
  try {
    apply(await saveLlmConfig(payload()))
    ElMessage.success('配置已保存并即时生效')
  } catch (err) {
    if (err && err.errors) Object.assign(errors, err.errors)
    else ElMessage.error((err && err.msg) || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testLlmConfig(payload())
  } catch (err) {
    testResult.value = { ok: false, message: (err && err.msg) || '测试失败', latency_ms: null }
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.status-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.status-main {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}
.status-text p {
  margin: 0;
  line-height: 1.8;
  color: var(--color-text-secondary);
}
.status-warn {
  color: var(--color-warning);
}
.block-title {
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 600;
}
.config-form {
  max-width: 760px;
}
.field {
  width: 420px;
}
.field-sm {
  width: 160px;
}
.field-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--color-text-light);
}
.field-tip.link {
  color: var(--color-primary);
}
.tip-card {
  margin-top: 16px;
}
.rule-list {
  margin: 0 0 12px;
  padding-left: 20px;
}
.rule-list li {
  margin-bottom: 8px;
  line-height: 1.9;
  color: var(--color-text-secondary);
}
code {
  padding: 1px 5px;
  background: var(--color-bg-gray);
  border-radius: 4px;
}
</style>
