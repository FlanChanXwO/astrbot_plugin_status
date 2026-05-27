from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metric:
    """
    单个指标的数据模型
    """

    icon_class: str  # 指标图标的CSS类
    label: str  # 指标名称
    value: str  # 指标值
    offset: float  # 指标的偏移量


@dataclass
class StatusPayload:
    """
    状态页面渲染所需的数据
    """

    css_style: str  # 内联的CSS样式
    bot_name: str  # 机器人名称
    metrics: list[Metric]  # 指标列表
    cpu_name: str  # CPU名称
    os_name: str  # 操作系统名称
    project_version: str  # 项目版本
    plugin_count: str  # 插件数量 (格式化后的字符串)
    upload_speed: str  # 上传速度
    download_speed: str  # 下载速度
    dashboard_name: str  # 仪表盘名称
    uptime: str  # 运行时间
