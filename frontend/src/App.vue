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

    <!-- 用户信息栏：未保存时显示输入框，已保存时显示昵称小控件 -->
    <div class="user-bar">
      <!-- 未保存状态：仅输入昵称 -->
      <template v-if="!hasUserInfo">
        <input v-model="nicknameInput" class="user-input-short" placeholder="输入昵称" maxlength="20" name="nickname"
          @keyup.enter="saveUser" />
        <button @click="saveUser" class="save-btn">保存</button>
      </template>

      <!-- 已保存状态：显示昵称小控件，点击触发对应操作 -->
      <template v-else>
        <div class="user-chip" @click="onClickUserChip" title="点击管理账号信息">
          <span class="user-chip-avatar">{{ nickname.charAt(0).toUpperCase() }}</span>
          <span class="user-chip-name">{{ nickname }}</span>
          <span class="user-chip-badge" :class="steamId ? 'badge-bound' : 'badge-unbound'">
            {{ steamId ? '🎮 已绑定' : '未绑定 Steam' }}
          </span>
        </div>
      </template>
    </div>

    <!-- ① 新用户首次保存后：引导绑定 Steam ID（绑定时需同步设置密码，可整体跳过不绑定） -->
    <div class="modal-mask" v-if="showBindModal">
      <div class="modal-box">
        <h3 class="modal-title">🎮 绑定 Steam ID</h3>
        <p class="modal-desc">
          绑定后可在报名列表展示你的 Steam 账号，方便队友添加好友。
          <span class="modal-warn">⚠️ Steam ID 一旦绑定不可修改，绑定时需同时设置密码用于后续身份验证。</span>
        </p>
        <input v-model="bindSteamInput" class="modal-input" type="text" inputmode="numeric" name="steam_id"
          placeholder="Steam ID（纯数字，可跳过）" maxlength="30" />
        <input v-model="bindPwdInput" class="modal-input" type="password" name="password"
          placeholder="设置密码（绑定 Steam ID 后必填，至少6位）" maxlength="32" />
        <p class="modal-hint">不绑定 Steam ID，点「跳过」即可（无需设置密码）。</p>
        <div class="modal-btns">
          <button class="modal-btn modal-btn-primary" @click="confirmBind">确认绑定</button>
          <button class="modal-btn modal-btn-cancel" @click="cancelBind">跳过</button>
        </div>
      </div>
    </div>

    <!-- ② 未绑定 Steam，点击昵称弹出绑定界面（绑定时需同步设置密码，可整体跳过） -->
    <div class="modal-mask" v-if="showSteamBindModal">
      <div class="modal-box">
        <h3 class="modal-title">🎮 绑定 Steam ID</h3>
        <p class="modal-desc">
          绑定后可在报名列表展示你的 Steam 账号。
          <span class="modal-warn">⚠️ Steam ID 绑定后不可修改，绑定时需同时设置密码用于后续身份验证。</span>
        </p>
        <input v-model="bindSteamInput" class="modal-input" type="text" inputmode="numeric" name="steam_id"
          placeholder="Steam ID（纯数字）" maxlength="30" />
        <input v-model="bindPwdInput" class="modal-input" type="password" name="password" placeholder="设置密码（至少6位）"
          maxlength="32" />
        <div class="modal-btns">
          <button class="modal-btn modal-btn-primary" @click="confirmSteamBind">确认绑定</button>
          <button class="modal-btn modal-btn-cancel" @click="closeSteamBindModal">跳过</button>
        </div>
      </div>
    </div>

    <!-- ③ 已绑定 Steam，点击昵称弹出修改昵称界面（需密码） -->
    <div class="modal-mask" v-if="showEditNicknameModal">
      <div class="modal-box">
        <h3 class="modal-title">✏️ 修改昵称</h3>
        <p class="modal-desc">Steam ID 绑定后以 Steam ID 作为唯一标识，昵称可以自由修改。</p>
        <input v-model="editNicknameInput" class="modal-input" type="text" name="nickname" placeholder="新昵称" maxlength="20" />
        <input v-model="verifyPwdInput" class="modal-input" type="password" name="password" placeholder="输入密码以确认" maxlength="32" />
        <div class="modal-btns">
          <button class="modal-btn modal-btn-primary" @click="confirmEditNickname">确认修改</button>
          <button class="modal-btn modal-btn-cancel" @click="closeEditNicknameModal">取消</button>
        </div>
      </div>
    </div>

    <!-- ④ 已有账号登录验证（昵称存在且有密码时）：验证身份后登录 -->
    <div class="modal-mask" v-if="showVerifyModal">
      <div class="modal-box">
        <h3 class="modal-title">🔑 验证身份</h3>
        <p class="modal-desc">昵称「{{ nicknameInput }}」已被注册并设有密码，请输入密码登录。</p>
        <input v-model="verifyPwdInput" class="modal-input" type="password" placeholder="请输入密码" maxlength="32" name="password"
          @keyup.enter="confirmVerify" />
        <div class="modal-btns">
          <button class="modal-btn modal-btn-primary" @click="confirmVerify">验证登录</button>
          <button class="modal-btn modal-btn-cancel" @click="cancelVerify">取消</button>
        </div>
      </div>
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
        <button v-if="isAdmin" class="tab-btn" :class="{ active: activeTab === 'member' }" @click="switchTab('member')">
          👥 成员管理
        </button>
      </div>
    </div>

    <!-- 搜索框：仅接龙列表显示 -->
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

        <div class="form-group">
          <label class="form-label">⏱️组队时间</label>
          <div class="time-select-wrap">
            <!-- 第一行：不限时间复选框 -->
            <label class="time-unlimited">
              <input type="checkbox" v-model="timeUnlimited"> 不限时间
            </label>
            <!-- 第二行：日期+时分选择器；visibility保持占位，切换不跳动 -->
            <div class="time-picker" :style="{ visibility: timeUnlimited ? 'hidden' : 'visible' }">
              <input type="date" v-model="eventDate" class="date-select" :min="todayDateStr" />
              <select v-model="eventHour" class="time-select">
                <option v-for="h in Array.from({ length: 24 }, (_, i) => i)" :key="h" :value="String(h).padStart(2, '0')">
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
      <div class="event-card" v-for="item in showEventList" :key="item.id" :class="{ 'card-expired': item?.is_expired }"
        @click="!(item?.is_expired) && goToDetail(item.id)" :title="(item?.is_expired) ? '该接龙已失效' : ''">
        <h3 class="event-title">{{ item.title }}</h3>
        <div class="tag-group">
          <span class="tag">🕒 {{ item.time_info }}</span>
          <span class="tag">👥 {{ item.participant_num }}人已报名</span>
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

    <!-- 管理员 - 成员管理页面 -->
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
        <button v-if="!isJoined" class="join-btn" :class="{ 'btn-disabled': !hasUserInfo || (detailEvent?.is_expired) }"
          @click="signUpCurrentEvent">
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
import { ref, onMounted, onUnmounted, computed } from 'vue'

