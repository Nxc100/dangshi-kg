import request from '@/utils/request'

// GET /api/admin/overview → {entity_count, relation_count, user_count, today_qa_count}
export const getOverview = () => request.get('/admin/overview')

// ---- 实体管理 /api/admin/entity ----
export const listEntities = (params) => request.get('/admin/entity', { params }) // {kw, type, page, size}
export const createEntity = (data) => request.post('/admin/entity', data) // {type, name, props}
export const updateEntity = (data) => request.put('/admin/entity', data) // {type, name, props, new_name?}
// 删除以请求体传 {type, name, confirm_name?}（关系数 ≥ 20 时必须与 name 一致）
export const deleteEntity = (data) => request.delete('/admin/entity', { data })

// ---- 关系管理 /api/admin/triple ----
export const listTriples = (params) => request.get('/admin/triple', { params }) // {head, tail, rel, page, size}
export const createTriple = (data) => request.post('/admin/triple', data) // {head, head_type, rel, tail, tail_type, props?}
export const deleteTriple = (data) => request.delete('/admin/triple', { data })

// GET /api/admin/oplog?action=&from=&to=&page=&size=（只读）
export const getOpLog = (params) => request.get('/admin/oplog', { params })
