<template>
  <div class="app-container">
    <!-- 全局消息提示 -->
    <div class="tip-box" :class="{ show: showTip }">{{ tipText }}</div>
    <!-- 顶部标题 -->
    <div class="header">
      <div class="header-icon">🎮</div>
      <h1 class="header-title">组队接龙</h1>
      <p class="header-subtitle">Steam游戏组队 · 随时开黑</p>
    </div>
    <!-- 用户输入区 -->
    <div class="user-bar">
      <input v-model="nickname" class="user-input" placeholder="昵称" />
      <input v-model="steamId" class="user-input" placeholder="Steam ID" />
      <button @click="saveUser" class="save-btn">保存</button>
    </div>
    <!-- 导航栏 -->
    <div class="tab-nav">
      <div class="tab-group">
        <button class="tab-btn" :class="{ active: activeTab === 'list' }" @click="switchTab('list')">
          📋 接龙列表
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'create', 'btn-disabled': !hasUserInfo }"
          @click="switchTab('create')">
          ➕ 发起接龙
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'my' }" @click="switchTab('my')">
          📄 我的接龙
        </button>
        <!-- 管理员专属：成员管理标签 -->
        <button v-if="isAdmin" class="tab-btn" :class="{ active: activeTab === 'member' }" @click="switchTab('member')">
          👥 成员管理
        </button>
      </div>
    </div>

    <!-- 搜索框：仅 接龙列表 显示，我的接龙、成员管理 隐藏 -->
    <div class="search-bar" v-if="activeTab === 'list' && currentPage !== 'detail'">
      <input v-model="searchKeyword" class="search-input" placeholder="搜索游戏名称/描述..." />
    </div>

    <!-- 发起/编辑接龙面板 -->
    <div class="create-panel" v-if="(activeTab === 'create' || isEditMode) && currentPage !== 'detail'">
      <div class="create-card">
        <h2 class="create-title">{{ isEditMode ? '编辑接龙' : '发起新接龙' }}</h2>
        <div class="form-group">
          <label class="form-label">🎮游戏名称</label>
          <input v-model="eventTitle" class="form-input" type="text" placeholder="例如：CS2、OW、LOL" />
        </div>

        <!-- 【改造】接龙时间：不限 + 时分选择 -->
        <div class="form-group">
          <label class="form-label">⏱️组队时间</label>
          <div class="time-select-wrap">
            <!-- 第一行：不限时间复选框 -->
            <label class="time-unlimited">
              <input type="checkbox" v-model="timeUnlimited"> 不限时间
            </label>
            <!-- 第二行：日期+时分选择器；用 visibility 而非 v-if，始终占据空间，避免勾选/取消时整体跳动 -->
            <div class="time-picker" :style="{ visibility: timeUnlimited ? 'hidden' : 'visible' }">
              <!-- 日期选择：限制最早可选日期为今天，避免选到过去的日期 -->
              <input type="date" v-model="eventDate" class="date-select" :min="todayDateStr" />
              <select v-model="eventHour" class="time-select">
                <!-- 小时范围 0-23，用 Array.from 生成从0开始的数组 -->
                <option v-for="h in Array.from({length: 24}, (_, i) => i)" :key="h" :value="String(h).padStart(2, '0')">
                  {{ String(h).padStart(2, '0') }}
                </option>
              </select>
              <span class="time-colon">:</span>
              <select v-model="eventMinute" class="time-select">
                <option value="00">00</option>
                <option value="15">15</option>
                <option value="30">30</option>
                <option value="45">45</option>
              </select>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">📝备注</label>
          <textarea v-model="eventDesc" class="form-textarea" placeholder="缺什么位置、段位要求等..." rows="3"></textarea>
        </div>
        <button @click="submitEvent" class="submit-btn">
          {{ isEditMode ? '保存修改' : '发布接龙' }}
        </button>
        <button v-if="isEditMode" class="back-normal-btn" @click="cancelEdit">
          返回
        </button>
      </div>
    </div>

    <!-- 接龙列表 -->
    <div class="event-list"
      v-if="(activeTab === 'list' || activeTab === 'my') && currentPage !== 'detail' && !isEditMode">
      <div class="event-card" v-for="item in showEventList" :key="item.id"
        :class="{ 'card-expired': item?.is_expired }"
        @click="!(item?.is_expired) && goToDetail(item.id)" :title="(item?.is_expired) ? '该接龙已失效' : ''">
        <h3 class="event-title">{{ item.title }}</h3>
        <div class="tag-group">
          <span class="tag">🕒 {{ item.time_info }}</span>
          <span class="tag">👥 {{ item.participant_num }}人已报名</span>
          <!-- 新增：失效标签 -->
          <span class="tag tag-expired" v-if="item?.is_expired">已失效</span>
        </div>
        <p class="event-desc">{{ item.description }}</p>
        <div class="event-bottom">
          <span class="participant-count">发布时间：{{ item.created_at }}</span>
          <div class="admin-op-group" v-if="isAdmin">
            <button class="edit-btn" @click.stop="openEditEvent(item.id)">编辑</button>
            <button class="del-btn" @click.stop="deleteEvent(item.id)">删除</button>
          </div>
        </div>
      </div>
      <div class="empty-tip" v-if="showEventList.length === 0">暂无数据</div>
    </div>

    <!-- 【新增】管理员 - 成员管理页面 -->
    <div class="member-panel" v-if="activeTab === 'member' && isAdmin && currentPage !== 'detail'">
      <div class="create-card">
        <h2 class="create-title">已注册成员列表</h2>
        <div class="member-list">
          <div class="member-item member-header">
            <span class="m-id">ID</span>
            <span class="m-name">昵称</span>
            <span class="m-steam">Steam ID</span>
            <span class="m-time">注册时间</span>
            <span class="m-op">操作</span>
          </div>
          <div class="member-item" v-for="user in memberList" :key="user.id">
            <span class="m-id">{{ user.id }}</span>
            <span class="m-name">{{ user.nickname }}</span>
            <span class="m-steam">{{ user.steam_id }}</span>
            <span class="m-time">{{ user.created_at }}</span>
            <span class="m-op">
              <button class="del-btn" @click="deleteMember(user.id)">删除</button>
            </span>
          </div>
          <div class="empty-tip" v-if="memberList.length === 0">暂无注册成员</div>
        </div>
      </div>
    </div>

    <!-- 接龙详情页 -->
    <div class="detail-page" v-if="currentPage === 'detail'">
      <div class="detail-card">
        <h2 class="detail-title">{{ detailEvent.title }}</h2>
        <div class="detail-tag-group">
          <span class="detail-tag">🕒 {{ detailEvent.time_info }}</span>
          <span class="detail-tag">🗓️ {{ detailEvent.created_at }}</span>
        </div>
        <div class="detail-desc-box">
          <p class="detail-desc">{{ detailEvent.description }}</p>
        </div>
        <button v-if="!isJoined" class="join-btn"
          :class="{ 'btn-disabled': !hasUserInfo || (detailEvent?.is_expired) }" @click="signUpCurrentEvent">
          🎯 加入接龙
        </button>
        <div class="signup-list">
          <h4 class="signup-title">已报名 {{ detailEvent.participant_num }} 人</h4>
          <div v-if="Array.isArray(detailSignups)" class="signup-item" v-for="(user, index) in detailSignups"
            :key="index">
            <span class="signup-index">{{ index + 1 }}</span>
            <span class="signup-name">
              {{ user.nickname }}
              <span v-if="user.nickname === nickname && user.steam_id === steamId" class="me-tag">我</span>
            </span>
            <span class="signup-steam">{{ user.steam_id }}</span>
            <button v-if="user.nickname === nickname && user.steam_id === steamId" class="quit-small-btn"
              @click="quitEvent">
              退出
            </button>
          </div>
        </div>
        <button @click="goBackToList" class="back-btn">← 返回列表</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, getCurrentInstance, computed } from 'vue'
