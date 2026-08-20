# -*- coding: utf-8 -*-
"""种子数据：三级监管账号 + 大规模脱敏老人档案 + 发放台账 + 通知公告（幂等）"""
import os

import bcrypt
from sqlalchemy.orm import Session

import config
from models import (User, Elder, PaymentRecord, Notice, CertifyRecord, ElderPayment,
                    Application, ElderChange, WorkOrder, CompareTask, AuditLog, Message)
from services import generator

# 受益老人档案条数（演示大数据量）；可通过环境变量 ELDER_TOTAL 调整，云端免费额度建议 10000
ELDER_TOTAL = int(os.environ.get("ELDER_TOTAL", "100000"))


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# 三级账号：1 市级 / 2 区县 / 3 街道
# username, password, name, role_level, district, street, dept_name
ACCOUNTS = [
    ("admin", "admin123", "王建国", 1, "", "", "西安市养老服务处"),
    ("yanta", "123456", "李慧敏", 2, "雁塔区", "", "雁塔区民政局"),
    ("lianhu", "123456", "王志强", 2, "莲湖区", "", "莲湖区民政局"),
    ("lintong", "123456", "张卫东", 2, "临潼区", "", "临潼区民政局"),
    ("huyi", "123456", "陈晓梅", 2, "鄠邑区", "", "鄠邑区民政局"),
    ("xiaozhai", "123456", "赵建国", 3, "雁塔区", "小寨路街道", "雁塔区小寨路街道办事处"),
    ("beiyuanmen", "123456", "钱丽华", 3, "莲湖区", "北院门街道", "莲湖区北院门街道办事处"),
    ("lishan", "123456", "孙卫民", 3, "临潼区", "骊山街道", "临潼区骊山街道办事处"),
]


def _seed_accounts(session: Session):
    if session.query(User).count() == 0:
        from services.mask import mask_operator_name
        for username, pw, name, level, district, street, dept in ACCOUNTS:
            session.add(User(
                username=username, password_hash=hash_pw(pw), name=mask_operator_name(name),
                role_level=level, district=district, street=street, dept_name=dept,
            ))
        session.commit()


def _seed_elders(session: Session):
    if session.query(Elder).count() == 0:
        rows = generator.generate_elders(ELDER_TOTAL)
        batch = 5000
        for i in range(0, len(rows), batch):
            session.bulk_insert_mappings(Elder, rows[i:i + batch])
            session.commit()


def _seed_payments(session: Session):
    if session.query(PaymentRecord).count() == 0:
        rows = generator.generate_payment_records()
        session.bulk_insert_mappings(PaymentRecord, rows)
        session.commit()


def _seed_notices(session: Session):
    if session.query(Notice).count() == 0:
        rows = generator.generate_notices()
        session.bulk_insert_mappings(Notice, rows)
        session.commit()


def _bulk_insert(session: Session, model, rows, batch: int = 5000):
    """分块批量插入，控制内存占用"""
    for i in range(0, len(rows), batch):
        session.bulk_insert_mappings(model, rows[i:i + batch])
        session.commit()


def _parse_standard(standard: str) -> int:
    return int(standard.replace("元/月", "").replace("元", "").strip())


def _seed_certify_records(session: Session):
    """为每位老人生成年度资格认证记录（2024 / 2025 / 2026）"""
    if session.query(CertifyRecord).count() == 0:
        import random as _r
        methods = config.CERTIFY_RULES["方式"]
        total = session.query(Elder).count()
        for offset in range(0, total, 10000):
            elders = session.query(Elder.id, Elder.certify_status, Elder.last_certify) \
                .order_by(Elder.id).offset(offset).limit(10000).all()
            rows = []
            for eid, certify, last in elders:
                rows.append({"elder_id": eid, "certify_date": "2024-06",
                             "method": _r.choice(methods), "result": "通过"})
                rows.append({"elder_id": eid, "certify_date": "2025-06",
                             "method": _r.choice(methods), "result": "通过"})
                if certify == "已认证":
                    rows.append({"elder_id": eid, "certify_date": last or "2026-06",
                                 "method": _r.choice(methods), "result": "通过"})
                elif certify == "认证过期":
                    rows.append({"elder_id": eid, "certify_date": last or "2025-01",
                                 "method": _r.choice(methods), "result": "未通过"})
                # 待认证：本年度暂无认证记录
            _bulk_insert(session, CertifyRecord, rows)


