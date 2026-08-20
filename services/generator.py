# -*- coding: utf-8 -*-
"""演示数据生成器 —— 大规模脱敏老人档案 + 发放台账 + 通知公告"""
import random

import config
from services.mask import (mask_name, mask_id_card, mask_phone, mask_bank_card,
                           mask_social_card, mask_address, mask_contact)

# 固定随机种子，保证生成结果幂等
SEED = 20260819
random.seed(SEED)

TOTAL_BENEFICIARIES = 1010000
CURRENT_MONTH = "2026-06"


def _parse_amount(s: str) -> int:
    return int(s.replace("元/月", "").replace("元", "").strip())


def _weighted(items, weights):
    return random.choices(items, weights=weights, k=1)[0]


def _month_back(month_str: str, back: int) -> str:
    y, m = int(month_str[:4]), int(month_str[5:7])
    total = y * 12 + (m - 1) - back
    yy, mm = divmod(total, 12)
    return f"{yy}-{mm + 1:02d}"


def _rand_date() -> str:
    """生成建档日期（2018-2025 年）"""
    return f"{random.randint(2018, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"


def _gen_certify():
    certify = _weighted(["已认证", "待认证", "认证过期"], [0.92, 0.05, 0.03])
    if certify == "已认证":
        last = _month_back(CURRENT_MONTH, random.randint(0, 5))
        suspect = ""
    elif certify == "待认证":
        last = ""
        suspect = "认证过期" if random.random() < 0.3 else ""
    else:
        last = _month_back(CURRENT_MONTH, random.randint(12, 24))
        suspect = "认证过期"

    if not suspect:
        r = random.random()
        if r < 0.01:
            suspect = "疑似冒领"
        elif r < 0.015:
            suspect = "重复领取"
        elif r < 0.02:
            suspect = "信息异常"
    return certify, last, suspect


def generate_elders(total: int) -> list:
    """生成 total 条脱敏老人档案（dict 列表）"""
    districts = list(config.DISTRICT_WEIGHTS.keys())
    d_weights = list(config.DISTRICT_WEIGHTS.values())
    bands = [(b[0], b[1]) for b in config.AGE_BAND_DIST]
    b_weights = [b[2] for b in config.AGE_BAND_DIST]

    rows = []
    for _ in range(total):
        district = _weighted(districts, d_weights)
        street = random.choice(config.STREETS.get(district, [""]))
        age_band, standard = _weighted(bands, b_weights)
        gender = _weighted(["男", "女"], [0.48, 0.52])
        certify, last_certify, suspect = _gen_certify()
        if certify == "认证过期":
            status = "停发"
        elif certify == "待认证":
            status = _weighted(["待认证", "在发"], [0.6, 0.4])
        else:
            status = _weighted(["在发", "停发"], [0.96, 0.04])

        rows.append({
            "district": district,
            "street": street,
            "name": mask_name(gender),
            "gender": gender,
            "age_band": age_band,
            "standard": standard,
            "id_card": mask_id_card(),
            "phone": mask_phone(),
            "bank_card": mask_bank_card(),
            "social_card": mask_social_card(),
            "address": mask_address(district),
            "contact": mask_contact(),
            "apply_channel": _weighted(config.APPLY_CHANNELS + ["线下村（居）委会"], [0.42, 0.28, 0.18, 0.12]),
            "register_date": _rand_date(),
            "status": status,
            "certify_status": certify,
            "last_certify": last_certify,
            "suspect_type": suspect,
        })
    return rows


def generate_payment_records() -> list:
    """生成 17 区县 × 18 个月发放台账（含增长趋势 + 月度波动，贴合实际）"""
    months = []
    for y in [2025, 2026]:
        for m in range(1, 13):
            if y == 2026 and m > 6:
                break
            months.append(f"{y}-{m:02d}")

    avg_month = sum(_parse_amount(b[1]) * b[2] for b in config.AGE_BAND_DIST)

    rows = []
    for district, w in config.DISTRICT_WEIGHTS.items():
        base_count = int(TOTAL_BENEFICIARIES * w / 100.0)
        for idx, month in enumerate(months):
            # 受益人数按月缓慢增长（年化约 3%）
            growth = 1.0 + idx * 0.0025
            # 月度随机波动（±4%）
            noise = 1.0 + random.uniform(-0.04, 0.04)
            count = int(base_count * growth * noise)
            rows.append({
                "district": district,
                "pay_month": month,
                "amount": round(count * avg_month / 10000.0, 2),
                "count": count,
            })
    return rows


