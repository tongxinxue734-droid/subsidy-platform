# -*- coding: utf-8 -*-
"""SQLAlchemy ORM 数据模型 —— 西安市高龄补贴监管平台"""
from datetime import datetime

from sqlalchemy import (Column, Integer, String, Boolean, DateTime,
                        Float, Text, JSON)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """监管账号（三级权限：1 市级 / 2 区县 / 3 街道）"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    name = Column(String(64), nullable=False)
    role_level = Column(Integer, nullable=False)          # 1 市级 / 2 区县 / 3 街道
    district = Column(String(32), default="")             # 管辖的区县（市级为空）
    street = Column(String(32), default="")               # 管辖的街道（街道级账号）
    dept_name = Column(String(64), default="")            # 部门名，如 雁塔区民政局
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Elder(Base):
    """受益老人档案（脱敏存储：姓名姓氏+称谓、证件/手机打码、年龄范围化）"""
    __tablename__ = "elders"
    id = Column(Integer, primary_key=True)
    district = Column(String(32), index=True, nullable=False)   # 区县
    street = Column(String(32), index=True, default="")         # 街道
    name = Column(String(16), nullable=False)                   # 脱敏姓名：张大爷/李奶奶
    gender = Column(String(4), default="男")                    # 男 / 女
    age_band = Column(String(16), default="70-79 周岁")          # 年龄段（范围化）
    standard = Column(String(16), default="50 元/月")            # 补贴标准
    id_card = Column(String(32), default="")                    # 脱敏身份证
    phone = Column(String(32), default="")                      # 脱敏手机
    bank_card = Column(String(32), default="")                  # 脱敏银行卡
    social_card = Column(String(32), default="")                # 脱敏社保卡
    address = Column(String(64), default="")                    # 脱敏家庭住址
    contact = Column(String(32), default="")                    # 脱敏联系人
    apply_channel = Column(String(32), default="线上小程序")     # 申领渠道
    register_date = Column(String(16), default="")              # 建档日期 YYYY-MM-DD
    status = Column(String(8), default="在发")                  # 在发 / 停发 / 待认证
    certify_status = Column(String(8), default="已认证")         # 已认证 / 待认证 / 认证过期
    last_certify = Column(String(16), default="")               # 最近认证月份 YYYY-MM
    suspect_type = Column(String(16), default="")               # 疑点类型（空=正常）
    created_at = Column(DateTime, default=datetime.now)


class PaymentRecord(Base):
    """月度发放台账（区县 × 月份聚合）"""
    __tablename__ = "payment_records"
    id = Column(Integer, primary_key=True)
    district = Column(String(32), index=True, nullable=False)
    pay_month = Column(String(16), index=True, nullable=False)  # 2026-06
    amount = Column(Float, default=0)                           # 当月发放金额（万元）
    count = Column(Integer, default=0)                          # 受益人数


class Notice(Base):
    """通知公告"""
    __tablename__ = "notices"
    id = Column(Integer, primary_key=True)
    title = Column(String(128), nullable=False)
    category = Column(String(16), default="通知")               # 通知 / 政策 / 预警
    content = Column(Text, default="")
    publish_date = Column(String(16), default="")
    important = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class CertifyRecord(Base):
    """年度资格认证记录（脱敏：仅存认证月份 / 方式 / 结果）"""
    __tablename__ = "certify_records"
    id = Column(Integer, primary_key=True)
    elder_id = Column(Integer, index=True, nullable=False)      # 关联 Elder.id
    certify_date = Column(String(16), default="")               # YYYY-MM
    method = Column(String(32), default="")                     # 线上小程序 / 线下村居 / 上门
    result = Column(String(16), default="通过")                 # 通过 / 未通过 / 待认证


class ElderPayment(Base):
    """个人月度发放记录（脱敏，供档案详情时间线）"""
    __tablename__ = "elder_payments"
    id = Column(Integer, primary_key=True)
    elder_id = Column(Integer, index=True, nullable=False)      # 关联 Elder.id
    pay_month = Column(String(16), index=True, nullable=False)  # YYYY-MM
    amount = Column(Float, default=0)                           # 当月实发金额（元）
    status = Column(String(16), default="已发放")               # 已发放 / 停发 / 待发放


class Application(Base):
    """申领工单（街道审核 → 区县审批 → 建档）"""
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    apply_no = Column(String(32), unique=True, nullable=False)  # 申领编号
    district = Column(String(32), index=True, nullable=False)
    street = Column(String(32), index=True, default="")
    name = Column(String(16), nullable=False)                   # 脱敏姓名
    gender = Column(String(4), default="男")
    age_band = Column(String(16), default="70-79 周岁")
    standard = Column(String(16), default="50 元/月")
    channel = Column(String(32), default="线上小程序")           # 申领渠道
    id_card = Column(String(32), default="")                    # 身份证（脱敏）
    phone = Column(String(32), default="")                      # 手机（脱敏）
    address = Column(String(64), default="")                    # 住址（脱敏）
    bank_card = Column(String(32), default="")                  # 银行卡（脱敏）
    remark = Column(String(128), default="")                    # 备注
    status = Column(String(16), default="待街道审核")            # 待街道审核 / 待区县审批 / 已建档 / 已驳回
    elder_id = Column(Integer, default=0)                       # 建档后的档案 id（0=未建档）
    created_at = Column(DateTime, default=datetime.now)


class ElderChange(Base):
    """待遇变更记录（调档 / 停发 / 恢复 / 死亡终止 / 迁出）"""
    __tablename__ = "elder_changes"
    id = Column(Integer, primary_key=True)
    elder_id = Column(Integer, index=True, nullable=False)
    change_type = Column(String(16), nullable=False)            # 调档 / 停发 / 恢复 / 死亡终止 / 迁出
    before_value = Column(String(64), default="")
    after_value = Column(String(64), default="")
    reason = Column(String(64), default="")
    operator = Column(String(32), default="")
    created_at = Column(DateTime, default=datetime.now)


class WorkOrder(Base):
    """监管工单（稽核 / 数据比对 / 政策找人 / 诉求）"""
    __tablename__ = "work_orders"
    id = Column(Integer, primary_key=True)
    work_no = Column(String(32), unique=True, nullable=False)
    category = Column(String(16), default="稽核")               # 稽核 / 比对 / 政策找人 / 诉求
    source = Column(String(32), default="")                     # 智能稽核 / 卫健死亡 / 12345热线 等
    elder_id = Column(Integer, index=True, default=0)           # 关联档案（政策找人为 0）
    district = Column(String(32), index=True, default="")
    street = Column(String(32), default="")
    name = Column(String(16), default="")                       # 脱敏姓名
    gender = Column(String(4), default="")
    age_band = Column(String(16), default="")
    title = Column(String(128), default="")
    description = Column(Text, default="")
    level = Column(String(8), default="黄色")                   # 红色 / 橙色 / 黄色
    status = Column(String(16), default="待处理")               # 待处理 / 整改中 / 待复核 / 已销号
    handler = Column(String(32), default="")
    satisfaction = Column(String(16), default="")               # 诉求满意度：满意 / 一般 / 不满意
    created_at = Column(DateTime, default=datetime.now)


class CompareTask(Base):
    """跨部门数据比对任务（公安 / 卫健 / 殡葬 / 社保）"""
    __tablename__ = "compare_tasks"
    id = Column(Integer, primary_key=True)
    task_no = Column(String(32), unique=True, nullable=False)
    source = Column(String(32), default="")                     # 公安户籍 / 卫健死亡 / 殡葬火化 / 社保
    district = Column(String(32), default="")
    compared_count = Column(Integer, default=0)                 # 比对人数
    hit_count = Column(Integer, default=0)                      # 命中人数
    status = Column(String(16), default="已完成")
    compared_at = Column(String(16), default="")


class AuditLog(Base):
    """操作审计日志（留痕）"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_name = Column(String(32), default="")
    role = Column(String(16), default="")
    action = Column(String(64), default="")
    target = Column(String(128), default="")
    created_at = Column(DateTime, default=datetime.now)