def _seed_elder_payments(session: Session):
    """为每位老人生成近 6 个月个人发放记录"""
    if session.query(ElderPayment).count() == 0:
        months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
        total = session.query(Elder).count()
        for offset in range(0, total, 10000):
            elders = session.query(Elder.id, Elder.standard, Elder.status, Elder.suspect_type) \
                .order_by(Elder.id).offset(offset).limit(10000).all()
            rows = []
            for eid, standard, status, suspect in elders:
                amt = _parse_standard(standard)
                for idx, month in enumerate(months):
                    if status == "停发" or suspect == "认证过期":
                        st = "停发" if idx >= len(months) - 2 else "已发放"
                    elif status == "待认证":
                        st = "待发放"
                    else:
                        st = "已发放"
                    rows.append({"elder_id": eid, "pay_month": month,
                                 "amount": amt if st == "已发放" else 0, "status": st})
            _bulk_insert(session, ElderPayment, rows)


def _seed_applications(session: Session):
    """生成演示申领工单（待街道审核 / 待区县审批）"""
    if session.query(Application).count() == 0:
        import random as _r
        from services.mask import mask_name, mask_id_card, mask_phone, mask_bank_card, mask_address
        channels = config.APPLY_CHANNELS + ["线下村（居）委会"]
        statuses = ["待街道审核", "待区县审批"]
        bands = [(b[0], b[1]) for b in config.AGE_BAND_DIST]
        rows = []
        for i in range(200):
            district = _r.choice(config.DISTRICTS)
            street = _r.choice(config.STREETS.get(district, [""]))
            gender = _r.choice(["男", "女"])
            age_band, standard = _r.choice(bands)
            rows.append({
                "apply_no": f"SQ2026{i + 1:05d}",
                "district": district, "street": street,
                "name": mask_name(gender), "gender": gender,
                "age_band": age_band, "standard": standard,
                "channel": _r.choice(channels),
                "id_card": mask_id_card(), "phone": mask_phone(),
                "address": mask_address(district), "bank_card": mask_bank_card(),
                "remark": _r.choice(["", "本人现场申请", "子女代办", "电话申请"]),
                "status": _r.choice(statuses), "elder_id": 0,
            })
        _bulk_insert(session, Application, rows)


def _seed_elder_changes(session: Session):
    """为老人生成待遇变更记录（调档 / 停发）"""
    if session.query(ElderChange).count() == 0:
        total = session.query(Elder).count()
        for offset in range(0, total, 10000):
            elders = session.query(Elder.id, Elder.age_band, Elder.standard, Elder.status) \
                .order_by(Elder.id).offset(offset).limit(10000).all()
            rows = []
            for eid, age_band, standard, status in elders:
                if age_band != "70-79 周岁":
                    rows.append({"elder_id": eid, "change_type": "调档",
                                 "before_value": "70-79 周岁（50 元/月）",
                                 "after_value": f"{age_band}（{standard}）",
                                 "reason": "年龄增长自动调档", "operator": "系统"})
                if status == "停发":
                    rows.append({"elder_id": eid, "change_type": "停发",
                                 "before_value": "在发", "after_value": "停发",
                                 "reason": "认证过期自动停发", "operator": "系统"})
            _bulk_insert(session, ElderChange, rows)


def _seed_work_orders(session: Session):
    """监管工单：数据比对命中 + 政策找人 + 诉求"""
    if session.query(WorkOrder).count() == 0:
        import random as _r
        from datetime import datetime, timedelta
        from services.mask import mask_name
        now = datetime.now()
        rows = []

        compare_sources = ["公安户籍", "卫健死亡", "殡葬火化", "社保"]
        compare_titles = {
            "公安户籍": "户籍信息与档案不一致，需核实",
            "卫健死亡": "死亡未停发，疑似冒领",
            "殡葬火化": "火化记录未同步，需停发",
            "社保": "社保停发但补贴仍发放，需核查",
        }
        for i in range(40):
            district = _r.choice(config.DISTRICTS)
            street = _r.choice(config.STREETS.get(district, [""]))
            gender = _r.choice(["男", "女"])
            src = _r.choice(compare_sources)
            rows.append({
                "work_no": f"BD2026{i + 1:05d}", "category": "比对", "source": src,
                "elder_id": 0, "district": district, "street": street,
                "name": mask_name(gender), "gender": gender, "age_band": "",
                "title": compare_titles[src],
                "description": "通过跨部门数据比对发现疑点，需逐人核实。",
                "level": "红色" if src != "社保" else "橙色",
                "status": _r.choice(["待处理", "整改中", "待复核", "已销号"]),
                "handler": "", "satisfaction": "",
                "created_at": now - timedelta(days=_r.randint(0, 30)),
            })

        bands = [b[0] for b in config.AGE_BAND_DIST]
        for i in range(60):
            district = _r.choice(config.DISTRICTS)
            street = _r.choice(config.STREETS.get(district, [""]))
            gender = _r.choice(["男", "女"])
            age_band = _r.choice(bands)
            rows.append({
                "work_no": f"ZR2026{i + 1:05d}", "category": "政策找人", "source": "政策找人",
                "elder_id": 0, "district": district, "street": street,
                "name": mask_name(gender), "gender": gender, "age_band": age_band,
                "title": "年满 70 周岁未申领高龄补贴",
                "description": "比对户籍年龄库发现应享未享人员，请主动联系协助申领。",
                "level": "黄色", "status": "待处理", "handler": "", "satisfaction": "",
                "created_at": now - timedelta(days=_r.randint(0, 20)),
            })

        complaint_sources = ["12345 热线", "平台举报", "来信来访"]
        for i in range(20):
            district = _r.choice(config.DISTRICTS)
            street = _r.choice(config.STREETS.get(district, [""]))
            gender = _r.choice(["男", "女"])
            src = _r.choice(complaint_sources)
            status = _r.choice(["待处理", "办理中", "已办结"])
            rows.append({
                "work_no": f"SS2026{i + 1:05d}", "category": "诉求", "source": src,
                "elder_id": 0, "district": district, "street": street,
                "name": mask_name(gender), "gender": gender, "age_band": "",
                "title": "高龄补贴发放咨询 / 投诉",
                "description": "反映高龄补贴发放相关问题，请核实办理并回访。",
                "level": "黄色", "status": status,
                "handler": "区县民政局" if status != "待处理" else "",
                "satisfaction": _r.choice(["满意", "一般", "不满意"]) if status == "已办结" else "",
                "created_at": now - timedelta(days=_r.randint(0, 15)),
            })

        _bulk_insert(session, WorkOrder, rows)


