import request from '@/utils/request'

// AI 增强模块配置（FR-L06，admin 专属）
// GET  /api/admin/llm       → {enabled, provider, base_url, model, timeout, api_key_masked,
//                              has_key, runtime:{available,source,...}, module_present, providers[]}
export const getLlmConfig = () => request.get('/admin/llm')

// PUT  /api/admin/llm       api_key 留空表示不修改（后端据此保留原密钥）
export const saveLlmConfig = (data) => request.put('/admin/llm', data)

// POST /api/admin/llm/test  按表单值试打一次，不落库
export const testLlmConfig = (data) => request.post('/admin/llm/test', data)
