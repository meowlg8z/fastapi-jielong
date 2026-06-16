from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, Query, Form, Request, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import re
from contextlib import asynccontextmanager

# bcrypt：用于密码密文存储与验证（密码不可逆，不可查看明文）
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    print("[警告] bcrypt 未安装，密码功能不可用，请执行: pip install bcrypt")

try:
    import psycopg2
except Exception:
    psycopg2 = None

# ====================== 配置区 ======================
ADMIN_PWD = "9468543586"
USE_NEON = True
NEON_DATABASE_URL = "postgresql://neondb_owner:npg_hY06BwWglesH@ep-shy-credit-aorrn4i4-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
DB_FILE = "game_events.db"
TZ_CN = timezone(timedelta(hours=8))

# 全局调度器：仅初始化一次
scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def now_cn() -> str:
    return datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M:%S")


def now_cn_datetime() -> datetime:
    return datetime.now(TZ_CN)


# =====================================================================

# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 先添加任务（只执行一次）
    if not scheduler.get_jobs():
        scheduler.add_job(auto_check_expire_events, "interval", minutes=1)

    # 2. 判断调度器是否运行，未运行再启动
    if not scheduler.running:
        scheduler.start()
        print("定时调度器已启动")

    yield

    # 3. 服务关闭，停止调度器
    if scheduler.running:
        scheduler.shutdown()
        print("定时调度器已停止")


