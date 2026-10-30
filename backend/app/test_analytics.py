import json
import re
from pathlib import Path
from pprint import pprint
from typing import Any

from services.analytics_service import (
    calculate_sales_metrics,
    build_management_context,
)

from services.llm_client import generate_management_narrative
from services.pdf_processor import extract_pdf_text

# =========================================================
# 1. مسیر فایل‌ها
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

PDF_PATH = BASE_DIR.parent / "data" / "sample_sales_report_for_rag.pdf"
OUTPUT_PATH = BASE_DIR / "management_report.json"


# =========================================================
# 2. ابزارهای عمومی
# =========================================================


def print_section(title: str):
    print(f"\n{'=' * 15} {title} {'=' * 15}")


def validate_required_fields(data: dict, fields: list):
    for field in fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")


def collect_text_values(
    data: Any,
    path: str = "root",
) -> list[tuple[str, str]]:

    results = []

    if isinstance(data, str):
        results.append((path, data))

    elif isinstance(data, dict):
        for key, value in data.items():
            results.extend(collect_text_values(value, f"{path}.{key}"))

    elif isinstance(data, list):
        for index, value in enumerate(data):
            results.extend(collect_text_values(value, f"{path}[{index}]"))

    return results


def debug_text(label: str, text: str):
    print(f"\n========== {label} ==========")
    print(repr(text))


def print_text_debug(data: dict):
    print_section("STRING DEBUG")

    for path, text in collect_text_values(data):
        print(f"\n{path}:")
        print(repr(text))


# =========================================================
# 3. مقایسه دقیق متن در مراحل مختلف
# =========================================================


def compare_narratives(
    original: dict,
    current: dict,
    stage: str,
):
    """
    مقایسه بخش‌های متنی دو گزارش.
    اگر حتی یک کاراکتر تغییر کرده باشد، محل آن را مشخص می‌کند.
    """

    print_section(f"NARRATIVE COMPARISON: {stage}")

    original_values = dict(collect_text_values(original))
    current_values = dict(collect_text_values(current))

    if original_values.keys() != current_values.keys():
        raise ValueError(f"Text structure changed during {stage}")

    differences = []

    for path in original_values:

        old_text = original_values[path]
        new_text = current_values[path]

        if old_text != new_text:

            differences.append(path)

            print(f"\nChanged field: {path}")
            print("BEFORE:", repr(old_text))
            print("AFTER: ", repr(new_text))

            limit = min(len(old_text), len(new_text))

            for index in range(limit):
                if old_text[index] != new_text[index]:

                    print("First difference at:", index)
                    print(
                        "Before character:",
                        repr(old_text[index]),
                        f"U+{ord(old_text[index]):04X}",
                    )
                    print(
                        "After character:",
                        repr(new_text[index]),
                        f"U+{ord(new_text[index]):04X}",
                    )

                    print(
                        "Before context:",
                        repr(old_text[max(0, index - 15) : index + 25]),
                    )

                    print(
                        "After context:",
                        repr(new_text[max(0, index - 15) : index + 25]),
                    )

                    break

            if len(old_text) != len(new_text):
                print(
                    "Length:",
                    len(old_text),
                    "->",
                    len(new_text),
                )

    if differences:
        raise ValueError(f"Text changed during {stage}: {differences}")

    print("All narrative strings are identical.")


# =========================================================
# 4. اعتبارسنجی فاصله‌گذاری فارسی
# =========================================================

SUSPICIOUS_SPACING_PATTERNS = [
    "میزانتغییر",
    "ثبت شدهو",
    "بهسفارش",
    "ارزیابیشود",
    "بررسیشود",
    "مشاهدهشده",
    "رتبه ۱را",
    "رتبه ۲را",
    "رتبه ۳را",
    "رتبه ۴را",
    "رتبه ۱رادارد",
    "رتبه ۲رادارد",
    "رتبه ۳رادارد",
    "رتبه ۴رادارد",
    "فوریه۲۰۲۶",
    "ژانویه۲۰۲۶",
    "مارس۲۰۲۶",
    "برابر با",
]


