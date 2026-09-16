import request from '@/utils/request'

// POST /api/qa  {question, use_llm?, prev_q?, prev_a?} → 问答响应（开发规范 8.2）
export const askQuestion = (data) => request.post('/qa', data)

// GET /api/config → {llm_available}
export const getConfig = () => request.get('/config')
