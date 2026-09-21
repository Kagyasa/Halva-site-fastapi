from sqlalchemy import select

from app.database import SessionLocal
from app.models.catalog import Product


DISPLAY_NAMES = {
    "bento-ptichka": "Бенто «Птичка»",
    "bento-tort-banan-karamel": "Бенто-торт",
    "bento-tort-vishnya-shokolad": "Бенто-торт",
    "bento-tort-klubnika-plombir": "Бенто-торт",
    "bento-tort-krasnyj-barhat": "Бенто-торт",
    "bento-tort-figurnyj": "Фигурный бенто-торт",
    "biskvitnyj-tort": "Бисквитный торт",
    "boul-s-lososem": "Боул с лососем",
    "boul-s-cyplenkom": "Боул с цыплёнком",
    "damskie-palchiki": "«Дамские пальчики»",
    "desert-anna-pavlova": "«Анна Павлова»",
    "kapkejki": "Капкейки",
    "kapkejki-mini": "Мини-капкейки",
    "kasha-molochnaya": "Молочная каша",
    "keks-finanse": "Кекс «Финансье»",
    "maminy-syrnichki": "Мамины сырнички",
    "merengovyj-rulet-maksi": "Меренговый рулет",
    "merengovyj-rulet-porcionno": "Меренговый рулет порционно",
    "merengovyj-rulet-standart": "Меренговый рулет",
    "mussovyj-tort-xl-dva-yarusa": "Муссовый торт",
    "mussovyj-tort-razmer-l": "Муссовый торт",
    "mussovyj-tort-razmer-s": "Муссовый торт",
    "pirozhnoe-kartoha": "Пирожное «Картоха»",
    "pirozhnye-dieticheskie": "Диетические пирожные",
    "pirozhnye-mussovye": "Муссовые пирожные",
    "ptichka": "Пирожное «Птичка»",
    "skrembl-pod-syrnym-sousom": "Скрэмбл с сырным соусом",
    "supy": "Супы",
    "sendvichi": "Сэндвичи",
    "tvorozhnoe-kolco": "Творожное кольцо",
    "tort-ptichka-razmer-s": "Торт «Птичка»",
    "tort-s-koronoj-i-blestkami-dlya-sduvaniya": "Торт с короной и блёстками",
    "tort-bomba": "Торт-бомба",
    "cyplenok-v-slivochno-soevom-souse-na-podushke-iz-ptitima": "Цыплёнок с птитимом",
    "chizkejk-san-sebastian": "Чизкейк San Sebastian",
    "chizkejk-san-sebastian-porcionno": "Чизкейк San Sebastian порционно",
}


def main():
    updated = 0
    missing = []

    with SessionLocal() as db:
        for slug, display_name in DISPLAY_NAMES.items():
            product = db.scalar(select(Product).where(Product.slug == slug))

            if product is None:
                missing.append(slug)
                continue

            product.display_name = display_name
            updated += 1

        db.commit()

    print(f"Готово. Обновлено товаров: {updated}")

    if missing:
        print("\nНе найдены товары:")
        for slug in missing:
            print(f"  - {slug}")


if __name__ == "__main__":
    main()