class Message(Base):
    """消息中心（预警 / 通知 / 待办）"""
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    category = Column(String(16), default="通知")               # 预警 / 通知 / 政策 / 待办
    title = Column(String(128), default="")
    content = Column(Text, default="")
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class SpotCheck(Base):
    """双随机抽查任务（随机抽对象 + 随机派人员）"""
    __tablename__ = "spot_checks"
    id = Column(Integer, primary_key=True)
    task_no = Column(String(32), unique=True, nullable=False)
    name = Column(String(64), default="")
    district = Column(String(32), default="")
    elder_count = Column(Integer, default=0)                    # 抽查人数
    checker_count = Column(Integer, default=0)                  # 检查人员数
    status = Column(String(16), default="检查中")               # 检查中 / 已完成
    created_at = Column(DateTime, default=datetime.now)


class SpotCheckRecord(Base):
    """双随机抽查记录（任务 → 老人）"""
    __tablename__ = "spot_check_records"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, index=True, nullable=False)
    elder_id = Column(Integer, default=0)
    archive_no = Column(String(32), default="")
    name = Column(String(16), default="")
    district = Column(String(32), default="")
    checker = Column(String(32), default="")                    # 检查人员（脱敏）
    result = Column(String(16), default="待检查")               # 待检查 / 正常 / 发现问题
    created_at = Column(DateTime, default=datetime.now)