// ========== 键盘指令（管理员模式） ==========
const inputBuffer = ref("")
let inputTimer = null
const CMD_ADMIN = "admin"
const CMD_EXIT = "exit"
const adminPwd = ref("")

function handleKeydown(e) {
  const activeTag = document.activeElement.tagName
  if (activeTag === 'INPUT' || activeTag === 'TEXTAREA' || activeTag === 'SELECT') return
  const key = e.key
  if (key.length !== 1) return
  inputBuffer.value += key
  clearTimeout(inputTimer)
  inputTimer = setTimeout(() => { inputBuffer.value = "" }, 5000)
  if (inputBuffer.value === CMD_ADMIN) {
    const pwd = prompt("请输入管理员密码")
    if (pwd) {
      adminPwd.value = pwd
      fetch('/api/admin/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `pwd=${pwd}`
      })
        .then(res => { if (!res.ok) throw new Error(); return res.json() })
        .then(() => { isAdmin.value = true; setTip("已进入管理模式"); getMemberList() })
        .catch(() => { setTip("管理员密码错误"); adminPwd.value = "" })
    }
    inputBuffer.value = ""
    clearTimeout(inputTimer)
  } else if (inputBuffer.value === CMD_EXIT) {
    isAdmin.value = false
    adminPwd.value = ""
    setTip("已退出管理模式")
    inputBuffer.value = ""
    clearTimeout(inputTimer)
  }
  const maxLen = Math.max(CMD_ADMIN.length, CMD_EXIT.length)
  if (inputBuffer.value.length > maxLen) inputBuffer.value = inputBuffer.value.slice(-maxLen)
}

// ========== 全局提示 ==========
const showTip = ref(false)
const tipText = ref('')
function setTip(text) {
  tipText.value = text
  showTip.value = true
  setTimeout(() => { showTip.value = false }, 2500)
}

// ========== 用户信息 ==========
const nickname = ref('')        // 已保存的昵称（与后端同步）
const steamId = ref('')         // 已保存的 Steam ID（与后端同步）
const nicknameInput = ref('')   // 新用户昵称输入框
const steamIdInput = ref('')    // 兼容旧流程保留
const currentUserId = ref(0)
const userHasPassword = ref(false) // 当前用户是否已设置密码

// 有昵称 + user_id 即视为有效用户（Steam ID 可选）
const hasUserInfo = computed(() => !!nickname.value && !!currentUserId.value)

// ========== 弹窗状态 ==========
const showBindModal = ref(false)         // ① 新用户首次保存后引导绑定 Steam + 密码
const showSteamBindModal = ref(false)    // ② 已登录未绑定 Steam，点击昵称弹出
const showEditNicknameModal = ref(false) // ③ 已绑定 Steam，点击昵称修改昵称
const showVerifyModal = ref(false)       // ④ 昵称已注册且有密码，登录验证

