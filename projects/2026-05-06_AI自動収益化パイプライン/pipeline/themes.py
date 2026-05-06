"""共通テーマ／ネタ供給モジュール。

日付をシードに決定論的にローテーションさせるため、同じ日に複数回呼んでも
同じ素材が返る。日が変われば自然にローテートする。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Theme:
    slug: str
    title_ja: str
    title_en: str
    keywords_ja: list[str]
    keywords_en: list[str]
    angle: str  # 切り口


THEMES: list[Theme] = [
    Theme(
        slug="quiet-life-takaoka",
        title_ja="静かな地方都市で暮らすという贅沢",
        title_en="A quiet life in a small Japanese town",
        keywords_ja=["高岡", "富山", "地方暮らし", "静かな日常"],
        keywords_en=["Takaoka", "Toyama", "quiet life", "Japan"],
        angle="都市の速度から離れて見える小さな豊かさ",
    ),
    Theme(
        slug="amaharashi-coast",
        title_ja="雨晴海岸から見る立山連峰",
        title_en="Tateyama Alps seen from Amaharashi Coast",
        keywords_ja=["雨晴海岸", "立山連峰", "富山湾", "絶景"],
        keywords_en=["Amaharashi", "Tateyama", "Toyama Bay", "scenic"],
        angle="海越しに3000m級の山が並ぶ世界的にも稀な景観",
    ),
    Theme(
        slug="ai-side-hustle-50s",
        title_ja="50代から始めるAI副業の現実",
        title_en="Starting an AI side hustle in your 50s",
        keywords_ja=["AI副業", "50代", "個人収益", "在宅"],
        keywords_en=["AI side hustle", "50s", "remote work", "Japan"],
        angle="派手な成功談ではなく等身大の試行錯誤",
    ),
    Theme(
        slug="seasonal-food-toyama",
        title_ja="富山の季節の食卓",
        title_en="Seasonal food in Toyama",
        keywords_ja=["富山", "白えび", "ホタルイカ", "ます寿司"],
        keywords_en=["Toyama", "shiroebi", "firefly squid", "Japanese food"],
        angle="土地の食材が暮らしのリズムを作る",
    ),
    Theme(
        slug="from-employee-to-solo",
        title_ja="会社員から個人収益へ移行する一年目",
        title_en="First year from employee to solo income",
        keywords_ja=["会社員", "個人事業", "副業", "独立"],
        keywords_en=["solo income", "freelance", "transition", "Japan"],
        angle="数字と心の両方の変化を記録する",
    ),
    Theme(
        slug="takaoka-craft",
        title_ja="高岡銅器と400年の手仕事",
        title_en="Takaoka copperware and 400 years of craft",
        keywords_ja=["高岡銅器", "伝統工芸", "高岡", "ものづくり"],
        keywords_en=["Takaoka copperware", "Japanese craft", "tradition"],
        angle="日常に溶け込む工芸品の存在感",
    ),
    Theme(
        slug="morning-routine-rural",
        title_ja="地方暮らしの朝のルーティン",
        title_en="A morning routine in rural Japan",
        keywords_ja=["朝活", "ルーティン", "地方暮らし"],
        keywords_en=["morning routine", "rural Japan", "slow living"],
        angle="一日の質は朝の30分で決まる",
    ),
]


def theme_for(d: date | None = None) -> Theme:
    """日付からテーマを決定論的に選ぶ。"""
    d = d or date.today()
    digest = hashlib.sha256(d.isoformat().encode()).digest()
    idx = digest[0] % len(THEMES)
    return THEMES[idx]


def slug_for(d: date | None = None) -> str:
    return theme_for(d).slug
