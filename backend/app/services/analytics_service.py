
import re


def calculate_percentage_change(current, previous):
    """
    محاسبه درصد تغییر نسبت به مقدار قبلی.
    """
    if previous is None or previous == 0 or current is None:
        return None

    return round(((current - previous) / previous) * 100, 2)


def calculate_share(value, total):
    """
    محاسبه سهم یک مقدار از کل.
    """
    if not total:
        return 0

    return round((value / total) * 100, 2)


def get_trend(change):
    """
    تعیین وضعیت روند بر اساس درصد تغییر.
    """
    if change is None:
        return "unknown"

    if change > 0:
        return "increase"

    if change < 0:
        return "decrease"

    return "stable"


def is_total_row(value):
    """
    تشخیص ردیف‌های جمع کل.
    """
    if value is None:
        return False

    normalized = str(value).strip().lower()
    normalized = re.sub(r"\s+", "", normalized)

    total_labels = {
        "total",
        "grandtotal",
        "overalltotal",
        "subtotal",
        "جمعکل",
        "مجموع",
        "جمع",
    }

    return normalized in total_labels


def normalize_headers(headers):
    """
    یکسان‌سازی نام ستون‌ها.
    مثال:
    Revenue (IRR) -> revenue
    Units Sold -> unitssold
    """
    normalized_headers = []

    for header in headers:
        if header is None:
            normalized_headers.append("")
            continue

        value = str(header).strip().lower()

        # حذف واحدهایی که داخل پرانتز هستند.
        value = re.sub(r"\([^)]*\)", "", value)

        # حذف فاصله‌ها و یکسان‌سازی نام ستون.
        value = re.sub(r"\s+", "", value)

        normalized_headers.append(value)

    return normalized_headers