const { proxy } = getCurrentInstance()
// 键盘指令
const inputBuffer = ref("")
let inputTimer = null
const CMD_ADMIN = "admin"
const CMD_EXIT = "exit"
const adminPwd = ref("")
// 全局键盘监听
function handleKeydown(e) {
  const activeTag = document.activeElement.tagName
  if (activeTag === 'INPUT' || activeTag === 'TEXTAREA' || activeTag === 'SELECT') return
  const key = e.key
  if (key.length !== 1) return
  inputBuffer.value += key
  clearTimeout(inputTimer)
  inputTimer = setTimeout(() => {
    inputBuffer.value = ""
  }, 5000)
  if (inputBuffer.value === CMD_ADMIN) {
    const pwd = prompt("请输入管理员密码")
    if (pwd) {
      // 把密码存入变量
      adminPwd.value = pwd
      fetch('/api/admin/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `pwd=${pwd}`
      })
        .then(res => {
          if (!res.ok) throw new Error()
          return res.json()
        })
        .then(() => {
          isAdmin.value = true
          setTip("已进入管理模式")
          getMemberList() // 加载成员列表
        })
        .catch(() => {
          setTip("管理员密码错误")
          adminPwd.value = "" // 密码错误清空
        })
    }
    inputBuffer.value = ""
    clearTimeout(inputTimer)
  } else if (inputBuffer.value === CMD_EXIT) {
    isAdmin.value = false
    adminPwd.value = "" // 退出管理模式清空密码
    setTip("已退出管理模式")
    inputBuffer.value = ""
    clearTimeout(inputTimer)
  }
  const maxLen = Math.max(CMD_ADMIN.length, CMD_EXIT.length)
  if (inputBuffer.value.length > maxLen) {
    inputBuffer.value = inputBuffer.slice(-maxLen)
  }
}
// 全局提示
const showTip = ref(false)
const tipText = ref('')
function setTip(text) {
  tipText.value = text
  showTip.value = true
  setTimeout(() => {
    showTip.value = false
  }, 2000)
}
// 用户信息
const nickname = ref('')
const steamId = ref('')
const currentUserId = ref(0)
const hasUserInfo = computed(() => !!nickname.value && !!steamId.value && !!currentUserId.value)
// 搜索关键词
const searchKeyword = ref('')
// 页面标签
const currentPage = ref('list')
const activeTab = ref('list')
// ========== 时间选择 相关变量 ==========
// 获取北京时间（UTC+8）当天日期字符串，格式 YYYY-MM-DD
// 用法：作为日期选择器的默认值，以及限制可选的最早日期（不允许选过去）
const getBeijingDateStr = () => {
  const now = new Date()
  // 将本地时间换算为北京时间：先转为UTC毫秒数，再加8小时偏移
  const beijingMs = now.getTime() + (8 * 60 + now.getTimezoneOffset()) * 60 * 1000
  const beijingDate = new Date(beijingMs)
  const y = beijingDate.getFullYear()
  const m = String(beijingDate.getMonth() + 1).padStart(2, '0')
  const d = String(beijingDate.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
// 日期选择器最早可选日期（今天，北京时间）
const todayDateStr = getBeijingDateStr()
const timeUnlimited = ref(true)
const eventDate = ref(getBeijingDateStr()) // 接龙日期，默认今天
const eventHour = ref("00")
const eventMinute = ref("00")
// 发起/编辑接龙表单
const eventTitle = ref('')
const eventDesc = ref('')
const isEditMode = ref(false)
const editEventId = ref(null)
// 管理员状态
const isAdmin = ref(false)
// 列表数据
const eventList = ref([])
const myEventList = ref([])
// 【新增】成员列表
const memberList = ref([])
// 列表搜索过滤
const showEventList = computed(() => {
  const baseList = activeTab.value === 'my' ? myEventList.value : eventList.value
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return baseList
  return baseList.filter(item =>
    item.title.toLowerCase().includes(keyword) ||
    item.description.toLowerCase().includes(keyword)
  )
})
// 详情数据
const currentEventId = ref(null)
const detailEvent = ref({})
const detailSignups = ref([])
const isJoined = ref(false)

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  const localNick = localStorage.getItem('nickname')
  const localSteam = localStorage.getItem('steamId')
  const localUid = localStorage.getItem('userId')
  if (localNick && localSteam) {
    nickname.value = localNick
    steamId.value = localSteam
  }
  if (localUid) {
    currentUserId.value = Number(localUid)
  }
  getEventList()
})
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  clearTimeout(inputTimer)
})