def _seed_compare_tasks(session: Session):
    """跨部门数据比对任务"""
    if session.query(CompareTask).count() == 0:
        import random as _r
        sources = ["公安户籍", "卫健死亡", "殡葬火化", "社保"]
        rows = []
        for i in range(8):
            src = sources[i % 4]
            compared = _r.randint(2000, 20000)
            hit = int(compared * _r.uniform(0.002, 0.02))
            rows.append({
                "task_no": f"BD-RUN-{i + 1:03d}", "source": src,
                "district": _r.choice(config.DISTRICTS),
                "compared_count": compared, "hit_count": hit,
                "status": "已完成", "compared_at": f"2026-0{i % 6 + 1}-15",
            })
        _bulk_insert(session, CompareTask, rows)


def _seed_messages(session: Session):
    """消息中心"""
    if session.query(Message).count() == 0:
        from datetime import datetime, timedelta
        now = datetime.now()
        msgs = [
            ("预警", "临潼区、鄠邑区拨付滞后已整改", "两区 2025 年度高龄补贴已于 2026-03-31 前足额发放完毕。"),
            ("预警", "发现疑似冒领红色预警", "本月数据比对新增疑似冒领疑点，请及时生成工单处置。"),
            ("通知", "2026 年度资格认证开始", "请年满 70 周岁对象于 6 月底前完成年度认证。"),
            ("政策", "陕西高龄补贴新政 12 月 1 日实施", "合并高龄补贴复审与养老待遇领取认证。"),
            ("待办", "有待复核工单", "您有若干工单处于待复核状态，请及时处理。"),
            ("通知", "第三季度发放工作部署", "请核对台账，确保 7 月资金按时足额发放。"),
        ]
        rows = [{"category": cat, "title": t, "content": c, "read": False,
                 "created_at": now - timedelta(days=i)} for i, (cat, t, c) in enumerate(msgs)]
        _bulk_insert(session, Message, rows)


def _seed_audit_logs(session: Session):
    """操作审计日志（演示留痕）"""
    if session.query(AuditLog).count() == 0:
        from datetime import datetime, timedelta
        now = datetime.now()
        logs = [
            ("王*国", "市级", "登录系统", "监管驾驶舱"),
            ("李*敏", "区县", "审核申领工单", "申领审核"),
            ("王*国", "市级", "生成稽核工单", "智能稽核"),
            ("张*东", "区县", "待遇变更", "受益对象管理"),
        ]
        rows = [{"user_name": n, "role": r, "action": a, "target": t,
                 "created_at": now - timedelta(hours=i * 3)} for i, (n, r, a, t) in enumerate(logs)]
        _bulk_insert(session, AuditLog, rows)


def seed_all(session: Session):
    _seed_accounts(session)
    _seed_elders(session)
    _seed_payments(session)
    _seed_notices(session)
    _seed_certify_records(session)
    _seed_elder_payments(session)
    _seed_applications(session)
    _seed_elder_changes(session)
    _seed_work_orders(session)
    _seed_compare_tasks(session)
    _seed_messages(session)
    _seed_audit_logs(session)
