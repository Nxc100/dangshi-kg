// 前端校验规则（与后端 backend/common/validators.py 保持一致；后端复校为准）
export const USERNAME_RE = /^[A-Za-z0-9_]{3,20}$/
export const QUESTION_MAX_LEN = 100
export const KEYWORD_MAX_LEN = 30
export const NICKNAME_MAX_LEN = 16
export const YEAR_MIN = 1921
export const YEAR_MAX = 2021

// 密码 8–20 位且同时含字母与数字（仅供本模块的 passwordRules 使用）
function isValidPassword(value) {
  const v = String(value || '')
  return v.length >= 8 && v.length <= 20 && /[A-Za-z]/.test(v) && /\d/.test(v)
}

export function normalizeNickname(value) {
  return String(value || '').trim()
}

export function isValidNickname(value) {
  const v = normalizeNickname(value)
  return v.length >= 1 && v.length <= NICKNAME_MAX_LEN
}

// 问句：非空、≤100 字、非纯符号 / 纯空白（至少含一个汉字、字母或数字）
export function questionError(value) {
  const v = String(value || '').trim()
  if (!v) return '请输入有效问题'
  if (v.length > QUESTION_MAX_LEN) return `问题不能超过 ${QUESTION_MAX_LEN} 字`
  if (!/[一-龥A-Za-z0-9]/.test(v)) return '请输入有效问题'
  return ''
}

// 图谱搜索词：非空且 ≤ 30 字（规范 1.3，后端 validate_kw 复校）
export function isValidKeyword(value) {
  const v = String(value || '').trim()
  return v.length >= 1 && v.length <= KEYWORD_MAX_LEN
}

export function isValidYear(value) {
  const s = String(value || '').trim()
  if (!/^\d{4}$/.test(s)) return false
  const y = Number(s)
  return y >= YEAR_MIN && y <= YEAR_MAX
}

export const YEAR_ERROR = `请输入 ${YEAR_MIN}–${YEAR_MAX} 之间的年份`

// ---------------- Element Plus 表单 rules 生成器 ----------------
export const usernameRules = [
  { required: true, message: '请输入用户名', trigger: 'blur' },
  { pattern: USERNAME_RE, message: '用户名为 3–20 位字母、数字或下划线', trigger: 'blur' },
]

export const passwordRules = [
  { required: true, message: '请输入密码', trigger: 'blur' },
  {
    validator: (_rule, value, callback) =>
      isValidPassword(value) ? callback() : callback(new Error('密码为 8–20 位且需同时包含字母与数字')),
    trigger: 'blur',
  },
]

// 确认密码：getPassword 返回当前密码值
export function confirmPasswordRules(getPassword) {
  return [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) =>
        value === getPassword() ? callback() : callback(new Error('两次输入的密码不一致')),
      trigger: 'blur',
    },
  ]
}

export const nicknameRules = [
  {
    validator: (_rule, value, callback) =>
      isValidNickname(value) ? callback() : callback(new Error(`昵称为 1–${NICKNAME_MAX_LEN} 个字符`)),
    trigger: 'blur',
  },
]

// 将后端 422 的 data.errors={字段: 提示} 映射为表单项错误对象
export function pickFieldErrors(err, fields) {
  const out = {}
  const errors = (err && err.errors) || {}
  fields.forEach((f) => {
    if (errors[f]) out[f] = errors[f]
  })
  return out
}