def validate_persian_spacing(data: dict):

    text_values = collect_text_values(data)
    errors = []

    forbidden_phrases = [
        "ثبت شدهو",
        "بهسفارش",
        "ارزیابیشود",
        "بررسیشود",
        "مشاهدهشده",
        "رتبه ۱را",
        "رتبه ۲را",
        "رتبه ۳را",
        "رتبه ۴را",
        "فوریه۲۰۲۶",
        "ژانویه۲۰۲۶",
        "مارس۲۰۲۶",
        "۴.۰۵درصد",
    ]

    required_phrases = [
        "ثبت شده و",
        "به سفارش",
        "ارزیابی شود",
        "رتبه ۱ را",
        "رتبه ۲ را",
        "رتبه ۳ را",
        "رتبه ۴ را",
    ]

    print_section("PERSIAN TEXT VALIDATION")

    if not text_values:
        raise ValueError("No text values found.")

    for path, text in text_values:

        for phrase in forbidden_phrases:
            if phrase in text:
                errors.append(f"{path}: forbidden phrase {phrase!r}")

    all_text = "\n".join(text for _, text in text_values)

    for phrase in required_phrases:
        if phrase not in all_text:
            errors.append(f"Required phrase not found: {phrase!r}")

    if errors:
        for error in errors:
            print(error)

        raise ValueError(f"Persian spacing validation failed: {len(errors)} issue(s).")

    print(f"Checked {len(text_values)} text value(s).")
    print("Persian spacing validation passed.")


# =========================================================
# 5. اعتبارسنجی ساختار narrative
# =========================================================


def validate_narrative(narrative: dict):

    if not isinstance(narrative, dict):
        raise TypeError("Narrative must be a dictionary.")

    required_sections = [
        "executive_summary",
        "monthly_analysis",
        "regional_analysis",
        "category_analysis",
        "risks",
        "recommendations",
    ]

    validate_required_fields(narrative, required_sections)

    string_sections = [
        "executive_summary",
        "monthly_analysis",
        "regional_analysis",
        "category_analysis",
    ]

    for section in string_sections:

        if not isinstance(narrative[section], str):
            raise TypeError(f"{section} must be a string.")

        if not narrative[section].strip():
            raise ValueError(f"{section} is empty.")

    for section in ["risks", "recommendations"]:

        if not isinstance(narrative[section], list):
            raise TypeError(f"{section} must be a list.")

        if not all(isinstance(item, str) for item in narrative[section]):
            raise TypeError(f"Invalid item in {section}.")

        if not narrative[section]:
            raise ValueError(f"{section} is empty.")

    print("Narrative structure validation passed.")


# =========================================================
# 6. ذخیره JSON
# =========================================================