def generate_notices() -> list:
    return [
        {"title": "关于做好 2026 年第三季度高龄补贴发放工作的通知",
         "category": "通知", "important": True,
         "publish_date": "2026-06-28",
         "content": "各区县民政局：请提前核对高龄补贴发放台账，确保 7 月资金按时足额发放到位；对认证过期、信息异常人员及时复核，严防错发漏发。"},
        {"title": "关于开展 2026 年度高龄补贴资格认证的公告",
         "category": "通知", "important": True,
         "publish_date": "2026-06-15",
         "content": "请年满 70 周岁的高龄补贴领取对象于 6 月底前完成年度资格认证，可通过「陕西民政通」等小程序线上认证或到户籍地村（居）委会现场认证。"},
        {"title": "西安市高龄老人生活保健补贴申领指南",
         "category": "政策", "important": False,
         "publish_date": "2026-05-20",
         "content": "具有西安市户籍、年满 70 周岁的老年人可申请高龄补贴；线上通过「陕西民政通」「三秦宝」「西民 e 站」申请，线下持身份证、户口簿向户籍地村（居）委会申请。"},
        {"title": "关于高龄补贴发放标准的说明",
         "category": "政策", "important": False,
         "publish_date": "2026-03-01",
         "content": "补贴按年龄段分四档：70-79 周岁 50 元/月、80-89 周岁 100 元/月、90-99 周岁 200 元/月、100 周岁及以上 360 元/月。"},
        {"title": "关于临潼区、鄠邑区高龄补贴资金拨付滞后问题的整改通报",
         "category": "预警", "important": True,
         "publish_date": "2026-04-10",
         "content": "针对省委基本民生保障专项督查反馈的临潼区、鄠邑区 2025 年度高龄补贴仅发放至二季度问题，两区已于 2026-03-31 前足额发放完毕，问题全部整改到位。"},
        {"title": "关于开展高龄补贴冒领、重复领取专项整治的通知",
         "category": "预警", "important": True,
         "publish_date": "2026-04-02",
         "content": "运用数据交叉比对，对疑似冒领、重复领取、死亡未停发等问题开展专项整治，逐人逐项核实，建立整改销号清单。"},
        {"title": "西安市高龄老人生活保健补贴实施办法（2026 年修订）",
         "category": "政策", "important": True,
         "publish_date": "2026-03-15",
         "content": "进一步规范高龄补贴申领、审核、发放、认证流程；明确四档补贴标准（50/100/200/360 元/月）；坚持保障对象属地管理、保障经费分级负担。"},
        {"title": "关于高龄补贴「免申即享、政策找人」改革的通知",
         "category": "政策", "important": True,
         "publish_date": "2026-03-01",
         "content": "依托户籍年龄库主动比对，对年满 70 周岁未申领人员主动推送提醒，实现从「人找政策」到「政策找人」。"},
        {"title": "陕西高龄补贴新政：合并复审与养老待遇认证",
         "category": "政策", "important": True,
         "publish_date": "2025-11-22",
         "content": "自 2025 年 12 月 1 日起，合并「高龄补贴复审」和「养老待遇领取认证」，一次办结，减少老人跑腿。"},
        {"title": "关于做好高龄补贴对象动态管理的通知",
         "category": "通知", "important": False,
         "publish_date": "2026-05-10",
         "content": "对户籍迁出、死亡、年龄跨档等情况及时更新台账，做到应发尽发、应停尽停。"},
        {"title": "关于 2026 年第二季度高龄补贴发放情况的通报",
         "category": "通知", "important": False,
         "publish_date": "2026-07-05",
         "content": "2026 年第二季度全市高龄补贴已足额发放，共惠及 104.1 万老人、发放 2.1 亿元，发放及时率 100%。"},
        {"title": "关于开展高龄补贴资金专项检查的通知",
         "category": "通知", "important": False,
         "publish_date": "2026-06-20",
         "content": "对省、市、区县三级财政分担资金到位情况进行专项检查，重点核查拨付进度与使用合规性。"},
        {"title": "高龄补贴「社保卡一卡通」发放指南",
         "category": "通知", "important": False,
         "publish_date": "2026-02-10",
         "content": "高龄补贴通过社保卡金融账户按月发放，请确保社保卡已激活金融功能；未激活的可到发卡银行网点办理。"},
        {"title": "关于部分区县资格认证率偏低的提醒",
         "category": "预警", "important": True,
         "publish_date": "2026-06-01",
         "content": "个别区县年度资格认证进度偏慢，请加快组织线上、线下、上门多种方式认证，确保按期完成。"},
    ]
