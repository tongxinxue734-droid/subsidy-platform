# -*- coding: utf-8 -*-
"""政务数据脱敏工具 —— 受益老人个人信息脱敏

脱敏规则（演示数据）：
- 姓名：只存「姓氏 + 称谓」，如 张大爷 / 李奶奶
- 年龄：只存年龄段（范围化），不存精确年龄
- 身份证：前 6 位保留 + 中间打码 + 后 4 位保留
- 手机号：前 3 位保留 + 中间打码 + 后 4 位保留
"""
import random

# 常见姓氏（演示用，非真实人员）
SURNAMES = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴",
            "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗",
            "郑", "梁", "谢", "宋", "唐", "韩", "冯", "于", "董", "萧"]

MALE_TITLES = ["大爷", "爷爷", "老汉", "伯"]
FEMALE_TITLES = ["大妈", "奶奶", "婆婆", "婶"]

PHONE_PREFIX = ["130", "131", "135", "136", "137", "138", "139",
                "150", "151", "155", "156", "158", "159",
                "186", "188", "189"]


def mask_name(gender: str = "男") -> str:
    """脱敏姓名：姓氏 + 称谓，如 张大爷 / 李奶奶"""
    surname = random.choice(SURNAMES)
    titles = MALE_TITLES if gender == "男" else FEMALE_TITLES
    return surname + random.choice(titles)


# 西安市身份证前 6 位中的区县代码（61=陕西 01=西安，后两位为区县）
_XIAN_DISTRICT_CODES = ["02", "03", "04", "11", "12", "13", "14", "15", "16", "17", "18", "22", "24"]


def mask_id_card() -> str:
    """脱敏身份证：6101XX********XXXX（6101 为西安市，XX 为区县代码）"""
    code = random.choice(_XIAN_DISTRICT_CODES)
    tail = "".join(str(random.randint(0, 9)) for _ in range(4))
    return "6101" + code + "********" + tail


def mask_phone() -> str:
    """脱敏手机号：138****2293"""
    prefix = random.choice(PHONE_PREFIX)
    tail = "".join(str(random.randint(0, 9)) for _ in range(4))
    return prefix + "****" + tail


def mask_bank_card() -> str:
    """脱敏银行卡：6222 **** **** 1234"""
    tail = "".join(str(random.randint(0, 9)) for _ in range(4))
    return "6222 **** **** " + tail


def mask_social_card() -> str:
    """脱敏社保卡：6101 **** **** 1234"""
    tail = "".join(str(random.randint(0, 9)) for _ in range(4))
    return "6101 **** **** " + tail


def mask_address(district: str = "") -> str:
    """脱敏家庭住址：仅保留区县，详细地址打码（如 雁塔区A路12号 → 雁塔区）"""
    return f"{district}（详细住址已脱敏）" if district else "详细住址已脱敏"


def mask_contact() -> str:
    """脱敏联系人：亲属称谓，如 张先生（子女）"""
    surname = random.choice(SURNAMES)
    title = random.choice(["先生", "女士"])
    rel = random.choice(["子女", "配偶", "亲属"])
    return f"{surname}{title}（{rel}）"


def mask_operator_name(full_name: str) -> str:
    """监管人员姓名脱敏：保留首尾、中间打码，如 王建国 → 王*国"""
    if not full_name:
        return "匿名"
    n = len(full_name)
    if n <= 2:
        return full_name[0] + "*" * (n - 1)
    return full_name[0] + "*" * (n - 2) + full_name[-1]
