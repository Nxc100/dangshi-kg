import request from '@/utils/request'

// GET /api/quiz?n=5|10&entities=a,b → 整卷 [{id, question, options:[{key,text}], answer_key, explanation, entity, template}]
export const getQuiz = (n = 5, entities = []) => {
  const params = { n }
  if (entities && entities.length) params.entities = entities.join(',')
  return request.get('/quiz', { params })
}

// POST /api/quiz/submit（需登录）{questions, answers, duration_sec} → {record_id, score, total}
export const submitQuiz = (data) => request.post('/quiz/submit', data)

// GET /api/quiz/records?page=&size= → 分页
export const getQuizRecords = (params) => request.get('/quiz/records', { params })

// GET /api/quiz/records/<id> → 详情（逐题回顾）
export const getQuizRecord = (id) => request.get(`/quiz/records/${id}`)