// 各弹窗输入值
const bindPwdInput = ref('')
const bindSteamInput = ref('')
const editNicknameInput = ref('')
const verifyPwdInput = ref('')

// 待提交的数据暂存（弹窗确认后提交）
let pendingSavePayload = null

// ========== 清理本地用户缓存：回退为「未保存用户」状态 ==========
// 触发场景：检测到当前 user_id 在数据库中已不存在（如被管理员删除），
// 需要把本地缓存的登录态彻底清空，避免继续以「幽灵账号」身份操作导致后续请求全部失败
const clearLocalUserState = () => {
  nickname.value = ''
  steamId.value = ''
  currentUserId.value = 0
  userHasPassword.value = false
  nicknameInput.value = ''
  steamIdInput.value = ''
  localStorage.removeItem('nickname')
  localStorage.removeItem('steamId')
  localStorage.removeItem('userId')
}

// ========== 后台静默检测：当前登录用户是否仍存在于数据库 ==========
// 返回 true 表示用户仍然有效，可继续后续操作；返回 false 表示账号已失效（已清理本地缓存）
// 设计为「先检测、再放行」模式：用户点击昵称、提交修改昵称、提交绑定 Steam 前均需调用一次，
// 防止账号被管理员删除后，前端仍持有过期 user_id 继续发起修改请求（后端会因找不到记录而报错）
const verifyCurrentUserExists = async () => {
  if (!currentUserId.value) return false
  try {
    const res = await fetch(`/api/user/check?user_id=${currentUserId.value}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    if (!data.exists) {
      // 数据库中已查不到该用户，说明账号已被删除：清理本地缓存，回退为未保存状态
      clearLocalUserState()
      setTip('账号信息已失效，请重新保存昵称')
      return false
    }
    return true
  } catch {
    // 网络异常时不清理缓存，避免误判（仅在确认账号不存在时才清理）
    setTip('网络异常，请重试')
    return false
  }
}
// ========== 昵称控件点击：先检测账号是否仍存在，再根据绑定状态路由到不同弹窗 ==========
const onClickUserChip = async () => {
  // 后台静默检测：账号已被删除则清理缓存并中止后续弹窗逻辑
  const stillExists = await verifyCurrentUserExists()
  if (!stillExists) return

  if (!steamId.value) {
    // 未绑定 Steam → 弹出绑定引导（可跳过）
    bindSteamInput.value = ''
    showSteamBindModal.value = true
  } else {
    // 已绑定 Steam → 弹出修改昵称（需密码）
    editNicknameInput.value = nickname.value
    verifyPwdInput.value = ''
    showEditNicknameModal.value = true
  }
}

// ========== 关闭弹窗辅助 ==========
const closeSteamBindModal = () => {
  showSteamBindModal.value = false
  bindSteamInput.value = ''
  bindPwdInput.value = ''
}

const closeEditNicknameModal = () => {
  showEditNicknameModal.value = false
  editNicknameInput.value = ''
  verifyPwdInput.value = ''
}

// ========== ② 补充绑定 Steam ID（点击昵称 → 未绑定时，绑定需同步设置密码） ==========
const confirmSteamBind = async () => {
  // 提交修改前再次确认账号仍存在（防止弹窗打开期间账号被管理员删除）
  const stillExists = await verifyCurrentUserExists()
  if (!stillExists) { closeSteamBindModal(); return }

  const sid = bindSteamInput.value.trim()
  const pwd = bindPwdInput.value.trim()
  if (!sid) { setTip('请输入 Steam ID'); return }
  if (!/^\d+$/.test(sid)) { setTip('Steam ID 必须为纯数字'); return }
  // 绑定 Steam ID 必须同步设置密码，且无需二次输入确认
  if (!pwd) { setTip('请设置密码（绑定 Steam ID 后需用密码验证身份）'); return }
  if (pwd.length < 6) { setTip('密码至少6位'); return }

  // 前端先检查 Steam ID 是否已被占用
  try {
    const res = await fetch(`/api/user/check?steam_id=${encodeURIComponent(sid)}`)
    const data = await res.json()
    if (data.exists) { setTip('该 Steam ID 已被其他账号绑定'); return }
  } catch { setTip('网络异常，请重试'); return }

  // Steam ID 通过检测，提交绑定（携带密码，后端写入密文）
  await doSaveUser({ nickname: nickname.value, steam_id: sid }, pwd)
  closeSteamBindModal()
}

// ========== ③ 修改昵称（已绑定 Steam，密码验证通过后才能改） ==========
const confirmEditNickname = async () => {
  // 提交修改前再次确认账号仍存在（防止弹窗打开期间账号被管理员删除）
  const stillExists = await verifyCurrentUserExists()
  if (!stillExists) { closeEditNicknameModal(); return }

  const newNick = editNicknameInput.value.trim()
  const pwd = verifyPwdInput.value.trim()
  if (!newNick) { setTip('昵称不能为空'); return }
  if (newNick === nickname.value) { setTip('昵称与当前相同'); return }
  if (!pwd) { setTip('请输入密码'); return }

  // 检查新昵称是否与他人重复（绑定了 Steam ID 的用户以 Steam ID 为标识，昵称允许重复吗？
  // 根据需求：有重复的昵称要提示并阻止——统一阻止昵称重复）
  try {
    const res = await fetch(`/api/user/check?nickname=${encodeURIComponent(newNick)}`)
    const data = await res.json()
    // 如果该昵称已存在且不是自己的账号，则阻止
    if (data.exists && data.user_id !== currentUserId.value) {
      setTip('该昵称已被他人使用，请换一个')
      return
    }
  } catch { setTip('网络异常，请重试'); return }

  // 用以 Steam ID 为标识提交修改，后端用密码验证
  await doSaveUser({ nickname: newNick, steam_id: steamId.value }, pwd)
  closeEditNicknameModal()
}

// ========== ① 新用户首次保存后绑定弹窗：跳过 ==========
const cancelBind = async () => {
  showBindModal.value = false
  bindSteamInput.value = ''
  bindPwdInput.value = ''
  // 跳过：仅以昵称注册，不绑定 Steam 和密码
  if (pendingSavePayload) {
    await doSaveUser(pendingSavePayload, null)
    pendingSavePayload = null
  }
}

// ========== ① 新用户首次保存后绑定弹窗：确认绑定 ==========
const confirmBind = async () => {
  const sid = bindSteamInput.value.trim()
  const pwd = bindPwdInput.value.trim()

  // Steam ID 格式校验（选填）
  if (sid && !/^\d+$/.test(sid)) { setTip('Steam ID 必须为纯数字'); return }
  // 关键校验：一旦填写 Steam ID（即执行绑定），密码必须设置，且长度需达标
  if (sid && !pwd) { setTip('绑定 Steam ID 需同时设置密码'); return }
  if (pwd && pwd.length < 6) { setTip('密码至少6位'); return }

  // Steam ID 重复检测
  if (sid) {
    try {
      const res = await fetch(`/api/user/check?steam_id=${encodeURIComponent(sid)}`)
      const data = await res.json()
      if (data.exists) { setTip('该 Steam ID 已被其他账号绑定'); return }
    } catch { setTip('网络异常，请重试'); return }
  }

  showBindModal.value = false
  bindSteamInput.value = ''
  bindPwdInput.value = ''

  if (pendingSavePayload) {
    const payload = { ...pendingSavePayload, steam_id: sid }
    // 仅在绑定了 Steam ID 时才提交密码；未绑定则不设密码
    await doSaveUser(payload, sid ? pwd : null)
    pendingSavePayload = null
  }
}

// ========== ④ 已注册且有密码的昵称：验证密码后登录 ==========
const cancelVerify = () => {
  showVerifyModal.value = false
  verifyPwdInput.value = ''
  pendingSavePayload = null
}

const confirmVerify = async () => {
  const pwd = verifyPwdInput.value.trim()
  if (!pwd) { setTip('请输入密码'); return }
  showVerifyModal.value = false
  verifyPwdInput.value = ''
  if (pendingSavePayload) {
    await doSaveUser(pendingSavePayload, pwd)
    pendingSavePayload = null
  }
}

// ========== 保存用户入口（新用户首次注册 / 已有账号登录） ==========
const saveUser = async () => {
  const nick = nicknameInput.value.trim()
  if (!nick) { setTip('昵称不能为空'); return }

  try {
    const res = await fetch(`/api/user/check?nickname=${encodeURIComponent(nick)}`)
    const data = await res.json()

    if (data.exists) {
      if (data.has_password) {
        // 昵称已注册且有密码 → 验证身份后登录
        pendingSavePayload = { nickname: nick, steam_id: data.steam_id || '' }
        showVerifyModal.value = true
      } else {
        // 昵称已注册无密码 → 直接登录（兼容历史无密码账号）
        await doSaveUser({ nickname: nick, steam_id: data.steam_id || '' }, null)
      }
    } else {
      // 全新昵称 → 先保存，再弹出 Steam 绑定引导
      pendingSavePayload = { nickname: nick, steam_id: '' }
      showBindModal.value = true
    }
  } catch {
    setTip('网络异常，请重试')
  }
}

// ========== 实际提交保存请求 ==========
const doSaveUser = async (payload, pwd) => {
  try {
    const body = { ...payload }
    if (pwd) body.password = pwd  // 后端用 bcrypt 存储密文

    const res = await fetch('/api/user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    if (data.code !== 200) {
      setTip(data.msg || '保存失败')
      return
    }
    // 同步本地状态
    currentUserId.value = Number(data.user_id)
    nickname.value = payload.nickname
    steamId.value = payload.steam_id || ''
    if (pwd) userHasPassword.value = true
    nicknameInput.value = payload.nickname
    steamIdInput.value = payload.steam_id || ''
    localStorage.setItem('nickname', payload.nickname)
    localStorage.setItem('steamId', payload.steam_id || '')
    localStorage.setItem('userId', String(currentUserId.value))
    setTip(data.msg || '保存成功')
  } catch {
    setTip('保存失败，请重试')
  }
}

// ========== 搜索、页面状态 ==========
const searchKeyword = ref('')
const currentPage = ref('list')
const activeTab = ref('list')

// ========== 时间选择相关变量 ==========
// 获取北京时间（UTC+8）当天日期字符串，格式 YYYY-MM-DD
const getBeijingDateStr = () => {
  const now = new Date()
  const beijingMs = now.getTime() + (8 * 60 + now.getTimezoneOffset()) * 60 * 1000
  const d = new Date(beijingMs)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const todayDateStr = getBeijingDateStr()
const timeUnlimited = ref(true)
const eventDate = ref(getBeijingDateStr())
const eventHour = ref("00")
const eventMinute = ref("00")

// ========== 发起/编辑接龙表单 ==========
const eventTitle = ref('')
const eventDesc = ref('')
const isEditMode = ref(false)
const editEventId = ref(null)

// ========== 管理员状态 ==========
const isAdmin = ref(false)

// ========== 列表数据 ==========
const eventList = ref([])
const myEventList = ref([])
const memberList = ref([])

// 列表搜索过滤
const showEventList = computed(() => {
  const baseList = activeTab.value === 'my' ? myEventList.value : eventList.value
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return baseList
  return baseList.filter(item =>
    item.title.toLowerCase().includes(keyword) ||
    (item.description || '').toLowerCase().includes(keyword)
  )
})

// ========== 详情数据 ==========
const currentEventId = ref(null)
const detailEvent = ref({})
const detailSignups = ref([])
const isJoined = ref(false)

// ========== 生命周期 ==========
onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  const localNick = localStorage.getItem('nickname')
  const localSteam = localStorage.getItem('steamId')
  const localUid = localStorage.getItem('userId')
  if (localNick) {
    nickname.value = localNick
    nicknameInput.value = localNick
  }
  if (localSteam) {
    steamId.value = localSteam
    steamIdInput.value = localSteam
  }
  if (localUid) currentUserId.value = Number(localUid)

  // 恢复时查询该昵称是否已设置密码，用于后续弹窗判断
  if (localNick) {
    try {
      const res = await fetch(`/api/user/check?nickname=${encodeURIComponent(localNick)}`)
      const data = await res.json()
      if (data.exists && data.has_password) userHasPassword.value = true
    } catch { /* 网络失败忽略，不影响主流程 */ }
  }

  getEventList()
})
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  clearTimeout(inputTimer)
})

// ========== 标签切换 ==========
const switchTab = (tab) => {
  if (tab === 'create' && !hasUserInfo.value) {
    setTip('请先保存昵称'); return
  }
  activeTab.value = tab
  currentPage.value = ''
  isEditMode.value = false
  editEventId.value = null
  searchKeyword.value = ''
  resetEventForm()
  if (tab === 'my') getMyEventList()
  else if (tab === 'member') getMemberList()
  else getEventList()
}

// ========== 表单操作 ==========
const resetEventForm = () => {
  eventTitle.value = ''
  eventDesc.value = ''
  timeUnlimited.value = true
  eventDate.value = getBeijingDateStr()
  eventHour.value = "00"
  eventMinute.value = "00"
}

// 拼接最终时间文本
const getTimeInfo = () => {
  if (timeUnlimited.value) return "不限时间"
  return `${eventDate.value} ${eventHour.value}:${eventMinute.value}`
}

// 编辑回填
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
    const timeStr = item.time_info || ""
    if (timeStr === "不限时间") {
      timeUnlimited.value = true
      eventDate.value = getBeijingDateStr()
      eventHour.value = "00"
      eventMinute.value = "00"
    } else {
      timeUnlimited.value = false
      const fullMatch = timeStr.match(/(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})/)
      if (fullMatch) {
        eventDate.value = fullMatch[1]
        eventHour.value = fullMatch[2]
        eventMinute.value = fullMatch[3]
      } else {
        const shortMatch = timeStr.match(/(\d{2}):(\d{2})/)
        eventDate.value = getBeijingDateStr()
        eventHour.value = shortMatch ? shortMatch[1] : "00"
        eventMinute.value = shortMatch ? shortMatch[2] : "00"
      }
    }
    activeTab.value = 'create'
    currentPage.value = ''
  } catch {
    setTip("加载编辑内容失败")
  }
}

const cancelEdit = () => {
  isEditMode.value = false
  editEventId.value = null
  resetEventForm()
  activeTab.value = 'list'
}

// ========== 提交接龙 ==========
const submitEvent = async () => {
  if (!hasUserInfo.value) { setTip('请先保存昵称'); return }
  if (!eventTitle.value) { setTip('请填写接龙标题'); return }
  if (!timeUnlimited.value && !eventDate.value) { setTip('请选择组队日期'); return }
  const finalTime = getTimeInfo()
  try {
    if (isEditMode.value) {
      await fetch(`/api/events/${editEventId.value}?pwd=${adminPwd.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: eventTitle.value, time_info: finalTime,
          description: eventDesc.value, creator_id: Number(currentUserId.value)
        })
      })
      setTip('修改成功')
    } else {
      const createRes = await fetch('/api/events/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: eventTitle.value, time_info: finalTime,
          description: eventDesc.value, creator_id: Number(currentUserId.value)
        })
      })
      const createData = await createRes.json()
      await fetch(`/api/events/${createData.id}/signup?user_id=${Number(currentUserId.value)}`, { method: 'POST' })
      setTip('接龙创建成功，已自动加入')
    }
    resetEventForm()
    isEditMode.value = false
    editEventId.value = null
    activeTab.value = 'list'
    getEventList()
  } catch {
    setTip('操作失败')
  }
}

