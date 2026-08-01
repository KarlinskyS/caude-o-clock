"""Minimal i18n layer. Language is picked from macOS's own ordered
preferred-languages list (System Settings -> General -> Language & Region),
so the app speaks whatever language each user's Mac is set to — falls back
to English for anything we don't have a translation table for.

Override for testing without touching system settings:
    CCUSAGE_LANG=ja ./.venv/bin/python ccusagebar.py
"""
from __future__ import annotations

import os

from Foundation import NSLocale

_STRINGS = {
    "en": {
        "app_name": "Caude o'clock",
        "five_hour": "5-Hour Window",
        "weekly": "Weekly",
        "today_header": "TODAY (LOCAL SESSIONS)",
        "messages": "Messages",
        "tokens": "Tokens",
        "updated": "Updated {time}",
        "open_claude": "Open claude.ai ↗",
        "refresh": "⟳ Refresh",
        "quit": "Quit",
        "resets_in": "Resets in {h}h {m}m",
        "resets_in_short": "Resets in {m}m",
        "resets_on": "Resets {weekday} {time}",
        "notif_title": "Claude usage",
        "notif_threshold_subtitle": "5-hour window at {pct}%",
        "notif_threshold_message": "Heads up before you hit the wall.",
        "notif_reset_subtitle": "5-hour limit reset",
        "notif_reset_message": "Fresh window, go for it.",
        "err_no_creds": "Not signed in. Run `claude login` in Terminal to connect your Claude Code account.",
        "err_bad_creds": "Unexpected credentials format in Keychain.",
        "err_rate_limited": "Anthropic rate-limited this endpoint (429).{retry}",
        "err_rate_limited_retry": " Retry in {s}s.",
        "err_api": "API returned {code}: {body}",
        "err_unexpected": "Unexpected error: {err}",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    },
    "ru": {
        "app_name": "Caude o'clock",
        "five_hour": "5-часовое окно",
        "weekly": "Недельный лимит",
        "today_header": "СЕГОДНЯ (ЛОКАЛЬНЫЕ СЕССИИ)",
        "messages": "Сообщений",
        "tokens": "Токенов",
        "updated": "Обновлено {time}",
        "open_claude": "Открыть claude.ai ↗",
        "refresh": "⟳ Обновить",
        "quit": "Выйти",
        "resets_in": "Сброс через {h}ч {m}м",
        "resets_in_short": "Сброс через {m}м",
        "resets_on": "Сброс {weekday} {time}",
        "notif_title": "Лимит Claude",
        "notif_threshold_subtitle": "5-часовое окно: {pct}%",
        "notif_threshold_message": "Скоро упрёшься в лимит — притормози.",
        "notif_reset_subtitle": "5-часовой лимит сброшен",
        "notif_reset_message": "Свежее окно, можно продолжать.",
        "err_no_creds": "Не авторизовано. Выполни `claude login` в терминале, чтобы подключить аккаунт Claude Code.",
        "err_bad_creds": "Неожиданный формат credentials в Keychain.",
        "err_rate_limited": "Anthropic зарейтлимитил этот эндпоинт (429).{retry}",
        "err_rate_limited_retry": " Повтор через {s}с.",
        "err_api": "API вернул {code}: {body}",
        "err_unexpected": "Неожиданная ошибка: {err}",
        "weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    },
    "es": {
        "app_name": "Caude o'clock",
        "five_hour": "Ventana de 5 horas",
        "weekly": "Semanal",
        "today_header": "HOY (SESIONES LOCALES)",
        "messages": "Mensajes",
        "tokens": "Tokens",
        "updated": "Actualizado {time}",
        "open_claude": "Abrir claude.ai ↗",
        "refresh": "⟳ Actualizar",
        "quit": "Salir",
        "resets_in": "Se reinicia en {h}h {m}m",
        "resets_in_short": "Se reinicia en {m}m",
        "resets_on": "Se reinicia {weekday} {time}",
        "notif_title": "Uso de Claude",
        "notif_threshold_subtitle": "Ventana de 5 horas al {pct}%",
        "notif_threshold_message": "Aviso antes de llegar al límite.",
        "notif_reset_subtitle": "Límite de 5 horas reiniciado",
        "notif_reset_message": "Nueva ventana, adelante.",
        "err_no_creds": "No has iniciado sesión. Ejecuta `claude login` en la Terminal para conectar tu cuenta de Claude Code.",
        "err_bad_creds": "Formato de credenciales inesperado en Keychain.",
        "err_rate_limited": "Anthropic limitó este endpoint (429).{retry}",
        "err_rate_limited_retry": " Reintenta en {s}s.",
        "err_api": "La API devolvió {code}: {body}",
        "err_unexpected": "Error inesperado: {err}",
        "weekdays": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
    },
    "de": {
        "app_name": "Caude o'clock",
        "five_hour": "5-Stunden-Fenster",
        "weekly": "Wöchentlich",
        "today_header": "HEUTE (LOKALE SITZUNGEN)",
        "messages": "Nachrichten",
        "tokens": "Tokens",
        "updated": "Aktualisiert {time}",
        "open_claude": "claude.ai öffnen ↗",
        "refresh": "⟳ Aktualisieren",
        "quit": "Beenden",
        "resets_in": "Zurücksetzung in {h}Std {m}Min",
        "resets_in_short": "Zurücksetzung in {m}Min",
        "resets_on": "Zurücksetzung {weekday} {time}",
        "notif_title": "Claude-Nutzung",
        "notif_threshold_subtitle": "5-Stunden-Fenster bei {pct}%",
        "notif_threshold_message": "Achtung, bald ist das Limit erreicht.",
        "notif_reset_subtitle": "5-Stunden-Limit zurückgesetzt",
        "notif_reset_message": "Neues Fenster, leg los.",
        "err_no_creds": "Nicht angemeldet. Führe `claude login` im Terminal aus, um dein Claude-Code-Konto zu verbinden.",
        "err_bad_creds": "Unerwartetes Anmeldedatenformat im Schlüsselbund.",
        "err_rate_limited": "Anthropic hat diesen Endpunkt limitiert (429).{retry}",
        "err_rate_limited_retry": " Erneuter Versuch in {s}s.",
        "err_api": "API antwortete mit {code}: {body}",
        "err_unexpected": "Unerwarteter Fehler: {err}",
        "weekdays": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    },
    "fr": {
        "app_name": "Caude o'clock",
        "five_hour": "Fenêtre de 5 heures",
        "weekly": "Hebdomadaire",
        "today_header": "AUJOURD'HUI (SESSIONS LOCALES)",
        "messages": "Messages",
        "tokens": "Jetons",
        "updated": "Mis à jour {time}",
        "open_claude": "Ouvrir claude.ai ↗",
        "refresh": "⟳ Actualiser",
        "quit": "Quitter",
        "resets_in": "Réinitialisation dans {h}h {m}m",
        "resets_in_short": "Réinitialisation dans {m}m",
        "resets_on": "Réinitialisation {weekday} {time}",
        "notif_title": "Utilisation de Claude",
        "notif_threshold_subtitle": "Fenêtre de 5 heures à {pct}%",
        "notif_threshold_message": "Attention avant d'atteindre la limite.",
        "notif_reset_subtitle": "Limite de 5 heures réinitialisée",
        "notif_reset_message": "Nouvelle fenêtre, à vous de jouer.",
        "err_no_creds": "Non connecté. Exécutez `claude login` dans le Terminal pour connecter votre compte Claude Code.",
        "err_bad_creds": "Format d'identifiants inattendu dans le trousseau.",
        "err_rate_limited": "Anthropic a limité ce point de terminaison (429).{retry}",
        "err_rate_limited_retry": " Réessai dans {s}s.",
        "err_api": "L'API a renvoyé {code} : {body}",
        "err_unexpected": "Erreur inattendue : {err}",
        "weekdays": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    },
    "pt": {
        "app_name": "Caude o'clock",
        "five_hour": "Janela de 5 horas",
        "weekly": "Semanal",
        "today_header": "HOJE (SESSÕES LOCAIS)",
        "messages": "Mensagens",
        "tokens": "Tokens",
        "updated": "Atualizado {time}",
        "open_claude": "Abrir claude.ai ↗",
        "refresh": "⟳ Atualizar",
        "quit": "Sair",
        "resets_in": "Reinicia em {h}h {m}m",
        "resets_in_short": "Reinicia em {m}m",
        "resets_on": "Reinicia {weekday} {time}",
        "notif_title": "Uso do Claude",
        "notif_threshold_subtitle": "Janela de 5 horas em {pct}%",
        "notif_threshold_message": "Atenção antes de atingir o limite.",
        "notif_reset_subtitle": "Limite de 5 horas reiniciado",
        "notif_reset_message": "Nova janela, pode continuar.",
        "err_no_creds": "Não conectado. Execute `claude login` no Terminal para conectar sua conta do Claude Code.",
        "err_bad_creds": "Formato de credenciais inesperado no Keychain.",
        "err_rate_limited": "A Anthropic limitou este endpoint (429).{retry}",
        "err_rate_limited_retry": " Tente novamente em {s}s.",
        "err_api": "A API retornou {code}: {body}",
        "err_unexpected": "Erro inesperado: {err}",
        "weekdays": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
    },
    "ja": {
        "app_name": "Caude o'clock",
        "five_hour": "5時間ウィンドウ",
        "weekly": "週間",
        "today_header": "今日（ローカルセッション）",
        "messages": "メッセージ数",
        "tokens": "トークン数",
        "updated": "更新: {time}",
        "open_claude": "claude.ai を開く ↗",
        "refresh": "⟳ 更新",
        "quit": "終了",
        "resets_in": "{h}時間{m}分後にリセット",
        "resets_in_short": "{m}分後にリセット",
        "resets_on": "{weekday} {time} にリセット",
        "notif_title": "Claude の使用状況",
        "notif_threshold_subtitle": "5時間ウィンドウが{pct}%に到達",
        "notif_threshold_message": "上限に達する前にご確認ください。",
        "notif_reset_subtitle": "5時間制限がリセットされました",
        "notif_reset_message": "新しいウィンドウです。どうぞ。",
        "err_no_creds": "サインインしていません。ターミナルで `claude login` を実行して Claude Code アカウントを接続してください。",
        "err_bad_creds": "Keychain 内の認証情報の形式が予期しないものです。",
        "err_rate_limited": "Anthropic によりこのエンドポイントがレート制限されました (429)。{retry}",
        "err_rate_limited_retry": " {s}秒後に再試行します。",
        "err_api": "API が {code} を返しました: {body}",
        "err_unexpected": "予期しないエラー: {err}",
        "weekdays": ["月", "火", "水", "木", "金", "土", "日"],
    },
    "zh": {
        "app_name": "Caude o'clock",
        "five_hour": "5小时窗口",
        "weekly": "每周",
        "today_header": "今天（本地会话）",
        "messages": "消息数",
        "tokens": "令牌数",
        "updated": "更新于 {time}",
        "open_claude": "打开 claude.ai ↗",
        "refresh": "⟳ 刷新",
        "quit": "退出",
        "resets_in": "{h}小时{m}分钟后重置",
        "resets_in_short": "{m}分钟后重置",
        "resets_on": "{weekday} {time} 重置",
        "notif_title": "Claude 用量",
        "notif_threshold_subtitle": "5小时窗口已达 {pct}%",
        "notif_threshold_message": "即将达到限额，请留意。",
        "notif_reset_subtitle": "5小时限额已重置",
        "notif_reset_message": "新窗口已开始，请继续。",
        "err_no_creds": "尚未登录。请在终端中运行 `claude login` 以连接您的 Claude Code 账户。",
        "err_bad_creds": "钥匙串中的凭据格式异常。",
        "err_rate_limited": "Anthropic 对该接口进行了限流 (429)。{retry}",
        "err_rate_limited_retry": " 将在 {s} 秒后重试。",
        "err_api": "API 返回 {code}：{body}",
        "err_unexpected": "意外错误：{err}",
        "weekdays": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    },
}

# Languages that conventionally use a 12-hour clock with AM/PM in software UI.
_TWELVE_HOUR_LANGS = {"en"}


def _detect_lang() -> str:
    forced = os.environ.get("CCUSAGE_LANG")
    if forced and forced in _STRINGS:
        return forced

    try:
        preferred = list(NSLocale.preferredLanguages())
    except Exception:
        preferred = []

    for tag in preferred:
        code = str(tag).replace("_", "-").split("-")[0].lower()
        if code in _STRINGS:
            return code
    return "en"


LANG = _detect_lang()
USES_12H_CLOCK = LANG in _TWELVE_HOUR_LANGS


def t(key: str, **kwargs) -> str:
    table = _STRINGS.get(LANG, _STRINGS["en"])
    template = table.get(key)
    if template is None:
        template = _STRINGS["en"].get(key, key)
    return template.format(**kwargs) if kwargs else template


def weekday_name(idx: int) -> str:
    table = _STRINGS.get(LANG, _STRINGS["en"])
    return table["weekdays"][idx]
