<template>
  <div class="avatar-upload">
    <div class="avatar-box" :class="{ disabled: uploading }" @click="choose">
      <el-avatar :size="96" :src="previewUrl || modelValue || defaultAvatar" />
      <div class="avatar-mask">更换头像</div>
    </div>
    <input ref="inputRef" type="file" accept="image/jpeg,image/png" hidden @change="onChange" />
    <div v-if="previewUrl" class="avatar-actions">
      <el-button type="primary" size="small" :loading="uploading" @click="confirm">确认上传</el-button>
      <el-button size="small" :disabled="uploading" @click="cancel">取消</el-button>
    </div>
    <p class="avatar-tip">仅支持 JPG / PNG，不超过 2MB，将裁剪为正方形</p>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadAvatar } from '@/api/user'
import { validateImageFile, cropAndCompress } from '@/utils/image'
import defaultAvatar from '@/assets/default_avatar.svg'

// 头像上传（FR-U02）：选择 → 前端校验 → canvas 裁剪压缩 → 圆形预览 → 确认上传 / 取消；失败保留原头像
defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue', 'uploaded'])

const inputRef = ref(null)
const previewUrl = ref('')
const uploading = ref(false)
let pendingBlob = null

function choose() {
  if (!uploading.value && inputRef.value) inputRef.value.click()
}

function revokePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

async function onChange(event) {
  const file = event.target.files && event.target.files[0]
  event.target.value = ''
  if (!file) return
  const error = validateImageFile(file)
  if (error) {
    ElMessage.warning(error)
    return
  }
  try {
    pendingBlob = await cropAndCompress(file)
    revokePreview()
    previewUrl.value = URL.createObjectURL(pendingBlob)
  } catch (ex) {
    ElMessage.error(ex.message || '图片处理失败')
  }
}

async function confirm() {
  if (!pendingBlob) return
  uploading.value = true
  try {
    const data = await uploadAvatar(new File([pendingBlob], 'avatar.jpg', { type: 'image/jpeg' }))
    revokePreview()
    pendingBlob = null
    emit('update:modelValue', data.avatar_url)
    emit('uploaded', data.avatar_url)
    ElMessage.success('头像已更新')
  } catch (ex) {
    ElMessage.error((ex && ex.msg) || '上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

function cancel() {
  revokePreview()
  pendingBlob = null
}

onBeforeUnmount(revokePreview)
</script>

<style scoped>
.avatar-upload {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.avatar-box {
  position: relative;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
}
.avatar-box.disabled {
  cursor: not-allowed;
}
.avatar-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}
.avatar-box:hover .avatar-mask {
  opacity: 1;
}
.avatar-tip {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-light);
}
</style>
