import { defineStore } from 'pinia'
import { getConfig } from '@/api/qa'

// AI 增强双层开关的用户层（FR-L01）：llm_available 来自 GET /api/config；用户偏好存 localStorage 键 llm_pref，
// localStorage 不可用时退化为内存状态；系统层不可用时开关控件整体不渲染
const PREF_KEY = 'llm_pref'
let memoryPref = false

function readPref() {
  try {
    return localStorage.getItem(PREF_KEY) === '1'
  } catch {
    return memoryPref
  }
}

function writePref(value) {
  memoryPref = value
  try {
    localStorage.setItem(PREF_KEY, value ? '1' : '0')
  } catch {
    // ignore
  }
}

export const useLlmPrefStore = defineStore('llmPref', {
  state: () => ({
    llm_available: false,
    loaded: false,
    enabled: readPref(),
  }),
  getters: {
    // 请求体 use_llm 取值：系统可用 ∧ 用户开启
    useLlm: (state) => state.llm_available && state.enabled,
  },
  actions: {
    async fetchConfig() {
      try {
        const data = await getConfig()
        this.llm_available = !!(data && data.llm_available)
      } catch {
        this.llm_available = false
      } finally {
        this.loaded = true
      }
    },
    setEnabled(value) {
      this.enabled = !!value
      writePref(this.enabled)
    },
  },
})
