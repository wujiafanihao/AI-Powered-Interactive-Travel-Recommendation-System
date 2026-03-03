<template>
  <div class="profile-page">
    <el-card class="profile-card" shadow="hover">
      <template #header>
        <div class="profile-header">
          <h2>个人资料</h2>
          <span class="sub">完善你的资料，让推荐更精准</span>
        </div>
      </template>

      <div class="avatar-section">
        <el-avatar :size="96" :src="displayAvatarUrl" :icon="UserFilled" />
        <div class="avatar-actions">
          <el-upload
            :show-file-list="false"
            :before-upload="beforeAvatarUpload"
            :http-request="uploadAvatarRequest"
            accept="image/png,image/jpeg"
          >
            <el-button type="primary" plain>上传头像</el-button>
          </el-upload>
          <p class="tip">支持 JPG/PNG，大小不超过 5MB</p>
        </div>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="96px"
        class="profile-form"
      >
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="form.nickname" maxlength="20" show-word-limit />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="form.phone" maxlength="11" placeholder="11位手机号" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12">
            <el-form-item label="年龄" prop="age">
              <el-input-number v-model="form.age" :min="1" :max="120" style="width: 100%" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12">
            <el-form-item label="性别" prop="gender">
              <el-select v-model="form.gender" placeholder="请选择" style="width: 100%">
                <el-option label="男" value="male" />
                <el-option label="女" value="female" />
                <el-option label="保密" value="unknown" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12">
            <el-form-item label="城市" prop="city">
              <el-input v-model="form.city" placeholder="如：南京" />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12">
            <el-form-item label="生日" prop="birthday">
              <el-date-picker
                v-model="form.birthday"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24">
            <el-form-item label="旅行偏好" prop="travel_style">
              <el-select v-model="form.travel_style" multiple filterable style="width: 100%" placeholder="可多选">
                <el-option label="历史文化" value="历史文化" />
                <el-option label="自然风光" value="自然风光" />
                <el-option label="亲子" value="亲子" />
                <el-option label="摄影" value="摄影" />
                <el-option label="美食" value="美食" />
                <el-option label="城市漫游" value="城市漫游" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :xs="24">
            <el-form-item label="个人简介" prop="bio">
              <el-input
                v-model="form.bio"
                type="textarea"
                :rows="4"
                maxlength="500"
                show-word-limit
                placeholder="介绍一下你的旅行偏好吧"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="actions">
          <el-button @click="goBack">返回</el-button>
          <el-button type="primary" :loading="saving" @click="saveProfile">保存资料</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, UploadRequestOptions } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { getMe, updateProfile, uploadAvatar } from '../api/spots'
import { resolveApiAssetUrl } from '../api/index'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const saving = ref(false)
const avatarPreview = ref('')
let currentAvatarObjectUrl = ''

const displayAvatarUrl = computed(() => {
  if (avatarPreview.value) return avatarPreview.value
  return resolveApiAssetUrl(form.avatar_url || userStore.userInfo?.avatar_url)
})

const form = reactive<any>({
  nickname: '',
  phone: '',
  age: undefined,
  gender: '',
  city: '',
  birthday: '',
  travel_style: [],
  bio: '',
  avatar_url: ''
})

const rules = {
  phone: [
    {
      validator: (_: any, value: string, callback: any) => {
        if (!value) return callback()
        if (!/^1\d{10}$/.test(value)) return callback(new Error('手机号格式不正确'))
        callback()
      },
      trigger: 'blur'
    }
  ]
}

const hydrateForm = (user: any) => {
  form.nickname = user?.nickname || ''
  form.phone = user?.phone || ''
  form.age = user?.age || undefined
  form.gender = user?.gender || ''
  form.city = user?.city || ''
  form.birthday = user?.birthday || ''
  form.travel_style = Array.isArray(user?.travel_style) ? user.travel_style : []
  form.bio = user?.bio || ''
  form.avatar_url = user?.avatar_url || ''
}

const loadMe = async () => {
  const me = await getMe()
  userStore.setUserInfo(me)
  hydrateForm(me)
}

const beforeAvatarUpload = (file: File) => {
  const okType = file.type === 'image/png' || file.type === 'image/jpeg'
  if (!okType) {
    ElMessage.error('仅支持 JPG/PNG')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('头像不能超过 5MB')
    return false
  }
  if (currentAvatarObjectUrl) {
    URL.revokeObjectURL(currentAvatarObjectUrl)
  }
  currentAvatarObjectUrl = URL.createObjectURL(file)
  avatarPreview.value = currentAvatarObjectUrl
  return true
}

const uploadAvatarRequest = async (options: UploadRequestOptions) => {
  try {
    const file = options.file as File
    const res = await uploadAvatar(file)
    form.avatar_url = res.avatar_url
    userStore.patchUserInfo({ avatar_url: res.avatar_url })
    ElMessage.success('头像上传成功')
    options.onSuccess?.(res as any)
  } catch (e: any) {
    options.onError?.(e)
  }
}

const saveProfile = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const payload = {
        nickname: form.nickname || null,
        phone: form.phone || null,
        age: form.age || null,
        gender: form.gender || null,
        city: form.city || null,
        birthday: form.birthday || null,
        travel_style: form.travel_style?.length ? form.travel_style : null,
        bio: form.bio || null,
        avatar_url: form.avatar_url || null
      }
      const latest = await updateProfile(payload)
      userStore.patchUserInfo(latest)
      hydrateForm({ ...userStore.userInfo, ...latest })
      ElMessage.success('资料已更新')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

const goBack = () => router.back()

onMounted(() => {
  if (!userStore.token) {
    router.push('/login?redirect=/profile')
    return
  }
  loadMe()
})

onBeforeUnmount(() => {
  if (currentAvatarObjectUrl) {
    URL.revokeObjectURL(currentAvatarObjectUrl)
    currentAvatarObjectUrl = ''
  }
})
</script>

<style scoped>
.profile-page {
  min-height: calc(100vh - 60px);
  padding: 24px;
  background: #f5f7fa;
}

.profile-card {
  max-width: 920px;
  margin: 0 auto;
  border-radius: 16px;
}

.profile-header h2 {
  margin: 0;
}

.profile-header .sub {
  font-size: 13px;
  color: #909399;
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: #909399;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
