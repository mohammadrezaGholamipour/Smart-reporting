from hazm import Normalizer

normalizer = Normalizer()

texts = [
    "میزانتغییر درآمد",
    "رتبه ۳را دارد",
    "این گزارش نیاز به بررسیشود",
    "فروش لوازم خانگی افزایش داشته است",
]

for text in texts:
    normalized = normalizer.normalize(text)

    print("Original:  ", text)
    print("Normalized:", normalized)
    print("-" * 40)