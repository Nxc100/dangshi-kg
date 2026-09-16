import request from '@/utils/request'

// GET /api/entity/<name> → {entity:{name,type,alias[],props{}}, intro, source, relations[], subgraph, favorited}；不存在 404
export const getEntity = (name) => request.get(`/entity/${encodeURIComponent(name)}`)