# 初始化 FastAPI 并直接绑定 lifespan（官方标准写法）
app = FastAPI(title="游戏组队接龙接口", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据库工具：获取连接前先确保库表结构存在，避免运行期数据库文件丢失后无法自愈
def get_db_conn():
    if USE_NEON:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(NEON_DATABASE_URL, sslmode="require")
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # PostgreSQL 侧表结构通常稳定存在，此处仅做一次轻量级建表保护（IF NOT EXISTS 开销很小）
        _create_tables(cursor)
        conn.commit()
        return conn, cursor
    else:
        # sqlite：每次取连接都先确保数据库文件与表结构存在
        # 原逻辑仅在应用启动时调用一次 init_db()，若运行期间 DB_FILE 被误删，
        # 后续所有接口都会因「表不存在」持续报错；这里改为按需自愈，
        # 任意接口（包括接龙列表刷新）触发取连接时都会自动重建数据库和表
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        _create_tables(cur)
        conn.commit()
        return conn, cur


# 建表语句集中维护：CREATE TABLE IF NOT EXISTS 本身具备幂等性，重复执行无副作用、开销极低
def _create_tables(cursor):
    """
    传入数据库游标，依次创建 users / events / signups 三张核心表（若不存在）。
    NEON(Postgres) 与 sqlite 的自增主键写法不同，需分支处理；其余字段定义保持一致。
    """
    id_type = "SERIAL PRIMARY KEY" if USE_NEON else "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS users (
        id {id_type},
        nickname TEXT NOT NULL UNIQUE,
        steam_id TEXT,
        password_hash TEXT,
        created_at TEXT
    )
    ''')
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS events (
        id {id_type},
        title TEXT NOT NULL,
        time_info TEXT,
        description TEXT,
        creator_id INTEGER,
        created_at TEXT,
        FOREIGN KEY (creator_id) REFERENCES users(id)
    )
    ''')
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS signups (
        id {id_type},
        event_id INTEGER,
        user_id INTEGER,
        created_at TEXT,
        UNIQUE(event_id, user_id),
        FOREIGN KEY (event_id) REFERENCES events(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')


# 应用启动时的建表入口：保留语义化函数名，内部委托给 _create_tables，避免重复代码
def init_db():
    if USE_NEON:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(NEON_DATABASE_URL, sslmode="require")
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            _create_tables(cursor)
            conn.commit()
        except Exception as e:
            print(f"[初始化数据库异常] {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    else:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            _create_tables(cursor)
            conn.commit()
        finally:
            conn.close()


init_db()


# ====================== 核心：时间解析 & 过期判断工具函数 ======================
def parse_event_time(time_str: str, create_time_str: str) -> datetime | None:
    """
    解析接龙时间，兼容两种格式：
    1. 新格式 "YYYY-MM-DD HH:MM"：前端可同时选择日期和时间
    2. 旧格式 "HH:MM"：历史数据仅有时分，日期取自接龙创建时间（向下兼容）
    3. "不限时间"：永久有效

    time_str: 接龙选择的时间文本
    create_time_str: 接龙创建时间（完整日期时间字符串，旧格式回填日期时使用）
    返回：带北京时区的完整时间对象；不限时间或解析失败均返回 None
    """
    if time_str == "不限时间":
        return None

    # 优先匹配新格式：YYYY-MM-DD HH:MM
    full_pattern = r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})"
    full_match = re.search(full_pattern, time_str)
    if full_match:
        year, month, day, hh, mm = full_match.groups()
        try:
            target_dt = datetime(int(year), int(month), int(day), int(hh), int(mm))
        except ValueError:
            # 日期数值非法（如2月30日等），视为解析失败
            return None
        return target_dt.replace(tzinfo=TZ_CN)

    # 兼容旧格式：仅有 HH:MM，日期取自接龙创建时间
    short_pattern = r"(\d{2}):(\d{2})"
    short_match = re.search(short_pattern, time_str)
    if not short_match:
        return None
    hh, mm = short_match.groups()
    try:
        create_dt = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None
    # 拼接 创建日期 + 接龙时分
    target_dt = create_dt.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    return target_dt.replace(tzinfo=TZ_CN)


def check_event_expire(time_info: str, create_at: str) -> tuple[bool, bool]:
    """
    返回 (is_expired:是否失效, need_delete:是否需要删除)
    规则：
    1. 不限时间 → 永久有效 (False, False)
    2. 当前时间 > 接龙时间 +1h → 失效
    3. 当前时间 > 接龙时间 +3h → 直接删除
    """
    now_dt = now_cn_datetime()
    event_dt = parse_event_time(time_info, create_at)
    if event_dt is None:
        return False, False

    delta_1h = timedelta(hours=1)
    delta_3h = timedelta(hours=3)

    if now_dt > event_dt + delta_3h:
        return True, True
    elif now_dt > event_dt + delta_1h:
        return True, False
    else:
        return False, False


# ====================== 定时任务：每分钟扫描过期接龙 ======================
def auto_check_expire_events():
    """定时任务：扫描过期接龙，超3小时自动删除"""
    conn, cursor = get_db_conn()
    try:
        # 查询所有接龙
        cursor.execute("SELECT id, time_info, created_at FROM events")
        all_events = cursor.fetchall()
        del_event_ids = []

        for row in all_events:
            e_id = row["id"]
            t_info = row["time_info"]
            c_time = row["created_at"]
            _, need_del = check_event_expire(t_info, c_time)
            if need_del:
                del_event_ids.append(e_id)

        # 批量删除
        if del_event_ids:
            ids_str = ",".join([str(x) for x in del_event_ids])
            if USE_NEON:
                cursor.execute(f"DELETE FROM signups WHERE event_id IN ({ids_str})")
                cursor.execute(f"DELETE FROM events WHERE id IN ({ids_str})")
            else:
                cursor.execute(f"DELETE FROM signups WHERE event_id IN ({ids_str})")
                cursor.execute(f"DELETE FROM events WHERE id IN ({ids_str})")
            conn.commit()
            print(f"[定时任务] 已自动删除过期接龙 ID: {del_event_ids}")
    except Exception as e:
        print(f"[定时任务异常] {e}")
        conn.rollback()
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# ====================== 数据模型 ======================
class UserInfo(BaseModel):
    nickname: str
    steam_id: str = ""        # Steam ID 可选，默认空字符串
    password: str | None = None  # 首次绑定时传密码；修改时传验证密码；无密码保护时为 None


class EventCreate(BaseModel):
    title: str
    time_info: str
    description: str
    creator_id: int


# 管理员密码校验
@app.post("/api/admin/check")
def admin_check(pwd: str = Form(...)):
    if pwd != ADMIN_PWD:
        raise HTTPException(status_code=401, detail="管理员密码错误")
    return {"code": 200, "msg": "验证成功", "is_admin": True}


# 管理员权限依赖
def admin_auth(pwd: str = Query(...)):
    if pwd != ADMIN_PWD:
        raise HTTPException(status_code=401, detail="无管理员权限")
    return True


# ====================== 管理员 - 用户管理接口 ======================
@app.get("/api/admin/users")
def get_all_users(_: bool = Depends(admin_auth)):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute("SELECT id, nickname, steam_id, created_at FROM users ORDER BY id DESC")
        else:
            cursor.execute("SELECT id, nickname, steam_id, created_at FROM users ORDER BY id DESC")
        rows = cursor.fetchall()
        return {"code": 200, "data": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


@app.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, _: bool = Depends(admin_auth)):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute("DELETE FROM signups WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("DELETE FROM signups WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return {"code": 200, "msg": "成员已删除"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# ====================== 原有接口（改造：增加过期状态、拦截报名）======================
@app.get("/health")
async def health():
    return {"status": "ok"}


# ====================== 用户接口 ======================

def hash_password(pwd: str) -> str:
    """使用 bcrypt 对密码加盐哈希，返回密文字符串（不可逆）"""
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def verify_password(pwd: str, hashed: str) -> bool:
    """验证明文密码是否与密文匹配"""
    try:
        return bcrypt.checkpw(pwd.encode(), hashed.encode())
    except Exception:
        return False


# 查询用户是否存在：支持三种查询方式（按需传参，优先级 user_id > steam_id > nickname）
# - nickname：注册/登录前检测昵称是否已占用（原有用途）
# - steam_id：绑定 Steam ID 前检测该 ID 是否已被其他账号占用
# - user_id：前端本地缓存了 user_id 后，用于反查该账号是否仍然存在于数据库
#   （例如被管理员删除后，本地缓存会变成「幽灵账号」，需要据此清理缓存）
@app.get("/api/user/check")
def check_nickname(
    nickname: str | None = Query(None),
    steam_id: str | None = Query(None),
    user_id: int | None = Query(None)
):
    # 三个查询参数至少需要传一个，否则查询条件不明确
    if not nickname and not steam_id and not user_id:
        raise HTTPException(status_code=400, detail="nickname / steam_id / user_id 至少传一个")

    conn, cursor = get_db_conn()
    try:
        # 按优先级拼接查询条件：user_id 最精确（主键），其次 steam_id，最后才是 nickname
        if user_id:
            sql = "SELECT id, nickname, steam_id, password_hash FROM users WHERE id = ?"
            param = user_id
        elif steam_id:
            sql = "SELECT id, nickname, steam_id, password_hash FROM users WHERE steam_id = ?"
            param = steam_id
        else:
            sql = "SELECT id, nickname, steam_id, password_hash FROM users WHERE nickname = ?"
            param = nickname

        if USE_NEON:
            sql = sql.replace("?", "%s")
        cursor.execute(sql, (param,))
        row = cursor.fetchone()
        if not row:
            return {"exists": False, "has_password": False}
        row = dict(row)
        return {
            "exists": True,
            "has_password": bool(row.get("password_hash")),
            "user_id": row.get("id"),
            "nickname": row.get("nickname"),
            "steam_id": row.get("steam_id") or ""
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 保存用户（新增/修改）
@app.post("/api/user")
def save_user(user: UserInfo):
    if not HAS_BCRYPT:
        raise HTTPException(status_code=500, detail="服务端缺少 bcrypt 依赖，请联系管理员")

    nick = user.nickname.strip()
    sid = user.steam_id.strip() if user.steam_id else ""
    pwd_input = user.password.strip() if user.password else None

    if not nick:
        raise HTTPException(status_code=400, detail="昵称不能为空")

    # Steam ID 非空时校验纯数字
    if sid and not re.fullmatch(r"\d+", sid):
        raise HTTPException(status_code=400, detail="Steam ID 必须为纯数字")

    conn, cursor = get_db_conn()
    try:
        # 查询该账号是否已注册：同时匹配昵称或 Steam ID（任一命中即视为老用户）
        # 原因：用户绑定 Steam ID 后昵称可自由修改，若仅按 nickname 查询，
        # 改名后会因找不到旧昵称而被误判为「新用户」，导致重复创建账号、密码保护失效
        sql_select = "SELECT id, password_hash, steam_id FROM users WHERE nickname = ? OR (steam_id != '' AND steam_id = ?)"
        if USE_NEON:
            sql_select = sql_select.replace("?", "%s")
        cursor.execute(sql_select, (nick, sid))
        row = cursor.fetchone()

        if row:
            # ===== 已注册：验证密码后允许修改 =====
            row = dict(row)
            user_id = row["id"]
            existing_hash = row.get("password_hash")
            existing_sid = row.get("steam_id") or ""

            if existing_hash:
                # 该昵称有密码保护：必须验证
                if not pwd_input:
                    return {"code": 403, "msg": "该昵称已设有密码，请输入密码后再修改"}
                if not verify_password(pwd_input, existing_hash):
                    return {"code": 403, "msg": "密码错误"}

            # 关键校验：本次操作为「首次绑定 Steam ID」（之前未绑定，本次传入非空 sid），
            # 必须同时设置密码，密码与绑定动作一一对应，杜绝出现无密码保护的绑定账号
            is_first_bind_steam = bool(sid) and not existing_sid
            if is_first_bind_steam and not pwd_input:
                return {"code": 400, "msg": "绑定 Steam ID 需同时设置密码"}

            # 首次绑定 Steam 时生成密码密文；非绑定场景密码字段保持原值不变
            new_pwd_hash = hash_password(pwd_input) if is_first_bind_steam else existing_hash

            sql_update = "UPDATE users SET nickname = ?, steam_id = ?, password_hash = ? WHERE id = ?"
            if USE_NEON:
                sql_update = sql_update.replace("?", "%s")
            try:
                cursor.execute(sql_update, (nick, sid, new_pwd_hash, user_id))
            except Exception as e:
                # nickname 字段带 UNIQUE 约束：并发场景下可能在前端查重通过后、提交更新前
                # 被他人抢先占用同一昵称，此处兜底捕获唯一性冲突，给出明确业务提示而非裸 500 错误
                is_unique_conflict = isinstance(e, sqlite3.IntegrityError) or \
                    (psycopg2 is not None and isinstance(e, psycopg2.IntegrityError))
                if is_unique_conflict:
                    conn.rollback()
                    return {"code": 400, "msg": "该昵称已被他人使用，请换一个"}
                raise
            conn.commit()
            return {"code": 200, "msg": "信息已更新", "user_id": user_id}

        else:
            # ===== 新昵称：插入记录 =====
            # 若本次注册同时绑定了 Steam ID，则强制要求设置密码（不要求二次确认密码）
            if sid and not pwd_input:
                return {"code": 400, "msg": "绑定 Steam ID 需同时设置密码"}

            pwd_hash = hash_password(pwd_input) if pwd_input else None
            if USE_NEON:
                cursor.execute(
                    "INSERT INTO users (nickname, steam_id, password_hash, created_at) VALUES (%s, %s, %s, %s)",
                    (nick, sid, pwd_hash, now_cn())
                )
                cursor.execute("SELECT LASTVAL()")
                new_id = cursor.fetchone()["lastval"]
            else:
                cursor.execute(
                    "INSERT INTO users (nickname, steam_id, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (nick, sid, pwd_hash, now_cn())
                )
                cursor.execute("SELECT last_insert_rowid()")
                new_id = cursor.fetchone()[0]
            conn.commit()
            msg = "注册成功（已设置密码保护）" if pwd_hash else "注册成功"
            return {"code": 200, "msg": msg, "user_id": new_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 获取全部接龙（新增 is_expired 失效状态）
@app.get("/api/events")
def get_all_events():
    conn, cursor = get_db_conn()
    try:
        sql = '''
        SELECT e.id, e.title, e.time_info, e.description, e.created_at,
               COUNT(s.id) as participant_num
        FROM events e
        LEFT JOIN signups s ON e.id = s.event_id
        GROUP BY e.id
        ORDER BY e.created_at DESC
        '''
        cursor.execute(sql)
        rows = cursor.fetchall()
        res_list = []
        for r in rows:
            item = dict(r)
            is_exp, _ = check_event_expire(item["time_info"], item["created_at"])
            item["is_expired"] = is_exp
            res_list.append(item)
        # 失效接龙排到列表末尾；sort为稳定排序，未失效/已失效各自内部仍保持原创建时间倒序
        res_list.sort(key=lambda x: x["is_expired"])
        return {"code": 200, "data": res_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 单条接龙（编辑回填）
@app.get("/api/events/{event_id}/single")
def get_single_event(event_id: int):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        else:
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="接龙不存在")
        item = dict(row)
        # 补充过期状态字段
        is_exp, _ = check_event_expire(item["time_info"], item["created_at"])
        item["is_expired"] = is_exp
        return {"code": 200, "data": item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 创建接龙
@app.post("/api/events/create")
def create_event(event: EventCreate):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute(
                "INSERT INTO events (title, time_info, description, creator_id, created_at) VALUES (%s, %s, %s, %s, %s)",
                (event.title, event.time_info, event.description, event.creator_id, now_cn())
            )
            cursor.execute("SELECT LASTVAL()")
            new_id = cursor.fetchone()["lastval"]
        else:
            cursor.execute(
                "INSERT INTO events (title, time_info, description, creator_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (event.title, event.time_info, event.description, event.creator_id, now_cn())
            )
            cursor.execute("SELECT last_insert_rowid()")
            new_id = cursor.fetchone()[0]
        conn.commit()
        return {"code": 200, "msg": "创建成功", "id": new_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 报名接龙（拦截：失效接龙禁止报名）
@app.post("/api/events/{event_id}/signup")
def event_signup(event_id: int, user_id: int = Query(...)):
    conn, cursor = get_db_conn()
    try:
        # 先查询接龙信息，判断是否失效
        if USE_NEON:
            cursor.execute("SELECT time_info, created_at FROM events WHERE id = %s", (event_id,))
        else:
            cursor.execute("SELECT time_info, created_at FROM events WHERE id = ?", (event_id,))
        event_row = cursor.fetchone()
        if not event_row:
            raise HTTPException(status_code=404, detail="接龙不存在")
        is_exp, _ = check_event_expire(event_row["time_info"], event_row["created_at"])
        if is_exp:
            raise HTTPException(status_code=400, detail="该接龙已失效，无法报名")

        # 正常报名
        if USE_NEON:
            cursor.execute(
                "INSERT INTO signups (event_id, user_id, created_at) VALUES (%s, %s, %s)",
                (event_id, user_id, now_cn())
            )
        else:
            cursor.execute(
                "INSERT INTO signups (event_id, user_id, created_at) VALUES (?, ?, ?)",
                (event_id, user_id, now_cn())
            )
        conn.commit()
        return {"code": 200, "msg": "报名成功"}
    except Exception as e:
        if isinstance(e, sqlite3.IntegrityError) or (psycopg2 is not None and isinstance(e, psycopg2.IntegrityError)):
            raise HTTPException(status_code=400, detail="已报名该接龙")
        conn.rollback()
        raise e
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 删除接龙
@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, _: bool = Depends(admin_auth)):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute("DELETE FROM signups WHERE event_id = %s", (event_id,))
            cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
        else:
            cursor.execute("DELETE FROM signups WHERE event_id = ?", (event_id,))
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        return {"code": 200, "msg": "删除成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 我参与的接龙（新增 is_expired）
@app.get("/api/events/my-participated")
def get_my_participated_events(user_id: int = Query(...)):
    conn, cursor = get_db_conn()
    try:
        sql = '''
        SELECT DISTINCT
            e.id, e.title, e.time_info, e.description, e.created_at,
            (SELECT COUNT(*) FROM signups s2 WHERE s2.event_id = e.id) AS participant_num
        FROM events e
        INNER JOIN signups s ON e.id = s.event_id
        WHERE s.user_id = ?
        ORDER BY e.created_at DESC
        '''
        if USE_NEON:
            sql = sql.replace("?", "%s")
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
        res_list = []
        for r in rows:
            item = dict(r)
            is_exp, _ = check_event_expire(item["time_info"], item["created_at"])
            item["is_expired"] = is_exp
            res_list.append(item)
        # 失效接龙排到列表末尾；sort为稳定排序，未失效/已失效各自内部仍保持创建时间倒序
        res_list.sort(key=lambda x: x["is_expired"])
        return {"code": 200, "data": res_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 接龙详情（新增失效状态）
@app.get("/api/events/{event_id}")
def get_event_detail(event_id: int):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute('''
                SELECT e.id, e.title, e.time_info, e.description, e.created_at,
                       COUNT(s.id) as participant_num
                FROM events e
                LEFT JOIN signups s ON e.id = s.event_id
                WHERE e.id = %s
                GROUP BY e.id
            ''', (event_id,))
        else:
            cursor.execute('''
                SELECT e.id, e.title, e.time_info, e.description, e.created_at,
                       COUNT(s.id) as participant_num
                FROM events e
                LEFT JOIN signups s ON e.id = s.event_id
                WHERE e.id = ?
                GROUP BY e.id
            ''', (event_id,))
        event_row = cursor.fetchone()
        if not event_row:
            raise HTTPException(status_code=404, detail="接龙不存在")
        event_data = dict(event_row)
        is_exp, _ = check_event_expire(event_data["time_info"], event_data["created_at"])
        event_data["is_expired"] = is_exp

        if USE_NEON:
            cursor.execute('''
                SELECT u.nickname, u.steam_id
                FROM signups s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.event_id = %s
                ORDER BY s.created_at
            ''', (event_id,))
        else:
            cursor.execute('''
                SELECT u.nickname, u.steam_id
                FROM signups s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.event_id = ?
                ORDER BY s.created_at
            ''', (event_id,))
        signups_rows = cursor.fetchall()
        return {
            "code": 200,
            "data": {
                "event": event_data,
                "signups": [dict(r) for r in signups_rows]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 退出接龙
@app.delete("/api/events/{event_id}/quit")
def quit_event(event_id: int, user_id: int = Query(...)):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute("DELETE FROM signups WHERE event_id = %s AND user_id = %s", (event_id, user_id))
        else:
            cursor.execute("DELETE FROM signups WHERE event_id = ? AND user_id = ?", (event_id, user_id))
        conn.commit()
        return {"code": 200, "msg": "退出成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 编辑接龙
@app.put("/api/events/{event_id}")
def update_event(event_id: int, event: EventCreate, _: bool = Depends(admin_auth)):
    conn, cursor = get_db_conn()
    try:
        if USE_NEON:
            cursor.execute('''
            UPDATE events 
            SET title = %s, time_info = %s, description = %s, creator_id = %s
            WHERE id = %s
            ''', (event.title, event.time_info, event.description, event.creator_id, event_id))
        else:
            cursor.execute('''
            UPDATE events 
            SET title = ?, time_info = ?, description = ?, creator_id = ?
            WHERE id = ?
            ''', (event.title, event.time_info, event.description, event.creator_id, event_id))
        conn.commit()
        return {"code": 200, "msg": "修改成功"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if USE_NEON: cursor.close()
        conn.close()


# 404兜底
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    path = request.url.path
    if path.startswith("/api"):
        raise HTTPException(status_code=404, detail="接口不存在")
    return FileResponse("dist/index.html")


# 静态资源（部署开启）
app.mount("/", StaticFiles(directory="dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)