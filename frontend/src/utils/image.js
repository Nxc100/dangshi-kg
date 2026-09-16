// 头像图片处理（FR-U02）：类型 / 大小校验 + canvas 中心裁剪正方形并压缩为 256×256 JPEG（质量 0.85）
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png']
export const MAX_IMAGE_SIZE = 2 * 1024 * 1024
export const AVATAR_SIZE = 256
export const AVATAR_QUALITY = 0.85

// 返回错误文案；合规返回空串
export function validateImageFile(file) {
  if (!file) return '请选择图片'
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) return '仅支持 JPG/PNG 格式'
  if (file.size > MAX_IMAGE_SIZE) return '图片不能超过 2MB'
  return ''
}

export function cropAndCompress(file, size = AVATAR_SIZE, quality = AVATAR_QUALITY) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const side = Math.min(img.width, img.height)
      const sx = (img.width - side) / 2
      const sy = (img.height - side) / 2
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      canvas.getContext('2d').drawImage(img, sx, sy, side, side, 0, 0, size, size)
      URL.revokeObjectURL(url)
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('图片处理失败'))),
        'image/jpeg',
        quality,
      )
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片读取失败'))
    }
    img.src = url
  })
}