// 切换标签
const switchTab = (tab) => {
  if (tab === 'create' && !hasUserInfo.value) {
    setTip('请先保存昵称和Steam ID');
    return
  }
  activeTab.value = tab
  currentPage.value = ''
  isEditMode.value = false
  editEventId.value = null
  searchKeyword.value = ''
  resetEventForm()
  if (tab === 'my') {
    getMyEventList()
  } else if (tab === 'member') {
    getMemberList()
  } else {
    getEventList()
  }
}

// 重置表单（重置时间选择，日期默认回到今天）
const resetEventForm = () => {
  eventTitle.value = ''
  eventDesc.value = ''
  timeUnlimited.value = true
  eventDate.value = getBeijingDateStr()
  eventHour.value = "00"
  eventMinute.value = "00"
}

// 拼接最终时间文本：不限时间 / "YYYY-MM-DD HH:MM"
const getTimeInfo = () => {
  if (timeUnlimited.value) return "不限时间"
  return `${eventDate.value} ${eventHour.value}:${eventMinute.value}`
}

// 编辑接龙回填时间
const openEditEvent = async (eventId) => {
  try {
    const res = await fetch(`/api/events/${eventId}/single`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    const item = data.data
    isEditMode.value = true
    editEventId.value = eventId
    eventTitle.value = item.title
    eventDesc.value = item.description
    // 回填时间（兼容新格式"YYYY-MM-DD HH:MM"与历史遗留的纯"HH:MM"格式）
    const timeStr = item.time_info || ""
    if (timeStr === "不限时间") {
      timeUnlimited.value = true
      eventDate.value = getBeijingDateStr()
      eventHour.value = "00"
      eventMinute.value = "00"
    } else {
      timeUnlimited.value = false
      // 优先匹配带日期的完整格式
      const fullMatch = timeStr.match(/(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})/)
      if (fullMatch) {
        eventDate.value = fullMatch[1]
        eventHour.value = fullMatch[2]
        eventMinute.value = fullMatch[3]
      } else {
        // 历史数据仅有"HH:MM"，日期回填为今天，需用户确认/调整
        const shortMatch = timeStr.match(/(\d{2}):(\d{2})/)
        eventDate.value = getBeijingDateStr()
        eventHour.value = shortMatch ? shortMatch[1] : "00"
        eventMinute.value = shortMatch ? shortMatch[2] : "00"
      }
    }
    activeTab.value = 'create'
    currentPage.value = ''
  } catch (err) {
    setTip("加载编辑内容失败")
  }
}