def save_json(data: dict, output_path: Path):

    with output_path.open("w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )


# =========================================================
# 7. محاسبه نسبت مرجوعی به سفارش
# =========================================================


def calculate_monthly_returns_ratios(analytics: dict) -> list:

    results = []

    monthly_sales = analytics.get("monthly_sales", [])

    for item in monthly_sales:

        orders = item.get("orders")
        returns = item.get("returns")

        valid_orders = (
            isinstance(orders, (int, float))
            and not isinstance(orders, bool)
            and orders > 0
        )

        valid_returns = (
            isinstance(returns, (int, float))
            and not isinstance(returns, bool)
            and returns >= 0
        )

        if valid_orders and valid_returns:
            ratio = round((returns / orders) * 100, 2)
        else:
            ratio = None

        results.append(
            {
                "month": item.get("month"),
                "orders": orders,
                "returns": returns,
                "returns_to_orders_ratio_percentage": ratio,
            }
        )

    previous_ratio = None

    for item in results:

        current_ratio = item["returns_to_orders_ratio_percentage"]

        item["previous_ratio_percentage"] = previous_ratio

        if current_ratio is None or previous_ratio is None:
            item["ratio_change_percentage_points"] = None
        else:
            item["ratio_change_percentage_points"] = round(
                current_ratio - previous_ratio,
                2,
            )

        if current_ratio is not None:
            previous_ratio = current_ratio

    return results


def validate_monthly_returns_ratios(returns_analysis: list):

    for item in returns_analysis:

        orders = item.get("orders")
        returns = item.get("returns")
        ratio = item.get("returns_to_orders_ratio_percentage")

        if orders is None or returns is None:
            continue

        if (
            isinstance(orders, bool)
            or isinstance(returns, bool)
            or orders <= 0
            or returns < 0
        ):
            raise ValueError(f"Invalid order/return count in {item.get('month')}")

        expected_ratio = round((returns / orders) * 100, 2)

        if ratio != expected_ratio:
            raise ValueError(f"Returns ratio mismatch in {item.get('month')}")

    print("Monthly returns ratios validation passed.")


# =========================================================
# 8. بررسی تحلیل ماهانه
# =========================================================


def debug_monthly_analysis(narrative: dict):

    print_section("MONTHLY ANALYSIS DEBUG")

    monthly_text = narrative.get("monthly_analysis", "")

    if not isinstance(monthly_text, str):
        raise TypeError("monthly_analysis must be a string.")

    print("\nOriginal text:")
    print(monthly_text)

    print("\nASCII representation:")
    print(ascii(monthly_text))

    checks = [
        ("به سفارش", "بهسفارش"),
        ("ثبت شده و", "ثبت شدهو"),
        ("ارزیابی شود", "ارزیابیشود"),
        ("بررسی شود", "بررسیشود"),
        ("رتبه ۳ را", "رتبه ۳را"),
    ]

    print("\nSpacing checks:")

    for correct_phrase, broken_phrase in checks:

        print(f"\nCorrect: {correct_phrase}")
        print("Exists:", correct_phrase in monthly_text)

        print(f"Broken: {broken_phrase}")
        print("Exists:", broken_phrase in monthly_text)

    print("\n--- END MONTHLY ANALYSIS DEBUG ---")


# =========================================================
# 9. اجرای pipeline
# =========================================================


def main():

    # -----------------------------------------------------
    # مرحله 1: استخراج PDF
    # -----------------------------------------------------

    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF file not found: {PDF_PATH}")

    print_section("PDF EXTRACTION")

    print(f"Source file: {PDF_PATH}")

    pdf_data = extract_pdf_text(str(PDF_PATH))

    if not isinstance(pdf_data, dict) or not pdf_data:
        raise ValueError("PDF extraction returned invalid data.")

    tables = pdf_data.get("tables", [])

    if not tables:
        raise ValueError("No tables extracted from PDF.")

    page_count = pdf_data.get("page_count", 0)
    table_count = pdf_data.get("table_count", len(tables))

    print(f"\nPages: {page_count}")
    print(f"Tables: {table_count}")

    # -----------------------------------------------------
    # مرحله 2: نمایش جداول
    # -----------------------------------------------------

    print_section("EXTRACTED TABLE HEADERS")

    for index, table in enumerate(tables, start=1):

        print(f"\nTable {index}:")
        print("Headers:", repr(table.get("headers", [])))

        print("First rows:")
        pprint(table.get("rows", [])[:3], width=100)

    # -----------------------------------------------------
    # مرحله 3: محاسبه analytics
    # -----------------------------------------------------

    print_section("SALES ANALYTICS")

    analytics = calculate_sales_metrics(tables)

    if not isinstance(analytics, dict) or not analytics:
        raise ValueError("Invalid analytics result.")

    validate_required_fields(
        analytics,
        [
            "summary",
            "monthly_sales",
            "monthly_analysis",
            "regions",
            "categories",
            "insights",
        ],
    )

    pprint(analytics, width=100)

    # -----------------------------------------------------
    # مرحله 4: نسبت مرجوعی
    # -----------------------------------------------------

    print_section("MONTHLY RETURNS ANALYSIS")

    monthly_returns_analysis = calculate_monthly_returns_ratios(analytics)

    validate_monthly_returns_ratios(monthly_returns_analysis)

    pprint(monthly_returns_analysis, width=100)

    # -----------------------------------------------------
    # مرحله 5: اطلاعات مدیریتی
    # -----------------------------------------------------

    print_section("MANAGEMENT CONTEXT")

    management_context = build_management_context(analytics)

    if not isinstance(management_context, dict):
        raise ValueError("Invalid management context.")

    pprint(management_context, width=100)

    # -----------------------------------------------------
    # مرحله 6: تولید narrative
    # -----------------------------------------------------

    print_section("MANAGEMENT NARRATIVE")

    narrative = generate_management_narrative(
        analytics,
        management_context,
    )

    validate_narrative(narrative)

    # یک نسخه مستقل برای مقایسه‌های بعدی
    original_narrative = json.loads(
        json.dumps(
            narrative,
            ensure_ascii=False,
            allow_nan=False,
        )
    )

    debug_monthly_analysis(narrative)

    print_text_debug(narrative)

    # -----------------------------------------------------
    # مرحله 7: ساخت گزارش
    # -----------------------------------------------------

    print_section("BUILDING FINAL REPORT")

    management_report = {
        "metrics": analytics,
        "management_context": management_context,
        "monthly_returns_analysis": monthly_returns_analysis,
        "narrative": narrative,
        "metadata": {
            "currency": "IRR",
            "currency_name": "ریال",
            "source_file": PDF_PATH.name,
            "page_count": page_count,
            "table_count": table_count,
        },
    }

    # بررسی اینکه ساخت گزارش متن را تغییر نداده باشد
    compare_narratives(
        original_narrative,
        management_report["narrative"],
        "AFTER REPORT BUILD",
    )

    # -----------------------------------------------------
    # مرحله 8: اعتبارسنجی متن
    # -----------------------------------------------------

    print_section("PERSIAN SPACING VALIDATION")

    validate_persian_spacing(narrative)

    # -----------------------------------------------------
    # مرحله 9: اعتبارسنجی ساختار
    # -----------------------------------------------------

    print_section("REPORT STRUCTURE VALIDATION")

    validate_required_fields(
        management_report,
        [
            "metrics",
            "management_context",
            "monthly_returns_analysis",
            "narrative",
            "metadata",
        ],
    )

    print("Report structure validation passed.")

    # -----------------------------------------------------
    # مرحله 10: کنترل یکسان بودن داده‌ها
    # -----------------------------------------------------

    print_section("CONSISTENCY CHECK")

    compare_narratives(
        original_narrative,
        management_report["narrative"],
        "CONSISTENCY CHECK",
    )

    print("All consistency checks passed.")

    # -----------------------------------------------------
    # مرحله 11: JSON serialization
    # -----------------------------------------------------

    print_section("JSON SERIALIZATION")

    json_before = json.dumps(
        management_report,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    compare_narratives(
        original_narrative,
        management_report["narrative"],
        "AFTER JSON DUMPS",
    )

    # خواندن مجدد از رشته JSON
    json_loaded = json.loads(json_before)

    compare_narratives(
        original_narrative,
        json_loaded["narrative"],
        "AFTER JSON LOADS",
    )

    print("JSON serialization validation passed.")

    # -----------------------------------------------------
    # مرحله 12: ذخیره فایل
    # -----------------------------------------------------

    print_section("SAVING REPORT")

    save_json(management_report, OUTPUT_PATH)

    print(f"\nSaved to: {OUTPUT_PATH}")

    # -----------------------------------------------------
    # مرحله 13: خواندن و بررسی فایل ذخیره‌شده
    # -----------------------------------------------------

    print_section("SAVED JSON VALIDATION")

    with OUTPUT_PATH.open("r", encoding="utf-8") as file:
        saved_report = json.load(file)

    print_section("FINAL TEXT VERIFICATION")

    for path, text in collect_text_values(saved_report["narrative"]):

        print(f"\n{path}")
        print(ascii(text))

    validate_persian_spacing(saved_report["narrative"])
    
    if saved_report != management_report:
        raise ValueError("Saved JSON does not match original report.")

    compare_narratives(
        original_narrative,
        saved_report["narrative"],
        "AFTER FILE SAVE AND LOAD",
    )

    validate_narrative(saved_report["narrative"])
    validate_persian_spacing(saved_report["narrative"])

    print("Saved JSON validation passed.")

    # -----------------------------------------------------
    # مرحله 14: نمایش گزارش نهایی
    # -----------------------------------------------------

    print_section("FINAL MANAGEMENT REPORT")

    print(
        json.dumps(
            saved_report,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
    )

    # -----------------------------------------------------
    # پایان
    # -----------------------------------------------------

    print_section("PIPELINE COMPLETED")

    print("PDF extraction: OK")
    print("Sales analytics: OK")
    print("Monthly returns analysis: OK")
    print("Management context: OK")
    print("Management narrative: OK")
    print("Persian text validation: OK")
    print("Narrative comparison: OK")
    print("JSON serialization: OK")
    print("Saved JSON validation: OK")

    print("\nAll pipeline steps completed successfully.")


# =========================================================
# 10. نقطه شروع برنامه
# =========================================================

if __name__ == "__main__":
    main()