// ========== 数据加载 ==========
const getEventList = async () => {
  try {
    const res = await fetch('/api/events')
    if (!res.ok) throw new Error()
    const data = await res.json()
    eventList.value = Array.isArray(data.data) ? data.data : []
  } catch { setTip('获取列表失败') }
}

const getMyEventList = async () => {
  if (!currentUserId.value) { setTip('请先保存昵称'); myEventList.value = []; return }
  try {
    const res = await fetch(`/api/events/my-participated?user_id=${currentUserId.value}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    myEventList.value = Array.isArray(data.data) ? data.data : []
  } catch { setTip('获取我的接龙失败') }
}

const getMemberList = async () => {
  try {
    const res = await fetch(`/api/admin/users?pwd=${adminPwd.value}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    memberList.value = Array.isArray(data.data) ? data.data : []
  } catch { setTip('获取成员列表失败'); memberList.value = [] }
}

const deleteMember = async (uid) => {
  if (!confirm("确定删除该成员？")) return
  try {
    await fetch(`/api/admin/users/${uid}?pwd=${adminPwd.value}`, { method: "DELETE" })
    setTip("成员删除成功"); getMemberList()
  } catch { setTip("删除失败") }
}

// ========== 详情 / 报名 / 退出 ==========
const goToDetail = async (eventId) => {
  detailEvent.value = {}; detailSignups.value = []; isJoined.value = false
  currentEventId.value = eventId
  try {
    const res = await fetch(`/api/events/${eventId}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    detailEvent.value = data.data.event || {}
    detailSignups.value = Array.isArray(data.data.signups) ? data.data.signups : []
    isJoined.value = detailSignups.value.some(u => u.nickname === nickname.value && u.steam_id === steamId.value)
    currentPage.value = 'detail'
  } catch { setTip('加载详情失败'); detailSignups.value = [] }
}

const signUpCurrentEvent = async () => {
  if (!hasUserInfo.value) { setTip('请先保存昵称'); return }
  if (!currentEventId.value) return
  try {
    await fetch(`/api/events/${currentEventId.value}/signup?user_id=${Number(currentUserId.value)}`, { method: 'POST' })
    setTip('报名成功'); goToDetail(currentEventId.value)
  } catch (err) { setTip(err?.message || '报名失败') }
}

const quitEvent = async () => {
  if (!hasUserInfo.value || !currentEventId.value || !currentUserId.value) return
  try {
    await fetch(`/api/events/${currentEventId.value}/quit?user_id=${Number(currentUserId.value)}`, { method: 'DELETE' })
    setTip('已退出接龙'); goToDetail(currentEventId.value); getEventList()
  } catch { setTip('退出失败') }
}

const goBackToList = () => {
  currentPage.value = ''; currentEventId.value = null; detailEvent.value = {}; detailSignups.value = []
  if (activeTab.value === 'list') getEventList()
  else if (activeTab.value === 'my') getMyEventList()
  else if (activeTab.value === 'member') getMemberList()
}

const deleteEvent = async (eventId) => {
  try {
    await fetch(`/api/events/${eventId}?pwd=${adminPwd.value}`, { method: 'DELETE' })
    setTip('删除成功'); getEventList()
  } catch { setTip('删除失败') }
}
</script>

<style scoped>
/* ===== 全局容器：铺满屏幕 ===== */
* {
  box-sizing: border-box;
}

.app-container {
  background-color: #f5f7fa;
  min-height: 100vh;
  width: 100%;
  padding: 0 0 40px;
  /* 左右不加padding，由内部子元素居中控制宽度 */
  color: #2d3748;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  position: relative;
}

/* ===== 禁用态 ===== */
.btn-disabled {
  opacity: 0.5 !important;
  pointer-events: none !important;
  cursor: not-allowed !important;
}

/* ===== 全局提示 ===== */
.tip-box {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #4f46e5;
  color: #fff;
  padding: 8px 20px;
  border-radius: 8px;
  z-index: 9999;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  white-space: nowrap;
}

.tip-box.show {
  opacity: 1;
}

/* ===== 顶部标题：铺满宽度 ===== */
.header {
  text-align: center;
  padding: 28px 0 20px;
  background: linear-gradient(180deg, #eef2ff 0%, transparent 100%);
  width: 100%;
  margin-bottom: 20px;
}

.header-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.header-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 4px;
  color: #1e293b;
}

.header-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

/* ===== 内容宽度统一约束（居中布局） ===== */
.user-bar,
.tab-nav,
.search-bar,
.create-panel,
.event-list,
.member-panel,
.detail-page {
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
  padding-left: 16px;
  padding-right: 16px;
}

/* ===== 用户信息栏：整体水平居中（未登录态输入框、已登录态昵称标签均居中展示） ===== */
.user-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
  justify-content: center;
}

/* 未登录态：短昵称输入框（约120px，不撑满整行） */
.user-input-short {
  width: 120px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  color: #2d3748;
  outline: none;
  transition: border 0.2s, box-shadow 0.2s;
  font-size: 14px;
}

.user-input-short:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.13);
}

/* 兼容旧样式引用（保留以防其他地方使用） */
.user-input {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  color: #2d3748;
  outline: none;
  transition: border 0.2s, box-shadow 0.2s;
  font-size: 14px;
}

.user-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.13);
}

/* 已登录态：昵称小控件 */
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 24px;
  padding: 5px 12px 5px 6px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  user-select: none;
  max-width: 100%;
}

.user-chip:hover {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
}

/* 头像字母圆圈 */
.user-chip-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 昵称文字 */
.user-chip-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 状态徽标 */
.user-chip-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 10px;
  flex-shrink: 0;
  font-weight: 500;
}

.badge-bound {
  background: #d1fae5;
  color: #065f46;
}

.badge-unbound {
  background: #fef3c7;
  color: #92400e;
}

/* 弹窗内小提示文字 */
.modal-hint {
  font-size: 12px;
  color: #94a3b8;
  margin: -4px 0 12px;
  line-height: 1.5;
}

/* 弹窗内不可修改警告（内联显示在描述段落中） */
.modal-warn {
  display: block;
  margin-top: 6px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 500;
}

.save-btn {
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  flex-shrink: 0;
  transition: background 0.2s;
}

.save-btn:hover {
  background: #4338ca;
}

/* ===== 弹窗遮罩 ===== */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-box {
  background: #fff;
  border-radius: 14px;
  padding: 28px 24px 22px;
  width: 100%;
  max-width: 360px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
}

.modal-title {
  font-size: 17px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 10px;
}

.modal-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 16px;
  line-height: 1.6;
}

.modal-desc strong {
  color: #dc2626;
}

.modal-input {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  color: #2d3748;
  outline: none;
  margin-bottom: 12px;
  transition: border 0.2s, box-shadow 0.2s;
}

.modal-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.13);
}

.modal-btns {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.modal-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.modal-btn:hover {
  opacity: 0.85;
}

.modal-btn-primary {
  background: #4f46e5;
  color: #fff;
}

.modal-btn-cancel {
  background: #f1f5f9;
  color: #64748b;
}

/* ===== 导航栏 ===== */
.tab-nav {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0;
}

.tab-group {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  width: 100%;
}

.tab-btn {
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 14px;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-btn.active {
  color: #4f46e5;
  border-bottom-color: #4f46e5;
}

.tab-btn:hover {
  color: #4f46e5;
}

/* ===== 搜索框 ===== */
.search-bar {
  margin-bottom: 16px;
}

.search-input {
  width: 100%;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 16px;
  color: #2d3748;
  outline: none;
  font-size: 14px;
  transition: border 0.2s, box-shadow 0.2s;
}

.search-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.13);
}

/* ===== 发起/编辑面板 ===== */
.create-panel {
  margin-bottom: 20px;
}

.create-card {
  background: #fff;
  border-radius: 12px;
  padding: 22px 18px;
  border: 1px solid #e2e8f0;
}

.create-title {
  color: #1e293b;
  font-size: 18px;
  font-weight: 600;
  text-align: center;
  margin: 0 0 18px;
}

.form-group {
  margin-bottom: 14px;
}

.form-label {
  display: block;
  color: #475569;
  font-size: 13px;
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  color: #2d3748;
  font-size: 14px;
  outline: none;
  transition: border 0.2s, box-shadow 0.2s;
}

.form-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.13);
}

.form-textarea {
  width: 100%;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  color: #2d3748;
  font-size: 14px;
  outline: none;
  resize: none;
  transition: border 0.2s, box-shadow 0.2s;
}

.form-textarea:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.13);
}

/* ===== 时间选择 ===== */
.time-select-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 2px 0;
}

.time-unlimited {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #475569;
  user-select: none;
}

.time-unlimited input[type="checkbox"] {
  width: 15px;
  height: 15px;
  accent-color: #4f46e5;
  cursor: pointer;
  margin: 0;
}

/* 日期+时分整体容器：宽度收紧，不撑满 */
.time-picker {
  display: inline-flex;
  /* inline-flex 自适应内容宽度，不拉伸 */
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  background: #fff;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  transition: border 0.2s, box-shadow 0.2s;
}

.time-picker:hover {
  border-color: #c7d2fe;
}

.time-picker:focus-within {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.13);
}

/* 日期选择器：宽度固定，右侧加分隔线 */
.date-select {
  border: none;
  outline: none;
  padding: 2px 6px;
  padding-right: 10px;
  border-right: 1px solid #e2e8f0;
  background: transparent;
  font-size: 13px;
  color: #2d3748;
  font-family: inherit;
  cursor: pointer;
  width: 120px;
  /* 固定宽度，避免不同浏览器撑开不一致 */
}

/* 时分下拉框 */
.time-select {
  border: none;
  outline: none;
  padding: 2px 18px 2px 4px;
  background: transparent;
  font-size: 13px;
  color: #2d3748;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 2px center;
  background-size: 10px;
  cursor: pointer;
  min-width: 44px;
}

.time-colon {
  font-size: 15px;
  color: #94a3b8;
  font-weight: 500;
  line-height: 1;
}

/* ===== 提交/返回按钮 ===== */
.submit-btn {
  width: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  margin-bottom: 10px;
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
  font-size: 14px;
  cursor: pointer;
}

/* ===== 接龙列表 ===== */
.event-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.event-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(27, 110, 243, 0.15);
}

.event-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.12);
  border-color: #c7d2fe;
}

.event-title {
  font-size: 17px;
  font-weight: 600;
  margin: 0 0 10px;
  color: #1e293b;
}

.tag-group {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.tag {
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 6px;
}

.tag-expired {
  background: #fee2e2;
  color: #dc2626;
}

.event-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 14px;
  line-height: 1.5;
}

.event-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 8px 12px;
  margin: 0 -16px -16px;
  border-top: 1px solid #f1f5f9;
}

.participant-count {
  font-size: 12px;
  color: #94a3b8;
}

.admin-op-group {
  display: flex;
  gap: 6px;
}

.edit-btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.edit-btn:hover {
  background: #2563eb;
}

.del-btn {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
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
  padding: 40px 0;
  font-size: 14px;
}

/* ===== 失效接龙 ===== */
.event-card.card-expired {
  background: #f8f9fa;
  opacity: 0.7;
  cursor: not-allowed;
}

.event-card.card-expired:hover {
  transform: none;
  box-shadow: 0 1px 3px rgba(27, 110, 243, 0.1);
}

/* ===== 成员管理 ===== */
.member-panel {
  margin-bottom: 20px;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
}

.member-header {
  background: #f1f5f9;
  font-weight: 600;
  color: #1e293b;
  border-radius: 8px;
}

.member-item:not(.member-header) {
  background: #f8fafc;
}

.m-id {
  width: 32px;
  flex-shrink: 0;
}

.m-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-steam {
  flex: 1.5;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-time {
  flex: 1.5;
  min-width: 0;
  font-size: 12px;
  color: #94a3b8;
}

.m-op {
  width: 52px;
  flex-shrink: 0;
}

/* ===== 详情页 ===== */
.detail-page {
  margin-bottom: 20px;
}

.detail-card {
  background: #fff;
  border-radius: 12px;
  padding: 22px 18px;
  border: 1px solid #e2e8f0;
}

.detail-title {
  font-size: 20px;
  font-weight: 600;
  padding: 0 0 14px;
  margin: 0;
  color: #1e293b;
  border-bottom: 1px solid #f1f5f9;
}

.detail-tag-group {
  display: flex;
  gap: 8px;
  margin: 14px 0;
  flex-wrap: wrap;
}

.detail-tag {
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
}

.detail-desc-box {
  background: #f8fafc;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 20px;
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
  padding: 13px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 20px;
  transition: background 0.2s;
}

.join-btn:hover {
  background: #059669;
}

.signup-list {
  margin-bottom: 20px;
}

.signup-title {
  font-size: 15px;
  color: #475569;
  margin: 0 0 10px;
}

.signup-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 6px;
}

.signup-index {
  width: 22px;
  height: 22px;
  background: #4f46e5;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.signup-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.me-tag {
  background: #4f46e5;
  color: #fff;
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 4px;
}

.signup-steam {
  font-size: 12px;
  color: #94a3b8;
  flex: 1;
}

.quit-small-btn {
  margin-left: auto;
  background: #dc2626;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
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
  padding: 12px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
}

/* ===== 统一字体 ===== */
input,
textarea,
select {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* ===== 移动端适配 ===== */
@media (max-width: 480px) {
  .tab-btn {
    padding: 8px 8px;
    font-size: 13px;
  }

  .date-select {
    width: 108px;
    font-size: 12px;
  }

  .time-select {
    font-size: 12px;
    min-width: 38px;
  }

  .modal-box {
    padding: 22px 16px 18px;
  }
}
</style>