"""ابزارهای عمومی متن و عدد (فارسی/عربی/انگلیسی) که در کل پروژه مشترک‌اند."""

import math
import re

_DIGITS_FROM = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
_DIGITS_TO = "01234567890123456789"
_TO_ASCII = str.maketrans(_DIGITS_FROM, _DIGITS_TO)
_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def normalize_digits(text: str) -> str:
    """تبدیل ارقام فارسی/عربی به انگلیسی و یکسان‌سازی جداکننده‌ها."""
    return (
        str(text)
        .translate(_TO_ASCII)
        .replace("٬", ",")
        .replace("٫", ".")
        .replace("\u2212", "-")  # علامت منفی یونیکد
    )


def to_persian_digits(value) -> str:
    return str(value).translate(_TO_PERSIAN)


def format_number(value, persian: bool = True) -> str:
    """قالب‌بندی عدد با جداکنندهٔ هزارگان."""
    if value is None:
        return "نامشخص"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "نامشخص"
        text = f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"
    elif isinstance(value, int) and not isinstance(value, bool):
        text = f"{value:,}"
    else:
        text = str(value)
    return to_persian_digits(text) if persian else text


_NUMBER_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")


def parse_number(value, allow_percent: bool = True):
    """
    تبدیل مقدار به int/float. اگر عدد نباشد None برمی‌گرداند.

    پشتیبانی از: ارقام فارسی، جداکنندهٔ هزارگان، علامت درصد، اعداد منفی داخل پرانتز.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value

    text = normalize_digits(str(value)).strip()
    if not text:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    if text.endswith("%"):
        if not allow_percent:
            return None
        text = text[:-1].strip()

    text = text.replace(",", "").replace(" ", "")
    if not _NUMBER_RE.match(text):
        return None

    number = float(text)
    if negative:
        number = -number
    return int(number) if number.is_integer() else number


def is_percent(value) -> bool:
    return isinstance(value, str) and value.strip().endswith("%") and (
        parse_number(value) is not None
    )


_TOTAL_LABELS = {
    "total", "grandtotal", "overalltotal", "subtotal", "sum", "alltotal",
    "جمعکل", "جمعکلی", "مجموع", "جمع", "جمعنهایی", "کل",
}


def is_total_label(value) -> bool:
    if value is None:
        return False
    normalized = re.sub(r"[\s:.\-_]+", "", str(value).strip().lower())
    return normalized in _TOTAL_LABELS


_PERSIAN_MONTHS = (
    "فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند|"
    "ژانویه|فوریه|مارس|آوریل|مه|ژوئن|ژوئیه|اوت|سپتامبر|اکتبر|نوامبر|دسامبر"
)
_EN_MONTHS = (
    "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
    "january|february|march|april|june|july|august|september|october|november|december"
)
_TEMPORAL_RE = re.compile(
    rf"(^|\W)({_PERSIAN_MONTHS})(\W|$)|"
    rf"\b({_EN_MONTHS})[a-z]*\b|"
    r"\b(1[34]\d\d|19\d\d|20\d\d)\b|"
    r"\bq[1-4]\b|\bweek\b|\bday\b|هفته|روز|فصل|سال|سه‌ماهه|trimester|quarter",
    re.IGNORECASE,
)


def looks_temporal(labels) -> bool:
    """آیا برچسب‌ها (بیشتر) زمانی‌اند؟ مثل ماه، سال، فصل."""
    labels = [normalize_digits(str(l)) for l in labels if l not in (None, "")]
    if len(labels) < 2:
        return False
    hits = sum(1 for l in labels if _TEMPORAL_RE.search(l))
    return hits / len(labels) >= 0.6
