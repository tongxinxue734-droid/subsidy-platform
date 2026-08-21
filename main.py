# -*- coding: utf-8 -*-
"""FastAPI 后端 —— 西安市高龄补贴监管平台"""
from typing import Optional

import bcrypt
import jwt
import time
import secrets
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

import db
import seed
import config
from models import (User, Elder, PaymentRecord, Notice, CertifyRecord, ElderPayment,
                    Application, ElderChange, WorkOrder, CompareTask, AuditLog, Message,
                    SpotCheck, SpotCheckRecord)

# ---------------- 初始化数据 ----------------
db.init_db()
_session = db.get_session()
try:
    seed.seed_all(_session)
finally:
    _session.close()

app = FastAPI(title=config.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---------------- 依赖 ----------------
def get_db():
    s = db.get_session()
    try:
        yield s
    finally:
        s.close()


def get_current_user(authorization: Optional[str] = Header(default=None),
                     s: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    try:
        payload = jwt.decode(authorization[7:], config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        uid = int(payload.get("sub", ""))
    except Exception:
        raise HTTPException(401, "登录态无效或已过期")
    user = s.query(User).get(uid)
    if not user or not user.active:
        raise HTTPException(401, "账号无效或已停用")
    return user


def elder_scope(s: Session, user: User):
    q = s.query(Elder)
    if user.role_level == 3:
        q = q.filter(Elder.street == user.street)
    elif user.role_level == 2:
        q = q.filter(Elder.district == user.district)
    return q


def pay_scope(s: Session, user: User):
    q = s.query(PaymentRecord)
    if user.role_level >= 2:
        q = q.filter(PaymentRecord.district == user.district)
    return q


def archive_no(district: str, eid: int) -> str:
    """生成业务档案号：区划代码-流水号，如 610113-000123"""
    code = config.DISTRICT_CODES.get(district, "610100")
    return f"{code}-{eid:06d}"


def certify_scope(s: Session, user: User):
    """认证记录按管辖范围过滤（join 老人档案）"""
    q = s.query(CertifyRecord).join(Elder, CertifyRecord.elder_id == Elder.id)
    if user.role_level == 3:
        q = q.filter(Elder.street == user.street)
    elif user.role_level == 2:
        q = q.filter(Elder.district == user.district)
    return q


def log_action(s: Session, user: User, action: str, target: str = ""):
    """写入操作审计日志"""
    role = {1: "市级", 2: "区县", 3: "街道"}.get(user.role_level, "用户")
    s.add(AuditLog(user_name=user.name, role=role, action=action, target=target))


# ---------------- 请求模型 ----------------
class LoginRequest(BaseModel):
    username: str
    password: str


class ApplyRequest(BaseModel):
    district: str
    street: str = ""
    gender: str
    age_band: str
    channel: str = ""
    id_card: str = ""
    phone: str = ""
    address: str = ""
    bank_card: str = ""
    remark: str = ""


# ---------------- 认证 ----------------
@app.post("/api/login")
def login(req: LoginRequest, s: Session = Depends(get_db)):
    u = s.query(User).filter(User.username == req.username, User.active == True).first()
    if not u:
        raise HTTPException(401, "账号或密码错误")
    try:
        ok = bcrypt.checkpw(req.password.encode("utf-8"), u.password_hash.encode("utf-8"))
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(401, "账号或密码错误")
    return {
        "token": jwt.encode({"sub": str(u.id), "exp": int(time.time()) + config.JWT_EXPIRE_HOURS * 3600}, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM),
        "user": {"id": u.id, "name": u.name, "role_level": u.role_level,
                 "district": u.district, "street": u.street, "dept_name": u.dept_name},
    }


# ---------------- 常量 / 标准 ----------------
@app.get("/api/standards")
def standards():
    return {
        "standards": config.SUBSIDY_STANDARDS,
        "channels": config.APPLY_CHANNELS,
        "fund_sources": config.FUND_SOURCES,
        "city_stats": config.CITY_STATS,
        "split_groups": config.FUND_SPLIT_GROUPS,
        "rectifications": config.RECTIFICATIONS,
        "policies": config.POLICIES,
        "apply_steps": config.APPLY_STEPS,
        "certify_rules": config.CERTIFY_RULES,
        "districts": config.DISTRICTS,
        "streets": config.STREETS,
    }


# ---------------- 驾驶舱 ----------------
@app.get("/api/dashboard")
def dashboard(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    eq = elder_scope(s, user)
    pq = pay_scope(s, user)

    total_elders = eq.count()
    certified = eq.filter(Elder.certify_status == "已认证").count()
    cert_rate = round(certified / total_elders * 100, 1) if total_elders else 0
    total_amount = pq.with_entities(func.sum(PaymentRecord.amount)).scalar() or 0
    latest_month = pq.with_entities(func.max(PaymentRecord.pay_month)).scalar() or ""
    latest_amount = pq.filter(PaymentRecord.pay_month == latest_month).with_entities(
        func.sum(PaymentRecord.amount)).scalar() or 0

    red = eq.filter(Elder.suspect_type.in_(["疑似冒领", "重复领取"])).count()
    orange = eq.filter(Elder.certify_status == "认证过期").count()
    yellow = eq.filter(Elder.suspect_type == "信息异常").count()

    trend = pq.with_entities(PaymentRecord.pay_month, func.sum(PaymentRecord.amount).label("amt")) \
        .group_by(PaymentRecord.pay_month).order_by(PaymentRecord.pay_month).all()
    age_rows = eq.with_entities(Elder.age_band, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.age_band).all()
    district_rows = eq.with_entities(Elder.district, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.district).order_by(func.count(Elder.id).desc()).all()

    return {
        "kpi": {
            "total_amount": round(total_amount, 0), "latest_amount": round(latest_amount, 0),
            "latest_month": latest_month, "total_elders": total_elders, "cert_rate": cert_rate,
            "beneficiary_count": config.CITY_BENEFICIARIES,
        },
        "alerts": {"red": red, "orange": orange, "yellow": yellow, "total": red + orange + yellow},
        "trend": [{"month": m, "amount": round(a, 1)} for m, a in trend],
        "age_structure": [{"name": a, "value": c} for a, c in age_rows],
        "district_dist": [{"name": d, "value": c} for d, c in district_rows],
    }


# ---------------- 老人档案 ----------------
@app.get("/api/elders")
def elders(district: str = Query(""), street: str = Query(""), age: str = Query(""),
           certify: str = Query(""),
           suspect: str = Query(""), page: int = Query(1), page_size: int = Query(20),
           user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    q = elder_scope(s, user)
    if district:
        q = q.filter(Elder.district == district)
    if street:
        q = q.filter(Elder.street == street)
    if age:
        q = q.filter(Elder.age_band == age)
    if certify:
        q = q.filter(Elder.certify_status == certify)
    if suspect:
        if suspect == "无":
            q = q.filter(Elder.suspect_type == "")
        else:
            q = q.filter(Elder.suspect_type == suspect)

    total = q.count()
    rows = q.order_by(Elder.id).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "id": r.id, "archive_no": archive_no(r.district, r.id),
        "district": r.district, "street": r.street, "name": r.name, "gender": r.gender,
        "age_band": r.age_band, "standard": r.standard, "id_card": r.id_card,
        "phone": r.phone, "status": r.status, "certify_status": r.certify_status,
        "suspect_type": r.suspect_type,
    } for r in rows]
    return {"total": total, "items": items, "page": page, "page_size": page_size}


@app.post("/api/elders/apply")
def apply(req: ApplyRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    import random
    from services.mask import mask_name, mask_id_card, mask_phone, mask_bank_card, mask_address
    standard = next((x["补贴标准"] for x in config.SUBSIDY_STANDARDS if x["年龄段"] == req.age_band), "50 元/月")
    district = req.district if user.role_level == 1 else user.district
    street = user.street if user.role_level == 3 else req.street
    channel = req.channel or "线上小程序"
    # 市级/区县账号直接进入区县审批，街道账号需先街道审核
    status = "待区县审批" if user.role_level in (1, 2) else "待街道审核"
    apply_no = "SQ" + datetime.now().strftime("%Y%m%d") + str(secrets.randbelow(100000)).zfill(5)
    s.add(Application(apply_no=apply_no, district=district, street=street,
                      name=mask_name(req.gender), gender=req.gender,
                      age_band=req.age_band, standard=standard, channel=channel,
                      id_card=req.id_card or mask_id_card(),
                      phone=req.phone or mask_phone(),
                      address=mask_address(district),
                      bank_card=req.bank_card or mask_bank_card(),
                      remark=req.remark, status=status, elder_id=0))
    log_action(s, user, "提交申领", apply_no)
    s.commit()
    return {"ok": True, "apply_no": apply_no, "message": "申领已提交，进入审核流程"}


@app.post("/api/elders/certify")
def certify(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    q = elder_scope(s, user).filter(Elder.certify_status.in_(["待认证", "认证过期"]))
    ids = [r[0] for r in q.with_entities(Elder.id).all()]
    count = len(ids)
    now = datetime.now().strftime("%Y-%m")
    q.update({Elder.certify_status: "已认证", Elder.last_certify: now,
              Elder.status: "在发", Elder.suspect_type: ""}, synchronize_session=False)
    if ids:
        s.bulk_insert_mappings(CertifyRecord, [{"elder_id": i, "certify_date": now,
                                                "method": "线上小程序认证", "result": "通过"}
                                               for i in ids])
    s.commit()
    return {"ok": True, "certified_count": count}


# ---------------- 老人档案详情（全生命周期下钻） ----------------
@app.get("/api/elders/{eid}")
def elder_detail(eid: int, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    e = elder_scope(s, user).filter(Elder.id == eid).first()
    if not e:
        raise HTTPException(404, "档案不存在或无权访问")

    certs = s.query(CertifyRecord).filter(CertifyRecord.elder_id == eid) \
        .order_by(CertifyRecord.certify_date.desc()).all()
    pays = s.query(ElderPayment).filter(ElderPayment.elder_id == eid) \
        .order_by(ElderPayment.pay_month.desc()).all()
    changes = s.query(ElderChange).filter(ElderChange.elder_id == eid) \
        .order_by(ElderChange.id.desc()).all()
    wos = s.query(WorkOrder).filter(WorkOrder.elder_id == eid) \
        .order_by(WorkOrder.id.desc()).all()

    return {
        "elder": {
            "id": e.id, "archive_no": archive_no(e.district, e.id),
            "district": e.district, "street": e.street, "name": e.name, "gender": e.gender,
            "age_band": e.age_band, "standard": e.standard, "id_card": e.id_card,
            "phone": e.phone, "bank_card": e.bank_card, "social_card": e.social_card,
            "address": e.address, "contact": e.contact, "apply_channel": e.apply_channel,
            "register_date": e.register_date, "status": e.status,
            "certify_status": e.certify_status, "last_certify": e.last_certify,
            "suspect_type": e.suspect_type,
        },
        "total_paid": round(sum(p.amount for p in pays), 0),
        "certify_records": [{"certify_date": c.certify_date, "method": c.method,
                             "result": c.result} for c in certs],
        "payments": [{"pay_month": p.pay_month, "amount": p.amount, "status": p.status}
                     for p in pays],
        "changes": [{"change_type": c.change_type, "before_value": c.before_value,
                     "after_value": c.after_value, "reason": c.reason, "operator": c.operator,
                     "date": c.created_at.strftime("%Y-%m-%d") if c.created_at else ""}
                    for c in changes],
        "work_orders": [{"work_no": w.work_no, "category": w.category, "title": w.title,
                         "status": w.status, "level": w.level} for w in wos],
    }


# ---------------- 申领审核 ----------------
class ReviewRequest(BaseModel):
    action: str = "approve"   # approve / reject
    comment: str = ""


@app.get("/api/applications")
def applications(status: str = Query(""), user: User = Depends(get_current_user),
                 s: Session = Depends(get_db)):
    q = s.query(Application)
    if user.role_level == 3:
        q = q.filter(Application.street == user.street)
    elif user.role_level == 2:
        q = q.filter(Application.district == user.district)
    if status:
        q = q.filter(Application.status == status)
    rows = q.order_by(Application.id.desc()).all()
    return {"items": [{
        "id": r.id, "apply_no": r.apply_no, "district": r.district, "street": r.street,
        "name": r.name, "gender": r.gender, "age_band": r.age_band, "standard": r.standard,
        "channel": r.channel, "status": r.status, "elder_id": r.elder_id,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
    } for r in rows]}


@app.post("/api/applications/{aid}/review")
def review_application(aid: int, req: ReviewRequest,
                       user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    a = s.query(Application).get(aid)
    if not a:
        raise HTTPException(404, "工单不存在")
    if user.role_level == 3 and a.street != user.street:
        raise HTTPException(403, "无权审核该工单")
    if user.role_level == 2 and a.district != user.district:
        raise HTTPException(403, "无权审核该工单")

    if req.action == "reject":
        a.status = "已驳回"
        log_action(s, user, "驳回申领", a.apply_no)
        s.commit()
        return {"ok": True, "status": a.status}

    if a.status == "待街道审核":
        a.status = "待区县审批"
    elif a.status == "待区县审批":
        a.status = "已建档"
        from datetime import datetime
        from services.mask import mask_id_card, mask_phone, mask_social_card, mask_contact
        e = Elder(district=a.district, street=a.street, name=a.name, gender=a.gender,
                  age_band=a.age_band, standard=a.standard,
                  id_card=a.id_card or mask_id_card(),
                  phone=a.phone or mask_phone(),
                  bank_card=a.bank_card, social_card=mask_social_card(),
                  address=a.address, contact=mask_contact(),
                  apply_channel=a.channel or "线上小程序",
                  register_date=datetime.now().strftime("%Y-%m-%d"),
                  status="待认证", certify_status="待认证",
                  last_certify="", suspect_type="")
        s.add(e)
        s.flush()
        a.elder_id = e.id
        s.add(CertifyRecord(elder_id=e.id, certify_date="", method="", result="待认证"))
    log_action(s, user, "审核申领", a.apply_no)
    s.commit()
    return {"ok": True, "status": a.status, "elder_id": a.elder_id}


# ---------------- 年度复审 ----------------
@app.get("/api/certify/overview")
def certify_overview(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    eq = elder_scope(s, user)
    total = eq.count()
    certified = eq.filter(Elder.certify_status == "已认证").count()
    pending = eq.filter(Elder.certify_status == "待认证").count()
    expired = eq.filter(Elder.certify_status == "认证过期").count()
    rate = round(certified / total * 100, 1) if total else 0

    d_total = dict(eq.with_entities(Elder.district, func.count(Elder.id))
                   .group_by(Elder.district).all())
    d_cert = dict(eq.filter(Elder.certify_status == "已认证")
                  .with_entities(Elder.district, func.count(Elder.id))
                  .group_by(Elder.district).all())
    districts = [{"district": d, "total": c,
                  "rate": round(d_cert.get(d, 0) / c * 100, 1) if c else 0}
                 for d, c in sorted(d_total.items(), key=lambda x: -x[1])]

    methods = certify_scope(s, user) \
        .with_entities(CertifyRecord.method, func.count(CertifyRecord.id)) \
        .group_by(CertifyRecord.method).all()

    def _brief(r):
        return {"id": r.id, "archive_no": archive_no(r.district, r.id),
                "district": r.district, "street": r.street, "name": r.name,
                "age_band": r.age_band, "certify_status": r.certify_status,
                "last_certify": r.last_certify}

    expired_list = eq.filter(Elder.certify_status == "认证过期").order_by(Elder.id).limit(50).all()
    pending_list = eq.filter(Elder.certify_status == "待认证").order_by(Elder.id).limit(50).all()
    recent = certify_scope(s, user).filter(CertifyRecord.result == "通过") \
        .with_entities(CertifyRecord.certify_date, CertifyRecord.method,
                       CertifyRecord.result, Elder.name) \
        .order_by(CertifyRecord.id.desc()).limit(12).all()

    return {
        "kpi": {"total": total, "certified": certified, "pending": pending,
                "expired": expired, "rate": rate},
        "districts": districts,
        "methods": [{"name": m or "其他", "value": c} for m, c in methods],
        "expired_list": [_brief(r) for r in expired_list],
        "pending_list": [_brief(r) for r in pending_list],
        "recent_records": [{"date": d, "method": m, "result": r, "name": n}
                           for d, m, r, n in recent],
    }


@app.post("/api/elders/{eid}/certify")
def certify_one(eid: int, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    e = elder_scope(s, user).filter(Elder.id == eid).first()
    if not e:
        raise HTTPException(404, "档案不存在或无权访问")
    now = datetime.now().strftime("%Y-%m")
    e.certify_status = "已认证"
    e.last_certify = now
    e.status = "在发"
    e.suspect_type = ""
    s.add(CertifyRecord(elder_id=eid, certify_date=now, method="线上小程序认证", result="通过"))
    log_action(s, user, "完成复审", archive_no(e.district, e.id))
    s.commit()
    return {"ok": True}


# ---------------- 待遇变更 ----------------
class ChangeRequest(BaseModel):
    change_type: str
    after_value: str = ""
    reason: str = ""


@app.post("/api/elders/{eid}/change")
def change_elder(eid: int, req: ChangeRequest,
                 user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    e = elder_scope(s, user).filter(Elder.id == eid).first()
    if not e:
        raise HTTPException(404, "档案不存在或无权访问")
    before = f"{e.age_band}（{e.standard}）/ {e.status}"
    t = req.change_type
    if t == "调档":
        std = next((x["补贴标准"] for x in config.SUBSIDY_STANDARDS
                    if x["年龄段"] == req.after_value), e.standard)
        e.age_band = req.after_value or e.age_band
        e.standard = std
    elif t == "停发":
        e.status = "停发"
    elif t == "恢复":
        e.status = "在发"
    elif t == "死亡终止":
        e.status = "停发"
        e.suspect_type = "信息异常"
    elif t == "迁出":
        e.status = "停发"
    after = f"{e.age_band}（{e.standard}）/ {e.status}"
    s.add(ElderChange(elder_id=eid, change_type=t, before_value=before,
                      after_value=after, reason=req.reason, operator=user.name))
    log_action(s, user, "待遇变更", t)
    s.commit()
    return {"ok": True, "after_value": after}


# ---------------- 发放管理 ----------------
@app.get("/api/payments")
def payments(district: str = Query(""), month: str = Query(""),
             user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    q = pay_scope(s, user)
    if district:
        q = q.filter(PaymentRecord.district == district)
    if month:
        q = q.filter(PaymentRecord.pay_month == month)

    rows = q.order_by(PaymentRecord.pay_month.desc(), PaymentRecord.district).all()
    total_amount = sum(r.amount for r in rows)
    total_count = sum(r.count for r in rows)

    trend_q = pay_scope(s, user)
    if district:
        trend_q = trend_q.filter(PaymentRecord.district == district)
    trend = trend_q.with_entities(PaymentRecord.pay_month, func.sum(PaymentRecord.amount).label("amt")) \
        .group_by(PaymentRecord.pay_month).order_by(PaymentRecord.pay_month).all()

    abnormal = elder_scope(s, user).filter(Elder.status.in_(["停发", "待认证"])) \
        .order_by(Elder.id).limit(100).all()

    return {
        "total_amount": round(total_amount, 0), "total_count": total_count,
        "trend": [{"month": m, "amount": round(a, 1)} for m, a in trend],
        "items": [{"district": r.district, "month": r.pay_month,
                   "amount": r.amount, "count": r.count} for r in rows],
        "abnormal": [{"id": r.id, "archive_no": archive_no(r.district, r.id),
                      "district": r.district, "name": r.name, "age_band": r.age_band,
                      "standard": r.standard, "status": r.status,
                      "certify_status": r.certify_status} for r in abnormal],
    }


# ---------------- 资金监管 ----------------
@app.get("/api/fund")
def fund(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    eq = elder_scope(s, user)
    pq = pay_scope(s, user)
    total_amount = pq.with_entities(func.sum(PaymentRecord.amount)).scalar() or 0

    district_fund = pq.with_entities(
        PaymentRecord.district, func.sum(PaymentRecord.amount).label("amt"),
        func.max(PaymentRecord.count).label("cnt")
    ).group_by(PaymentRecord.district).order_by(func.sum(PaymentRecord.amount).desc()).all()

    return {
        "total_amount": round(total_amount, 0),
        "split_groups": config.FUND_SPLIT_GROUPS,
        "fund_sources": config.FUND_SOURCES,
        "district_fund": [{"district": d, "amount": round(a, 0), "count": c}
                          for d, a, c in district_fund],
    }


# ---------------- 智能稽核 ----------------
@app.get("/api/audit")
def audit(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    eq = elder_scope(s, user)
    red = eq.filter(Elder.suspect_type.in_(["疑似冒领", "重复领取"])).count()
    orange = eq.filter(Elder.certify_status == "认证过期").count()
    yellow = eq.filter(Elder.suspect_type == "信息异常").count()

    suspects = eq.filter(Elder.suspect_type != "").order_by(
        Elder.suspect_type, Elder.id).limit(200).all()

    return {
        "alerts": {"red": red, "orange": orange, "yellow": yellow, "total": red + orange + yellow},
        "suspect_types": config.SUSPECT_TYPES,
        "alert_levels": config.ALERT_LEVELS,
        "rectifications": config.RECTIFICATIONS,
        "suspects": [{"id": r.id, "district": r.district, "name": r.name, "age_band": r.age_band,
                      "suspect_type": r.suspect_type, "certify_status": r.certify_status,
                      "status": r.status} for r in suspects],
    }


@app.post("/api/audit/generate")
def generate_audit_workorders(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    eq = elder_scope(s, user)
    suspects = eq.filter(Elder.suspect_type != "").order_by(Elder.id).limit(100).all()
    level_map = {"疑似冒领": "红色", "重复领取": "红色", "认证过期": "橙色", "信息异常": "黄色"}
    count = 0
    for e in suspects:
        exist = s.query(WorkOrder).filter(WorkOrder.elder_id == e.id,
                                          WorkOrder.category == "稽核").first()
        if exist:
            continue
        s.add(WorkOrder(
            work_no=f"JC{datetime.now().strftime('%Y%m%d%H%M%S')}{e.id:06d}",
            category="稽核", source="智能稽核", elder_id=e.id,
            district=e.district, street=e.street, name=e.name, gender=e.gender,
            age_band=e.age_band, title=f"疑点：{e.suspect_type}",
            description=f"智能稽核发现 {e.name} 存在「{e.suspect_type}」疑点，请核实处置。",
            level=level_map.get(e.suspect_type, "黄色"), status="待处理"))
        count += 1
    log_action(s, user, "生成稽核工单", f"{count} 件")
    s.commit()
    return {"ok": True, "generated": count}


# ---------------- 统计分析 ----------------
@app.get("/api/analysis")
def analysis(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    eq = elder_scope(s, user)
    district_rows = eq.with_entities(Elder.district, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.district).order_by(func.count(Elder.id).desc()).all()
    age_rows = eq.with_entities(Elder.age_band, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.age_band).all()
    gender_rows = eq.with_entities(Elder.gender, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.gender).all()
    cross = eq.with_entities(Elder.district, Elder.age_band, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.district, Elder.age_band).all()
    channel_rows = eq.with_entities(Elder.apply_channel, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.apply_channel).all()

    # 未来 5 年高龄人口与资金需求预测
    std_map = {x["年龄段"]: int(x["补贴标准"].replace("元/月", "").replace("元", "").strip())
               for x in config.SUBSIDY_STANDARDS}
    age_totals = {a: c for a, c in age_rows}
    growth = {"70-79 周岁": 0.03, "80-89 周岁": 0.05, "90-99 周岁": 0.06, "100 周岁及以上": 0.07}
    projection = []
    for y in range(2027, 2032):
        people = 0.0
        fund = 0.0
        for band, std in std_map.items():
            p = age_totals.get(band, 0) * (1 + growth.get(band, 0.03)) ** (y - 2026)
            people += p
            fund += p * std
        projection.append({"year": str(y), "people": round(people),
                           "fund": round(fund / 10000.0, 1)})

    return {
        "district_dist": [{"name": d, "value": c} for d, c in district_rows],
        "age_structure": [{"name": a, "value": c} for a, c in age_rows],
        "gender_structure": [{"name": g, "value": c} for g, c in gender_rows],
        "channel_dist": [{"name": c or "其他", "value": n} for c, n in channel_rows],
        "projection": projection,
        "cross": [{"district": d, "age_band": a, "count": c} for d, a, c in cross],
    }


# ---------------- 监管工单（闭环） ----------------
@app.get("/api/workorders")
def workorders(category: str = Query(""), status: str = Query(""), level: str = Query(""),
               user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    q = s.query(WorkOrder)
    if user.role_level == 3:
        q = q.filter(WorkOrder.street == user.street)
    elif user.role_level == 2:
        q = q.filter(WorkOrder.district == user.district)
    if category:
        q = q.filter(WorkOrder.category == category)
    if status:
        q = q.filter(WorkOrder.status == status)
    if level:
        q = q.filter(WorkOrder.level == level)
    rows = q.order_by(WorkOrder.id.desc()).all()
    return {"items": [{
        "id": r.id, "work_no": r.work_no, "category": r.category, "source": r.source,
        "elder_id": r.elder_id, "district": r.district, "street": r.street, "name": r.name,
        "gender": r.gender, "age_band": r.age_band, "title": r.title,
        "description": r.description, "level": r.level, "status": r.status,
        "handler": r.handler, "satisfaction": r.satisfaction,
        "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
    } for r in rows]}


@app.post("/api/workorders/{wid}/advance")
def advance_workorder(wid: int, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    w = s.query(WorkOrder).get(wid)
    if not w:
        raise HTTPException(404, "工单不存在")
    if user.role_level == 3 and w.street != user.street:
        raise HTTPException(403, "无权处理该工单")
    if user.role_level == 2 and w.district != user.district:
        raise HTTPException(403, "无权处理该工单")
    flow = {"待处理": "整改中", "整改中": "待复核", "待复核": "已销号"}
    if w.status in flow:
        w.status = flow[w.status]
        w.handler = user.name
        log_action(s, user, "工单流转", w.work_no)
    s.commit()
    return {"ok": True, "status": w.status}


@app.post("/api/workorders/{wid}/enroll")
def enroll_workorder(wid: int, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    import random
    w = s.query(WorkOrder).get(wid)
    if not w:
        raise HTTPException(404, "工单不存在")
    standard = next((x["补贴标准"] for x in config.SUBSIDY_STANDARDS
                     if x["年龄段"] == w.age_band), "50 元/月")
    apply_no = "SQ" + datetime.now().strftime("%Y%m%d") + str(secrets.randbelow(100000)).zfill(5)
    s.add(Application(apply_no=apply_no, district=w.district, street=w.street, name=w.name,
                      gender=w.gender, age_band=w.age_band, standard=standard,
                      channel="政策找人主动服务", status="待区县审批", elder_id=0))
    w.status = "已销号"
    log_action(s, user, "政策找人纳入申领", w.name)
    s.commit()
    return {"ok": True, "apply_no": apply_no}


# ---------------- 数据比对 ----------------
@app.get("/api/compare")
def compare_tasks(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    q = s.query(CompareTask)
    if user.role_level == 2:
        q = q.filter(CompareTask.district == user.district)
    rows = q.order_by(CompareTask.id.desc()).all()
    return {"items": [{
        "id": r.id, "task_no": r.task_no, "source": r.source, "district": r.district,
        "compared_count": r.compared_count, "hit_count": r.hit_count,
        "status": r.status, "compared_at": r.compared_at,
    } for r in rows]}


@app.post("/api/compare/run")
def run_compare(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    import random
    from datetime import datetime
    source = random.choice(["公安户籍", "卫健死亡", "殡葬火化", "社保"])
    compared = secrets.randbelow(15000) + 5000
    hit = int(compared * random.uniform(0.002, 0.02))
    task_no = "BD-RUN-" + datetime.now().strftime("%H%M%S")
    s.add(CompareTask(task_no=task_no, source=source, district=user.district,
                      compared_count=compared, hit_count=hit, status="已完成",
                      compared_at=datetime.now().strftime("%Y-%m-%d")))
    log_action(s, user, "发起数据比对", source)
    s.commit()
    return {"ok": True, "task_no": task_no, "hit_count": hit}


# ---------------- 资金绩效 ----------------
@app.get("/api/performance")
def performance(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    pq = pay_scope(s, user)
    total_amount = pq.with_entities(func.sum(PaymentRecord.amount)).scalar() or 0
    months = pq.with_entities(PaymentRecord.pay_month).distinct().count()
    avg_month = round(total_amount / months, 0) if months else 0
    district_fund = pq.with_entities(PaymentRecord.district, func.sum(PaymentRecord.amount).label("amt")) \
        .group_by(PaymentRecord.district).order_by(func.sum(PaymentRecord.amount).desc()).all()
    lagged = len(config.RECTIFICATIONS)
    on_time_rate = round((len(config.DISTRICTS) - lagged) / len(config.DISTRICTS) * 100, 1) if config.DISTRICTS else 100.0
    actual_2026 = pq.filter(PaymentRecord.pay_month >= "2026-01") \
        .with_entities(func.sum(PaymentRecord.amount)).scalar() or 0
    exec_rate = round(actual_2026 / config.ANNUAL_BUDGET_2026 * 100, 1) if config.ANNUAL_BUDGET_2026 else 0
    return {
        "kpi": {
            "total_amount": round(total_amount, 0), "avg_month": avg_month, "months": months,
            "exec_rate": exec_rate, "on_time_rate": on_time_rate,
        },
        "district_fund": [{"district": d, "amount": round(a, 0)} for d, a in district_fund],
        "city_stats": config.CITY_STATS,
        "rectifications": config.RECTIFICATIONS,
    }


# ---------------- 阳光公示 ----------------
class ReportRequest(BaseModel):
    content: str = ""


@app.get("/api/publicity")
def publicity(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    pq = pay_scope(s, user)
    latest_month = pq.with_entities(func.max(PaymentRecord.pay_month)).scalar() or ""
    rows = pq.filter(PaymentRecord.pay_month == latest_month).with_entities(
        PaymentRecord.district, func.sum(PaymentRecord.amount).label("amt"),
        func.sum(PaymentRecord.count).label("cnt")
    ).group_by(PaymentRecord.district).order_by(PaymentRecord.district).all()
    return {
        "latest_month": latest_month,
        "items": [{"district": d, "amount": round(a, 0), "count": c} for d, a, c in rows],
        "total_amount": round(sum(a for _, a, _ in rows), 0),
        "total_count": sum(c for _, _, c in rows),
    }


@app.post("/api/publicity/report")
def report(req: ReportRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    import random
    content = req.content.strip()
    if not content:
        raise HTTPException(400, "举报内容不能为空")
    work_no = "SS" + datetime.now().strftime("%Y%m%d") + str(secrets.randbelow(1000)).zfill(3)
    s.add(WorkOrder(work_no=work_no, category="诉求", source="平台举报",
                    district=user.district, street=user.street, name="",
                    title="平台举报", description=content, level="黄色", status="待处理"))
    log_action(s, user, "提交举报", work_no)
    s.commit()
    return {"ok": True, "work_no": work_no}


# ---------------- 用户管理 ----------------
class UserRequest(BaseModel):
    username: str
    password: str
    name: str
    role_level: int
    district: str = ""
    street: str = ""
    dept_name: str = ""


@app.get("/api/users")
def list_users(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    if user.role_level != 1:
        raise HTTPException(403, "仅市级账号可管理用户")
    rows = s.query(User).order_by(User.id).all()
    return {"items": [{"id": r.id, "username": r.username, "name": r.name,
                       "role_level": r.role_level, "district": r.district, "street": r.street,
                       "dept_name": r.dept_name, "active": r.active} for r in rows]}


@app.post("/api/users")
def add_user(req: UserRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    if user.role_level != 1:
        raise HTTPException(403, "仅市级账号可管理用户")
    import bcrypt as _bcrypt
    from services.mask import mask_operator_name
    s.add(User(username=req.username,
               password_hash=_bcrypt.hashpw(req.password.encode(), _bcrypt.gensalt()).decode(),
               name=mask_operator_name(req.name), role_level=req.role_level, district=req.district,
               street=req.street, dept_name=req.dept_name, active=True))
    log_action(s, user, "新增用户", req.username)
    s.commit()
    return {"ok": True}


@app.post("/api/users/{uid}/toggle")
def toggle_user(uid: int, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    if user.role_level != 1:
        raise HTTPException(403, "仅市级账号可管理用户")
    u = s.query(User).get(uid)
    if not u:
        raise HTTPException(404, "用户不存在")
    u.active = not u.active
    log_action(s, user, "停用/启用用户", u.username)
    s.commit()
    return {"ok": True, "active": u.active}


# ---------------- 审计日志 ----------------
@app.get("/api/audit-logs")
def audit_logs(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    if user.role_level != 1:
        raise HTTPException(403, "仅市级账号可查看审计日志")
    rows = s.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()
    return {"items": [{"id": r.id, "user_name": r.user_name, "role": r.role,
                       "action": r.action, "target": r.target,
                       "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""}
                      for r in rows]}


# ---------------- 消息中心 ----------------
@app.get("/api/messages")
def messages(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    rows = s.query(Message).order_by(Message.id.desc()).all()
    return {"items": [{"id": r.id, "category": r.category, "title": r.title,
                       "content": r.content, "read": r.read,
                       "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else ""}
                      for r in rows]}


@app.post("/api/messages/{mid}/read")
def read_message(mid: int, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    m = s.query(Message).get(mid)
    if m:
        m.read = True
        s.commit()
    return {"ok": True}


# ---------------- 全局搜索 ----------------
@app.get("/api/search")
def search(q: str = Query(""), user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    q = q.strip()
    if not q:
        return {"elders": [], "work_orders": [], "applications": []}

    eq = elder_scope(s, user)
    elders = []
    if "-" in q:
        tail = q.rsplit("-", 1)[-1]
        if tail.isdigit():
            e = eq.filter(Elder.id == int(tail)).first()
            if e:
                elders = [e]
    # 区划码搜索（如 610102）
    if not elders:
        dist = [d for d, c in config.DISTRICT_CODES.items() if c == q]
        if dist:
            elders = eq.filter(Elder.district == dist[0]).limit(20).all()
    if not elders:
        elders = eq.filter(or_(Elder.name.contains(q), Elder.id_card.contains(q),
                               Elder.phone.contains(q))).limit(20).all()

    woq = s.query(WorkOrder)
    apq = s.query(Application)
    if user.role_level == 3:
        woq = woq.filter(WorkOrder.street == user.street)
        apq = apq.filter(Application.street == user.street)
    elif user.role_level == 2:
        woq = woq.filter(WorkOrder.district == user.district)
        apq = apq.filter(Application.district == user.district)
    wos = woq.filter(or_(WorkOrder.work_no.contains(q), WorkOrder.name.contains(q),
                         WorkOrder.title.contains(q))).limit(20).all()
    apps = apq.filter(or_(Application.apply_no.contains(q), Application.name.contains(q))).limit(20).all()

    return {
        "elders": [{"id": e.id, "archive_no": archive_no(e.district, e.id), "name": e.name,
                    "district": e.district, "age_band": e.age_band} for e in elders],
        "work_orders": [{"id": w.id, "work_no": w.work_no, "title": w.title,
                         "category": w.category, "status": w.status} for w in wos],
        "applications": [{"id": a.id, "apply_no": a.apply_no, "name": a.name,
                          "status": a.status} for a in apps],
    }


# ---------------- 工作台（待办中心） ----------------
@app.get("/api/workbench")
def workbench(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    eq = elder_scope(s, user)
    apq = s.query(Application)
    woq = s.query(WorkOrder)
    if user.role_level == 3:
        apq = apq.filter(Application.street == user.street)
        woq = woq.filter(WorkOrder.street == user.street)
    elif user.role_level == 2:
        apq = apq.filter(Application.district == user.district)
        woq = woq.filter(WorkOrder.district == user.district)

    pending_apps = apq.filter(Application.status.in_(["待街道审核", "待区县审批"])).count()
    recent_apps = apq.filter(Application.status.in_(["待街道审核", "待区县审批"])) \
        .order_by(Application.id.desc()).limit(5).all()
    pending_cert = eq.filter(Elder.certify_status.in_(["待认证", "认证过期"])).count()
    recent_cert = eq.filter(Elder.certify_status.in_(["待认证", "认证过期"])) \
        .order_by(Elder.id).limit(5).all()
    pending_wo = woq.filter(WorkOrder.status.in_(["待处理", "待复核"])).count()
    recent_wo = woq.filter(WorkOrder.status.in_(["待处理", "待复核"])) \
        .order_by(WorkOrder.id.desc()).limit(5).all()
    unread = s.query(Message).filter(Message.read == False).count()
    recent_msg = s.query(Message).filter(Message.read == False).order_by(Message.id.desc()).limit(5).all()

    return {
        "kpi": {"pending_apps": pending_apps, "pending_cert": pending_cert,
                "pending_wo": pending_wo, "unread": unread},
        "recent_apps": [{"id": a.id, "apply_no": a.apply_no, "name": a.name,
                         "district": a.district, "status": a.status} for a in recent_apps],
        "recent_cert": [{"id": e.id, "archive_no": archive_no(e.district, e.id), "name": e.name,
                         "district": e.district, "certify_status": e.certify_status} for e in recent_cert],
        "recent_wo": [{"id": w.id, "work_no": w.work_no, "category": w.category,
                       "title": w.title, "status": w.status} for w in recent_wo],
        "recent_msg": [{"id": m.id, "category": m.category, "title": m.title} for m in recent_msg],
    }


# ---------------- 区县街道下钻 ----------------
@app.get("/api/district/{name}/streets")
def district_streets(name: str, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    rows = elder_scope(s, user).filter(Elder.district == name) \
        .with_entities(Elder.street, func.count(Elder.id).label("cnt")) \
        .group_by(Elder.street).order_by(func.count(Elder.id).desc()).limit(20).all()
    return {"items": [{"street": st or "其他", "count": c} for st, c in rows]}


# ---------------- 批量操作 ----------------
class BatchRequest(BaseModel):
    ids: list = []
    action: str = "stop"   # stop / certify


@app.post("/api/elders/batch")
def batch_update(req: BatchRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    if not req.ids:
        return {"ok": True, "count": 0}
    q = elder_scope(s, user).filter(Elder.id.in_(req.ids))
    if req.action == "stop":
        q.update({Elder.status: "停发"}, synchronize_session=False)
    elif req.action == "certify":
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m")
        ids = [r[0] for r in q.with_entities(Elder.id).all()]
        q.update({Elder.certify_status: "已认证", Elder.last_certify: now,
                  Elder.status: "在发", Elder.suspect_type: ""}, synchronize_session=False)
        if ids:
            s.bulk_insert_mappings(CertifyRecord, [{"elder_id": i, "certify_date": now,
                                                    "method": "线上小程序认证", "result": "通过"}
                                                   for i in ids])
    log_action(s, user, f"批量{'复审' if req.action == 'certify' else '停发'}", f"{len(req.ids)} 人")
    s.commit()
    return {"ok": True, "count": len(req.ids)}


# ---------------- AI 助手 ----------------
class ChatRequest(BaseModel):
    messages: list = []


def build_ai_context(s: Session, user: User) -> str:
    """构造平台上下文，让 AI 回答本平台的具体政策、流程与实时数据"""
    eq = elder_scope(s, user)
    total = eq.count()
    certified = eq.filter(Elder.certify_status == "已认证").count()
    pending = eq.filter(Elder.certify_status.in_(["待认证", "认证过期"])).count()
    suspects = eq.filter(Elder.suspect_type != "").count()
    stds = "；".join(f"{x['年龄段']}：{x['补贴标准']}" for x in config.SUBSIDY_STANDARDS)
    steps = " → ".join(x["步骤"] for x in config.APPLY_STEPS)
    policies = "；".join(f"{x['政策名称']}：{x['要点']}" for x in config.POLICIES)
    faq = "；".join(f"{x['问']}：{x['答']}" for x in config.AI_FAQ)
    alerts = "；".join(f"{k}：{v['desc']}" for k, v in config.ALERT_LEVELS.items())
    funds = "；".join(g["分担比例"] + "：" + "、".join(g["区县"]) for g in config.FUND_SPLIT_GROUPS)
    return (
        f"你是「西安市高龄补贴监管平台」的 AI 助手，为监管工作人员提供政策与数据咨询服务。"
        f"当前管辖范围：{user.district or '全市'}。\n"
        f"【补贴标准】{stds}。\n"
        f"【申领渠道】{'、'.join(config.APPLY_CHANNELS)}。\n"
        f"【申领流程】{steps}。\n"
        f"【资格认证】每年一次，方式：{'、'.join(config.CERTIFY_RULES['方式'])}；逾期处理：{config.CERTIFY_RULES['逾期处理']}。\n"
        f"【资金分担】{funds}。\n"
        f"【预警分级】{alerts}。\n"
        f"【政策法规】{policies}。\n"
        f"【常见问题】{faq}。\n"
        f"【实时数据】在册老人 {total} 人，已认证 {certified} 人，待复审 {pending} 人，疑点 {suspects} 人。\n"
        f"请用简洁、专业的中文回答；涉及数据时引用上述实时数据；政策类问题优先引用政策法规和常见问题。"
    )


@app.post("/api/ai/chat")
async def ai_chat(req: ChatRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    import httpx
    if not config.DEEPSEEK_API_KEY:
        raise HTTPException(500, "未配置 DeepSeek API Key")
    system = build_ai_context(s, user)
    msgs = [{"role": "system", "content": system}] + \
           [m for m in req.messages[-10:] if m.get("role") in ("user", "assistant")]
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                config.DEEPSEEK_API_URL,
                headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
                json={"model": config.DEEPSEEK_MODEL, "messages": msgs,
                      "temperature": 0.7, "max_tokens": 1000},
            )
            r.raise_for_status()
            data = r.json()
            return {"reply": data["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(502, f"AI 服务调用失败：{e}")


@app.post("/api/ai/stream")
async def ai_stream(req: ChatRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    import httpx
    import json
    if not config.DEEPSEEK_API_KEY:
        raise HTTPException(500, "未配置 DeepSeek API Key")
    system = build_ai_context(s, user)
    msgs = [{"role": "system", "content": system}] + \
           [m for m in req.messages[-10:] if m.get("role") in ("user", "assistant")]

    async def gen():
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST", config.DEEPSEEK_API_URL,
                    headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
                    json={"model": config.DEEPSEEK_MODEL, "messages": msgs,
                          "stream": True, "temperature": 0.7, "max_tokens": 1000},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            obj = json.loads(data)
                            delta = obj["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield f"data: {json.dumps({'content': delta}, ensure_ascii=False)}\n\n"
                        except Exception:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------- NL2SQL 自然语言数据查询 ----------------
@app.post("/api/ai/nl2sql")
async def ai_nl2sql(req: ChatRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    import httpx
    import re
    question = req.messages[-1].get("content", "") if req.messages else ""
    if not question:
        raise HTTPException(400, "问题不能为空")
    if not config.DEEPSEEK_API_KEY:
        raise HTTPException(500, "未配置 DeepSeek API Key")

    schema = (
        "SQLite 表结构（字段含义）：\n"
        "elders(id, district 区县, street 街道, name, gender 性别, age_band 年龄段, standard 补贴标准, "
        "certify_status 认证状态[已认证/待认证/认证过期], status 发放状态[在发/停发/待认证], "
        "suspect_type 疑点类型, apply_channel 申领渠道, register_date 建档日期)\n"
        "payment_records(district 区县, pay_month 发放月份, amount 发放金额万元, count 受益人数)\n"
        "work_orders(category 类别, district 区县, level 级别, status 状态[待处理/整改中/待复核/已销号])\n"
        "applications(district 区县, status 状态, age_band 年龄段)\n"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            config.DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
            json={"model": config.DEEPSEEK_MODEL,
                  "messages": [{"role": "user",
                                "content": f"{schema}\n为下面的问题生成一条 SQLite 只读 SELECT 查询，只输出 SQL 本身，不要解释、不要 markdown 代码块：\n{question}"}],
                  "temperature": 0, "max_tokens": 500})
        r.raise_for_status()
        sql = r.json()["choices"][0]["message"]["content"].strip()

    sql = re.sub(r"```(?:sql)?", "", sql).strip().rstrip(";")
    upper = sql.upper()
    if not upper.startswith("SELECT"):
        return {"sql": sql, "error": "仅支持只读查询"}
    for bad in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "PRAGMA", "ATTACH"):
        if bad in upper:
            return {"sql": sql, "error": "检测到非法操作"}
    try:
        result = s.execute(text(sql + " LIMIT 20")).fetchall()
        cols = list(result[0].keys()) if result else []
        rows = [[str(x) for x in row] for row in result]
        return {"sql": sql, "columns": cols, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"sql": sql, "error": f"查询失败：{e}"}


# ---------------- 统计异常检测（z-score 离群） ----------------
@app.get("/api/anomaly")
def anomaly(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    import statistics
    eq = elder_scope(s, user)
    elders = eq.filter(Elder.certify_status.in_(["已认证", "认证过期"])) \
        .with_entities(Elder.id, Elder.district, Elder.name, Elder.certify_status,
                       Elder.last_certify).all()
    intervals = []
    for eid, district, name, status, last in elders:
        if not last:
            continue
        y, m = int(last[:4]), int(last[5:7])
        months = (2026 - y) * 12 + (8 - m)
        intervals.append({"id": eid, "district": district, "name": name, "status": status,
                          "last_certify": last, "months": months})
    vals = [x["months"] for x in intervals]
    mean = statistics.mean(vals) if vals else 0
    stdev = statistics.stdev(vals) if len(vals) > 1 else 0
    outliers = []
    for x in intervals:
        z = (x["months"] - mean) / stdev if stdev else 0
        if z >= 1.5:
            x["z_score"] = round(z, 2)
            outliers.append(x)
    outliers.sort(key=lambda x: -x["months"])
    return {
        "method": "z-score 统计离群检测",
        "policy": "依据《西安市高龄老人生活保健补贴发放办法》，补贴需每年资格认证、逾期暂停发放；本检测用 z-score 自动发现认证间隔统计异常对象",
        "mean": round(mean, 1), "stdev": round(stdev, 1),
        "outliers": outliers[:20], "total": len(intervals),
    }


# ---------------- 风险画像 ----------------
def _risk_score(e) -> int:
    """老人风险评分（0-100）：疑点 + 认证状态 + 发放状态"""
    s = 0
    if e.suspect_type in ("疑似冒领", "重复领取"):
        s += 40
    elif e.suspect_type == "认证过期":
        s += 30
    elif e.suspect_type == "信息异常":
        s += 20
    if e.certify_status == "认证过期":
        s += 20
    elif e.certify_status == "待认证":
        s += 10
    if e.status == "停发":
        s += 10
    return min(s, 100)


@app.get("/api/risk")
def risk(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    eq = elder_scope(s, user)
    total = eq.count()
    high_cond = or_(Elder.suspect_type.in_(["疑似冒领", "重复领取"]),
                    Elder.certify_status == "认证过期")
    mid_cond = or_(Elder.suspect_type == "信息异常", Elder.certify_status == "待认证")
    high = eq.filter(high_cond).count()
    mid = eq.filter(mid_cond).count()
    low = max(total - high - mid, 0)

    district_risk = eq.filter(high_cond).with_entities(
        Elder.district, func.count(Elder.id).label("cnt")
    ).group_by(Elder.district).order_by(func.count(Elder.id).desc()).all()

    high_list = eq.filter(high_cond).order_by(Elder.id).limit(100).all()

    # 疑点类型分布
    type_rows = eq.filter(Elder.suspect_type != "").with_entities(
        Elder.suspect_type, func.count(Elder.id).label("cnt")
    ).group_by(Elder.suspect_type).all()

    # 年龄段风险分布
    age_risk = eq.filter(high_cond).with_entities(
        Elder.age_band, func.count(Elder.id).label("cnt")
    ).group_by(Elder.age_band).all()

    # 风险分数段分布
    buckets = {"0-19": 0, "20-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
    for e in eq.filter(high_cond).all():
        sc = _risk_score(e)
        if sc < 20:
            buckets["0-19"] += 1
        elif sc < 40:
            buckets["20-39"] += 1
        elif sc < 60:
            buckets["40-59"] += 1
        elif sc < 80:
            buckets["60-79"] += 1
        else:
            buckets["80-100"] += 1

    # 处置情况
    disposed = s.query(WorkOrder).filter(WorkOrder.category == "稽核", WorkOrder.elder_id != 0).count()
    resolved = s.query(WorkOrder).filter(WorkOrder.status == "已销号").count()

    return {
        "kpi": {"total": total, "high": high, "mid": mid, "low": low,
                "disposed": disposed, "resolved": resolved},
        "district_risk": [{"district": d, "high": c} for d, c in district_risk],
        "type_dist": [{"name": t, "value": c} for t, c in type_rows],
        "age_risk": [{"name": a, "value": c} for a, c in age_risk],
        "score_dist": [{"name": k, "value": v} for k, v in buckets.items()],
        "high_list": [{"id": e.id, "archive_no": archive_no(e.district, e.id), "name": e.name,
                       "district": e.district, "street": e.street, "suspect_type": e.suspect_type,
                       "certify_status": e.certify_status, "status": e.status,
                       "score": _risk_score(e)} for e in high_list],
    }


# ---------------- 双随机抽查 ----------------
class SpotCheckRequest(BaseModel):
    count: int = 20


@app.post("/api/spotcheck/generate")
def generate_spotcheck(req: SpotCheckRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    import random
    eq = elder_scope(s, user)
    sample = eq.order_by(func.random()).limit(max(1, min(req.count, 50))).all()
    checkers = [u.name for u in s.query(User).filter(User.active == True).all()] or ["王**", "李**", "张**"]
    if not sample:
        raise HTTPException(400, "当前管辖范围内无可用抽查对象")
    task_no = "SC" + datetime.now().strftime("%Y%m%d%H%M%S")
    task = SpotCheck(task_no=task_no, name=f"双随机抽查（{user.district or '全市'}）",
                     district=user.district, elder_count=len(sample),
                     checker_count=len(checkers), status="检查中")
    s.add(task)
    s.flush()
    for e in sample:
        s.add(SpotCheckRecord(task_id=task.id, elder_id=e.id,
                              archive_no=archive_no(e.district, e.id), name=e.name,
                              district=e.district, checker=random.choice(checkers), result="待检查"))
    log_action(s, user, "发起双随机抽查", f"{len(sample)} 人")
    s.commit()
    return {"ok": True, "task_id": task.id, "count": len(sample)}


@app.get("/api/spotcheck")
def spotchecks(user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    tasks = s.query(SpotCheck).order_by(SpotCheck.id.desc()).all()
    return {"items": [{
        "id": t.id, "task_no": t.task_no, "name": t.name, "district": t.district,
        "elder_count": t.elder_count, "checker_count": t.checker_count, "status": t.status,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
    } for t in tasks]}


@app.get("/api/spotcheck/{tid}/records")
def spotcheck_records(tid: int, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    recs = s.query(SpotCheckRecord).filter(SpotCheckRecord.task_id == tid).all()
    return {"items": [{
        "id": r.id, "archive_no": r.archive_no, "name": r.name, "district": r.district,
        "checker": r.checker, "result": r.result,
    } for r in recs]}


class SpotResultRequest(BaseModel):
    result: str = "正常"


@app.post("/api/spotcheck/record/{rid}/result")
def spotcheck_result(rid: int, req: SpotResultRequest, user: User = Depends(get_current_user), s: Session = Depends(get_db)):
    from datetime import datetime
    import random
    r = s.query(SpotCheckRecord).get(rid)
    if not r:
        raise HTTPException(404, "抽查记录不存在")
    r.result = req.result
    if req.result == "发现问题":
        elder = s.query(Elder).get(r.elder_id) if r.elder_id else None
        work_no = "JC" + datetime.now().strftime("%Y%m%d%H%M%S") + str(secrets.randbelow(100)).zfill(2)
        s.add(WorkOrder(work_no=work_no, category="稽核", source="双随机抽查", elder_id=r.elder_id,
                        district=r.district, street=elder.street if elder else "", name=r.name,
                        title="双随机抽查发现问题",
                        description=f"双随机抽查发现 {r.name} 存在问题，请核实处置。",
                        level="黄色", status="待处理"))
    log_action(s, user, "抽查结果登记", r.name)
    s.commit()
    return {"ok": True, "result": r.result}


# ---------------- 通知公告 ----------------
@app.get("/api/notices")
def notices(s: Session = Depends(get_db)):
    rows = s.query(Notice).order_by(Notice.important.desc(), Notice.publish_date.desc()).all()
    return {"items": [{"id": r.id, "title": r.title, "category": r.category,
                       "content": r.content, "publish_date": r.publish_date,
                       "important": r.important} for r in rows]}


@app.get("/api/health")
def health():
    return {"ok": True}