def to_number(value, default=0):
    """
    تبدیل مقدار به عدد.
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return default

    if isinstance(value, (int, float)):
        return value

    value = str(value).strip()

    if not value:
        return default

    value = value.replace(",", "").replace(" ", "")

    try:
        number = float(value)

        if number.is_integer():
            return int(number)

        return number

    except ValueError:
        return default


def calculate_sales_metrics(tables):
    """
    محاسبه شاخص‌های فروش و استخراج تحلیل‌های قابل استناد.

    تمام محاسبات عددی در Python انجام می‌شوند.
    ردیف‌های TOTAL در محاسبات لحاظ نمی‌شوند.
    """

    monthly_sales = []
    regions = []
    categories = []

    # -----------------------------------------
    # 1. استخراج جدول‌های فروش
    # -----------------------------------------

    for table in tables:
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        if not headers or not rows:
            continue

        headers = normalize_headers(headers)

        # جدول فروش ماهانه
        if "month" in headers and "revenue" in headers:

            for row in rows:
                record = dict(zip(headers, row))

                month = record.get("month")

                if month is None or is_total_row(month):
                    continue

                monthly_sales.append(
                    {
                        "month": str(month).strip(),
                        "revenue": to_number(record.get("revenue")),
                        "orders": to_number(record.get("orders")),
                        "units_sold": to_number(record.get("unitssold")),
                        "returns": to_number(record.get("returns")),
                    }
                )

        # جدول مناطق
        elif "region" in headers and "revenue" in headers:

            for row in rows:
                record = dict(zip(headers, row))

                region_name = record.get("region")

                if region_name is None or is_total_row(region_name):
                    continue

                regions.append(
                    {
                        "region": str(region_name).strip(),
                        "revenue": to_number(record.get("revenue")),
                        "orders": to_number(record.get("orders")),
                    }
                )

        # جدول دسته‌بندی محصولات
        elif "category" in headers and "revenue" in headers:

            for row in rows:
                record = dict(zip(headers, row))

                category_name = record.get("category")

                if category_name is None or is_total_row(category_name):
                    continue

                categories.append(
                    {
                        "category": str(category_name).strip(),
                        "revenue": to_number(record.get("revenue")),
                        "units_sold": to_number(record.get("unitssold")),
                    }
                )

    # -----------------------------------------
    # 2. اعتبارسنجی داده‌ها
    # -----------------------------------------

    if not monthly_sales:
        raise ValueError("جدول فروش ماهانه در PDF پیدا نشد.")

    if not regions:
        raise ValueError("جدول مناطق در PDF پیدا نشد.")

    if not categories:
        raise ValueError("جدول دسته‌بندی محصولات در PDF پیدا نشد.")

    # -----------------------------------------
    # 3. محاسبه شاخص‌های کلی
    # -----------------------------------------

    total_revenue = sum(item["revenue"] for item in monthly_sales)

    total_orders = sum(item["orders"] for item in monthly_sales)

    total_units_sold = sum(item["units_sold"] for item in monthly_sales)

    total_returns = sum(item["returns"] for item in monthly_sales)

    average_monthly_revenue = (
        total_revenue / len(monthly_sales)
        if monthly_sales
        else 0
    )

    average_order_value = (
        total_revenue / total_orders
        if total_orders
        else 0
    )

    # -----------------------------------------
    # 4. تحلیل تغییرات ماهانه
    # -----------------------------------------

    monthly_analysis = []

    for index, current in enumerate(monthly_sales):

        previous = monthly_sales[index - 1] if index > 0 else None

        revenue_change = calculate_percentage_change(
            current["revenue"],
            previous["revenue"] if previous else None,
        )

        orders_change = calculate_percentage_change(
            current["orders"],
            previous["orders"] if previous else None,
        )

        returns_change = calculate_percentage_change(
            current["returns"],
            previous["returns"] if previous else None,
        )

        monthly_analysis.append(
            {
                "month": current["month"],

                "revenue_change_percentage": revenue_change,
                "revenue_trend": get_trend(revenue_change),

                "orders_change_percentage": orders_change,
                "orders_trend": get_trend(orders_change),

                "returns_change_percentage": returns_change,
                "returns_trend": get_trend(returns_change),
            }
        )

    # مقایسه اولین و آخرین ماه
    first_month = monthly_sales[0]
    last_month = monthly_sales[-1]

    overall_growth = calculate_percentage_change(
        last_month["revenue"],
        first_month["revenue"],
    )

    # -----------------------------------------
    # 5. تحلیل مناطق
    # -----------------------------------------

    for region in regions:
        region["share_percentage"] = calculate_share(
            region["revenue"],
            total_revenue,
        )

    regions.sort(
        key=lambda item: item["revenue"],
        reverse=True,
    )

    top_region = regions[0]

    # -----------------------------------------
    # 6. تحلیل دسته‌بندی محصولات
    # -----------------------------------------

    for category in categories:
        category["share_percentage"] = calculate_share(
            category["revenue"],
            total_revenue,
        )

    categories.sort(
        key=lambda item: item["revenue"],
        reverse=True,
    )

    top_category = categories[0]

    # -----------------------------------------
    # 7. تحلیل تمرکز درآمد
    # -----------------------------------------

    top_region_share = top_region["share_percentage"]

    top_category_share = top_category["share_percentage"]

    # -----------------------------------------
    # 8. محاسبه نسبت مرجوعی به سفارش
    # -----------------------------------------

    returns_to_orders_ratio = (
        round((total_returns / total_orders) * 100, 2)
        if total_orders
        else None
    )

    # -----------------------------------------
    # 9. ساخت تحلیل‌های قابل استناد
    # -----------------------------------------

    first_to_last_growth = {
        "from_month": first_month["month"],
        "to_month": last_month["month"],
        "change_percentage": overall_growth,
        "trend": get_trend(overall_growth),
    }

    monthly_revenue_changes = [
        item["revenue_change_percentage"]
        for item in monthly_analysis[1:]
    ]

    positive_months = sum(
        1
        for value in monthly_revenue_changes
        if value is not None and value > 0
    )

    negative_months = sum(
        1
        for value in monthly_revenue_changes
        if value is not None and value < 0
    )

    stable_months = sum(
        1
        for value in monthly_revenue_changes
        if value == 0
    )

    # -----------------------------------------
    # 10. خروجی نهایی
    # -----------------------------------------

    return {
        "summary": {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_units_sold": total_units_sold,
            "total_returns": total_returns,

            "average_monthly_revenue": round(
                average_monthly_revenue,
                2,
            ),

            "average_order_value": round(
                average_order_value,
                2,
            ),

            "growth_percentage": overall_growth,
        },

        "monthly_sales": monthly_sales,

        "monthly_analysis": monthly_analysis,

        "regions": regions,

        "categories": categories,

        "insights": {
            "top_region": top_region,

            "top_category": top_category,

            "revenue_growth": first_to_last_growth,

            "monthly_revenue_direction": {
                "increasing_months": positive_months,
                "decreasing_months": negative_months,
                "stable_months": stable_months,
            },

            "revenue_concentration": {
                "top_region": top_region["region"],
                "top_region_share_percentage": top_region_share,

                "top_category": top_category["category"],
                "top_category_share_percentage": top_category_share,
            },

            "returns_analysis": {
                "total_returns": total_returns,
                "total_orders": total_orders,

                "returns_to_orders_ratio_percentage": (
                    returns_to_orders_ratio
                ),

                "is_product_return_rate": False,

                "description": (
                    "نسبت تعداد مرجوعی به تعداد سفارش‌ها است؛ "
                    "این شاخص لزوماً نرخ واقعی مرجوعی کالا نیست."
                ),
            },
        },
    }


def build_management_context(data: dict) -> dict:
    """
    ساخت اطلاعات قابل استناد برای گزارش مدیریتی.

    وضعیت‌ها و مقایسه‌ها توسط Python تعیین می‌شوند.
    """

    if not isinstance(data, dict):
        raise ValueError("داده ورودی باید dict باشد.")

    monthly_sales = data.get("monthly_sales", [])
    monthly_analysis = data.get("monthly_analysis", [])
    regions = data.get("regions", [])
    categories = data.get("categories", [])
    insights = data.get("insights", {})

    # -----------------------------------------
    # 1. تحلیل قطعی ماهانه
    # -----------------------------------------

    monthly_observations = []

    for index, item in enumerate(monthly_analysis):

        previous = (
            monthly_sales[index - 1]
            if index > 0 and index - 1 < len(monthly_sales)
            else None
        )

        monthly_observations.append({
            "month": item["month"],

            "data_available": True,

            "comparison_available": previous is not None,

            "revenue_trend": item["revenue_trend"],

            "orders_trend": item["orders_trend"],

            "returns_trend": item["returns_trend"],

            "previous_month": (
                previous["month"] if previous else None
            ),
        })

    # -----------------------------------------
    # 2. رتبه‌بندی مناطق
    # -----------------------------------------

    regional_ranking = [
        {
            "region": item["region"],
            "rank": index + 1,
        }
        for index, item in enumerate(regions)
    ]

    # -----------------------------------------
    # 3. رتبه‌بندی دسته‌بندی‌ها
    # -----------------------------------------

    category_ranking = [
        {
            "category": item["category"],
            "rank": index + 1,
        }
        for index, item in enumerate(categories)
    ]

    # -----------------------------------------
    # 4. روند کلی درآمد
    # -----------------------------------------

    revenue_growth = insights.get("revenue_growth", {})

    # -----------------------------------------
    # 5. اطلاعات مرجوعی
    # -----------------------------------------

    returns_analysis = insights.get("returns_analysis", {})

    return {
        "overall_revenue_trend": revenue_growth.get("trend"),

        "monthly_observations": monthly_observations,

        "regional_ranking": regional_ranking,

        "category_ranking": category_ranking,

        "returns_analysis": {
            "comparison_available": len(monthly_sales) > 1,
            "product_return_rate_verified": (
                returns_analysis.get("is_product_return_rate", False)
            ),
        },
    }