// 取消编辑
const cancelEdit = () => {
  isEditMode.value = false
  editEventId.value = null
  resetEventForm()
  activeTab.value = 'list'
}

// 保存用户
const saveUser = async () => {
  if (!nickname.value || !steamId.value) {
    setTip('昵称和Steam ID不能为空')
    return
  }
  const isOnlyDigits = /^\d+$/.test(steamId.value.trim())
  if (!isOnlyDigits) {
    setTip('SteamID 必须为纯数字，请检查输入')
    return
  }
  try {
    const res = await fetch('/api/user', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        nickname: nickname.value,
        steam_id: steamId.value
      })
    })
    const data = await res.json()
    currentUserId.value = Number(data.user_id)
    localStorage.setItem('nickname', nickname.value)
    localStorage.setItem('steamId', steamId.value)
    localStorage.setItem('userId', currentUserId.value)
    setTip(data.msg)
  } catch (err) {
    setTip('保存失败')
  }
}

// 提交接龙（新增/编辑）
const submitEvent = async () => {
  if (!hasUserInfo.value) {
    setTip('请先保存昵称和Steam ID')
    return
  }
  if (!eventTitle.value) {
    setTip('请填写接龙标题')
    return
  }
  // 非"不限时间"模式下，日期为必填项
  if (!timeUnlimited.value && !eventDate.value) {
    setTip('请选择组队日期')
    return
  }
  const finalTime = getTimeInfo()
  try {
    if (isEditMode.value) {
      const res = await fetch(`/api/events/${editEventId.value}?pwd=${adminPwd.value}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: eventTitle.value,
          time_info: finalTime,
          description: eventDesc.value,
          creator_id: Number(currentUserId.value)
        })
      })
      await res.json()
      setTip('修改成功')
    } else {
      const createRes = await fetch('/api/events/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: eventTitle.value,
          time_info: finalTime,
          description: eventDesc.value,
          creator_id: Number(currentUserId.value)
        })
      })
      const createData = await createRes.json()
      const newEventId = createData.id
      await fetch(`/api/events/${newEventId}/signup?user_id=${Number(currentUserId.value)}`, {
        method: 'POST'
      })
      setTip('接龙创建成功，已自动加入')
    }
    resetEventForm()
    isEditMode.value = false
    editEventId.value = null
    activeTab.value = 'list'
    getEventList()
  } catch (err) {
    setTip('操作失败')
  }
}

// 获取全部接龙
const getEventList = async () => {
  try {
    const res = await fetch('/api/events')
    if (!res.ok) throw new Error()
    const data = await res.json()
    eventList.value = Array.isArray(data.data) ? data.data : []
  } catch (err) {
    console.error('获取列表失败', err)
    setTip('获取列表失败')
  }
}

// 获取我参与的接龙
const getMyEventList = async () => {
  if (!currentUserId.value) {
    setTip('请先保存个人信息')
    myEventList.value = []
    return
  }
  try {
    const res = await fetch(`/api/events/my-participated?user_id=${currentUserId.value}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    myEventList.value = Array.isArray(data.data) ? data.data : []
  } catch (err) {
    setTip('获取我的接龙失败')
  }
}

// 【新增】获取所有注册成员
const getMemberList = async () => {
  try {
    // 拼接管理员密码参数
    const res = await fetch(`/api/admin/users?pwd=${adminPwd.value}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    memberList.value = Array.isArray(data.data) ? data.data : []
  } catch (err) {
    setTip('获取成员列表失败')
    memberList.value = []
  }
}
// 【新增】删除注册成员
const deleteMember = async (uid) => {
  if (!confirm("确定删除该成员？")) return
  try {
    await fetch(`/api/admin/users/${uid}?pwd=${adminPwd.value}`, { method: "DELETE" })
    setTip("成员删除成功")
    getMemberList()
  } catch (err) {
    setTip("删除失败")
  }
}
// 进入接龙详情
const goToDetail = async (eventId) => {
  detailEvent.value = {}
  detailSignups.value = []
  isJoined.value = false
  currentEventId.value = eventId
  try {
    const res = await fetch(`/api/events/${eventId}`)
    if (!res.ok) throw new Error('接口请求失败')
    const contentType = res.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      throw new Error('返回非JSON数据')
    }
    const data = await res.json()
    detailEvent.value = data.data.event || {}
    detailSignups.value = Array.isArray(data.data.signups) ? data.data.signups : []
    const list = detailSignups.value
    isJoined.value = list.some(item =>
      item.nickname === nickname.value && item.steam_id === steamId.value
    )
    currentPage.value = 'detail'
  } catch (err) {
    setTip('加载详情失败')
    console.error('加载详情失败', err)
    detailSignups.value = []
  }
}

// 加入接龙
const signUpCurrentEvent = async () => {
  if (!hasUserInfo.value) {
    setTip('请先保存昵称和Steam ID')
    return
  }
  if (!currentEventId.value) return
  try {
    await fetch(`/api/events/${currentEventId.value}/signup?user_id=${Number(currentUserId.value)}`, {
      method: 'POST'
    })
    setTip('报名成功')
    goToDetail(currentEventId.value)
  } catch (err) {
    const msg = err?.message || '报名失败'
    setTip(msg)
  }
}

// 退出接龙
const quitEvent = async () => {
  if (!hasUserInfo.value) {
    setTip("请先保存昵称和Steam ID，再执行退出")
    return
  }
  if (!currentEventId.value || !currentUserId.value) return
  try {
    await fetch(`/api/events/${currentEventId.value}/quit?user_id=${Number(currentUserId.value)}`, {
      method: 'DELETE'
    })
    setTip('已退出接龙')
    goToDetail(currentEventId.value)
    getEventList()
  } catch (err) {
    setTip('退出失败')
  }
}

// 返回列表页
const goBackToList = () => {
  currentPage.value = ''
  currentEventId.value = null
  detailEvent.value = {}
  detailSignups.value = []
  if (activeTab.value === 'list') {
    getEventList()
  } else if (activeTab.value === 'my') {
    getMyEventList()
  } else if (activeTab.value === 'member') {
    getMemberList()
  }
}

// 删除接龙
const deleteEvent = async (eventId) => {
  try {
    await fetch(`/api/events/${eventId}?pwd=${adminPwd.value}`, {
      method: 'DELETE'
    })
    setTip('删除成功')
    getEventList()
  } catch (err) {
    setTip('删除失败')
  }
}
</script>

<style scoped>
/* 全局样式 */
.app-container {
  background-color: #f5f7fa;
  min-height: 100vh;
  padding: 0 20px 40px;
  color: #2d3748;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  position: relative;
}

/* 禁用样式 */
.btn-disabled {
  opacity: 0.5 !important;
  pointer-events: none !important;
  cursor: not-allowed !important;
}

/* 消息提示 */
.tip-box {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #4f46e5;
  color: #fff;
  padding: 8px 20px;
  border-radius: 8px;
  z-index: 999;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.tip-box.show {
  opacity: 1;
}

/* 头部标题 */
.header {
  text-align: center;
  padding: 30px 0;
  background: linear-gradient(180deg, #eef2ff 0%, transparent 100%);
  margin: 0 -20px 20px;
}

.header-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.header-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 6px;
  color: #1e293b;
}

.header-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

/* 用户输入栏 */
.user-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

/* ========== 核心优化：输入框 移除黑边、统一边框 ========== */
.user-input {
  flex: 1;
  background: #ffffff;
  /* 替换原生黑边：浅灰色细边框 */
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  color: #2d3748;
  outline: none;
  /* 清除默认聚焦黑轮廓 */
  transition: border 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

/* 聚焦样式：替换原生黑边，使用主题色弱阴影 */
.user-input:focus {
  border-color: #4f46e5;
  /* 用柔和阴影替代生硬黑轮廓，兼顾可用性 */
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.15);
}

.save-btn {
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
  flex-shrink: 0;
}

.save-btn:hover {
  background: #4338ca;
}

/* 导航栏 */
.tab-nav {
  max-width: 600px;
  margin: 0 auto 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 8px;
}

.tab-group {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

/* 标签按钮 */
.tab-btn {
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 14px;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn.active {
  color: #4f46e5;
  border-bottom-color: #4f46e5;
}

.tab-btn:hover {
  color: #4f46e5;
}

/* 搜索框 */
.search-bar {
  max-width: 600px;
  margin: 0 auto 20px;
}

.search-input {
  width: 100%;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 16px;
  color: #2d3748;
  outline: none;
  transition: border 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.15);
}

/* 发起/编辑面板 */
.create-panel {
  max-width: 600px;
  margin: 0 auto 24px;
}

.create-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 24px 20px;
  border: 1px solid #e2e8f0;
}

.create-title {
  color: #1e293b;
  font-size: 20px;
  font-weight: 600;
  text-align: center;
  margin: 0 0 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  color: #475569;
  font-size: 14px;
  margin-bottom: 6px;
  line-height: 1.4;
}

/* 表单输入框 统一样式 */
.form-input {
  width: 100%;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  color: #2d3748;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.form-input::placeholder {
  color: #94a3b8;
  font-size: 15px;
  opacity: 1;
}

.form-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.15);
}

/* 文本域 去除黑边 */
.form-textarea {
  width: 100%;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  color: #2d3748;
  font-size: 15px;
  outline: none;
  resize: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.form-textarea::placeholder {
  color: #94a3b8;
  font-size: 15px;
  opacity: 1;
}

.form-textarea:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.15);
}

/* 美化：时间选择整体容器 - 上下两行布局，高度固定不跳动 */
.time-select-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 4px 0;
}

/* 不限时间 复选框区域美化 */
.time-unlimited {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #475569;
  user-select: none;
}

.time-unlimited input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #4f46e5;
  /* 复选框主题色 */
  cursor: pointer;
  margin: 0;
}

/* 时分选择容器 - 缩小尺寸 */
.time-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  /* 小屏下允许日期与时分换行，避免横向溢出 */
  flex-wrap: wrap;
  background: #ffffff;
  padding: 4px 10px;
  /* 缩小上下+左右内边距 */
  border-radius: 8px;
  /* 缩小圆角 */
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.time-picker:hover {
  border-color: #c7d2fe;
  background: #fdfdff;
}

.time-picker:focus-within {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.15);
}

/* 美化下拉选择框（小时/分钟）+ 自定义下拉箭头 */
.time-select {
  border: none;
  outline: none;
  padding: 4px 20px 4px 6px;
  /* 缩小内边距 */
  background-color: transparent;
  font-size: 14px;
  /* 字体略微缩小 */
  color: #2d3748;
  /* 移除原生下拉箭头 */
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  /* 自定义下拉箭头 */
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 2px center;
  background-size: 10px;
  /* 缩小箭头尺寸 */
  cursor: pointer;
  min-width: 50px;
  /* 缩小最小宽度 */
}

/* 日期选择器样式：与时分选择保持视觉统一，右侧加分隔线区分日期/时间区块 */
.date-select {
  border: none;
  outline: none;
  padding: 4px 10px 4px 6px;
  margin-right: 4px;
  border-right: 1px solid #e2e8f0;
  background-color: transparent;
  font-size: 14px;
  color: #2d3748;
  font-family: inherit;
  cursor: pointer;
}

/* 冒号样式 */
.time-colon {
  font-size: 16px;
  color: #94a3b8;
  font-weight: 500;
  line-height: 1;
}

/* 统一所有表单控件字体 */
input,
textarea,
select {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif !important;
  font-size: 15px !important;
  line-height: 1.5 !important;
}

.submit-btn {
  width: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-bottom: 12px;
}

.submit-btn:hover {
  opacity: 0.9;
}

.back-normal-btn {
  width: 100%;
  background: #f1f5f9;
  color: #475569;
  border: none;
  border-radius: 8px;
  padding: 10px;
  font-size: 15px;
  cursor: pointer;
}

/* 接龙列表 */
.event-list {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.event-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 18px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(27, 110, 243, 0.25);
}

.event-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.12);
  border-color: #c7d2fe;
}

.event-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px;
  color: #1e293b;
}

.tag-group {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.tag {
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
}

.event-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 16px;
  line-height: 1.5;
}

.event-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 10px 12px;
  border-radius: 0;
  margin: 18px -18px -18px -18px;
}

.participant-count {
  font-size: 13px;
  color: #64748b;
}

.admin-op-group {
  display: flex;
  gap: 8px;
}

.edit-btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
}

.del-btn {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.del-btn:hover {
  background: #dc2626;
}

.empty-tip {
  text-align: center;
  color: #94a3b8;
  padding: 20px;
}

/* 成员管理列表样式 */
.member-panel {
  max-width: 600px;
  margin: 0 auto 24px;
}

.member-list {
  width: 100%;
}

.member-item {
  display: flex;
  align-items: center;
  padding: 10px 8px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.member-header {
  background: #f8fafc;
  font-weight: 500;
}

.m-id {
  width: 60px;
  text-align: center;
}

.m-name {
  flex: 1;
  padding: 0 8px;
}

.m-steam {
  flex: 1.2;
  padding: 0 8px;
}

.m-time {
  flex: 1.5;
  padding: 0 8px;
  font-size: 12px;
  color: #64748b;
}

.m-op {
  width: 80px;
  text-align: center;
}

/* 接龙详情页 */
.detail-page {
  max-width: 600px;
  margin: 0 auto;
}

.detail-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(27, 110, 243, 0.25);
}

.detail-title {
  font-size: 22px;
  font-weight: 600;
  padding: 0 16px;
  margin: 2px 0;
  color: #1e293b;
}

.detail-tag-group {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.detail-tag {
  background: #f1f5f9;
  color: #475569;
  font-size: 13px;
  padding: 5px 12px;
  border-radius: 6px;
}

.detail-desc-box {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.detail-desc {
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
}

.join-btn {
  width: 100%;
  background: #10b981;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 24px;
  transition: background 0.2s;
}

.join-btn:hover {
  background: #059669;
}

.signup-list {
  margin-bottom: 24px;
}

.signup-title {
  font-size: 16px;
  color: #475569;
  margin: 0 0 12px;
}

.signup-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  transition: all 0.2s;
}

.signup-index {
  width: 24px;
  height: 24px;
  background: #4f46e5;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}

.signup-name {
  font-size: 15px;
  font-weight: 500;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.me-tag {
  background: #4f46e5;
  color: #fff;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

.signup-steam {
  font-size: 13px;
  color: #64748b;
}

.quit-small-btn {
  margin-left: auto;
  background: #dc2626;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.quit-small-btn:hover {
  background: #b91c1c;
}

.back-btn {
  width: 100%;
  background: #f1f5f9;
  color: #475569;
  border: none;
  border-radius: 10px;
  padding: 14px;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
}

/* 全局盒模型 */
.app-container,
.create-card,
.form-input,
.form-textarea,
.user-input,
.save-btn,
.submit-btn {
  box-sizing: border-box;
}

/* 失效接龙卡片样式 */
.event-card.card-expired {
  background-color: #f8f9fa;
  opacity: 0.7;
  cursor: not-allowed;
}

.event-card.card-expired:hover {
  transform: none;
  box-shadow: 0 1px 3px rgba(27, 110, 243, 0.25);
}

/* 失效标签 */
.tag-expired {
  background: #fee2e2;
  color: #dc2626;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .app-container {
    padding: 0 16px 30px;
  }

  .user-bar {
    display: flex;
    flex-wrap: nowrap;
    gap: 8px;
    margin-bottom: 16px;
  }

  .user-input {
    flex: 1;
    min-width: 0;
    padding: 10px 12px;
    font-size: 15px;
    border-radius: 8px;
  }

  .save-btn {
    flex-shrink: 0;
    padding: 10px 16px;
    font-size: 15px;
    border-radius: 8px;
    white-space: nowrap;
  }

  .tab-nav {
    flex-wrap: wrap;
    row-gap: 10px;
  }

  .tab-group {
    gap: 10px;
  }

  .tab-btn {
    padding: 6px 8px;
    font-size: 14px;
  }

  .search-input {
    padding: 12px 14px;
    font-size: 15px;
  }

  .event-card {
    padding: 16px;
    margin-bottom: 12px;
  }

  .event-title {
    font-size: 18px;
    margin-bottom: 10px;
  }

  .tag-group {
    gap: 8px;
    margin-bottom: 10px;
  }

  .tag {
    padding: 4px 8px;
    font-size: 13px;
  }

  .event-desc {
    font-size: 14px;
    margin-bottom: 10px;
  }

  .event-bottom {
    margin: 16px -16px -16px -16px;
    padding: 8px 12px;
    font-size: 13px;
  }

  .create-card {
    padding: 20px 16px;
    width: 100%;
  }

  .create-title {
    font-size: 20px;
    margin-bottom: 20px;
    text-align: center;
  }

  .form-group {
    margin-bottom: 16px;
  }

  .form-label {
    font-size: 15px;
    margin-bottom: 8px;
  }

  .form-input {
    width: 100%;
    padding: 12px 14px;
    font-size: 15px;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
  }

  .form-textarea {
    width: 100%;
    padding: 12px 14px;
    font-size: 15px;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    min-height: 100px;
    resize: none;
  }

  .submit-btn {
    width: 100%;
    padding: 14px;
    font-size: 16px;
    border-radius: 8px;
  }

  .detail-card {
    padding: 16px;
  }

  .signup-item {
    padding: 10px;
  }

  .quit-small-btn {
    padding: 4px 12px;
    font-size: 13px;
  }
}
</style>