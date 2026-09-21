from sqlalchemy import select

from app.database import SessionLocal
from app.models.catalog import Product


VK_URLS_BY_SLUG = {
    "bento-ptichka": "https://vk.ru/market/product/bento-ptichka-134363661-11968248",

    # Одна карточка VK для всех стандартных вкусов бенто-торта
    "bento-tort-banan-karamel": "https://vk.ru/market/product/bento-tort-134363661-6786661",
    "bento-tort-vishnya-shokolad": "https://vk.ru/market/product/bento-tort-134363661-6786661",
    "bento-tort-klubnika-plombir": "https://vk.ru/market/product/bento-tort-134363661-6786661",
    "bento-tort-krasnyj-barhat": "https://vk.ru/market/product/bento-tort-134363661-6786661",
    "pirozhnye-mussovye": "https://vk.ru/market/product/pirozhnye-mussovye-134363661-9155506",

    "bento-tort-figurnyj": "https://vk.ru/market/product/bento-tort-figurny-134363661-12906778",
    "biskvitnyj-tort": "https://vk.ru/market/product/biskvitny-tort-134363661-12967910",
    "boul-s-lososem": "https://vk.ru/market/product/boul-s-lososem-134363661-10230055",
    "boul-s-cyplenkom": "https://vk.ru/market/product/boul-s-tsyplenkom-134363661-11417514",
    "damskie-palchiki": "https://vk.ru/market/product/damskie-palchiki-134363661-11968072",
    "desert-anna-pavlova": "https://vk.ru/market/product/desert-quotanna-pavlovaquot-134363661-1800526",
    "kapkejki": "https://vk.ru/market/product/kapkeyki-134363661-9155516",
    "kapkejki-mini": "https://vk.ru/market/product/kapkeyki-mini-134363661-9155510",
    "kasha-molochnaya": "https://vk.ru/market/product/kasha-molochnaya-134363661-10230162",
    "keks-finanse": "https://vk.ru/market/product/kex-quotfinansyequot-134363661-9155469",
    "maminy-syrnichki": "https://vk.ru/market/product/maminy-syrnichki-134363661-10230263",

    # Одна карточка VK для стандартного и maxi рулета
    "merengovyj-rulet-maksi": "https://vk.ru/market/product/merengovy-rulet-134363661-3329146",
    "merengovyj-rulet-standart": "https://vk.ru/market/product/merengovy-rulet-134363661-3329146",
    "merengovyj-rulet-porcionno": "https://vk.ru/market/product/merengovy-rulet-portsionno-134363661-9155493",

    # Одна карточка VK для всех размеров муссового торта
    "mussovyj-tort-xl-dva-yarusa": "https://vk.ru/market/product/tort-mussovy-134363661-12074290",
    "mussovyj-tort-razmer-l": "https://vk.ru/market/product/tort-mussovy-134363661-12074290",
    "mussovyj-tort-razmer-s": "https://vk.ru/market/product/tort-mussovy-134363661-12074290",

    "pirozhnoe-kartoha": "https://vk.ru/market/product/pirozhnoe-quotkartokhaquot-134363661-11418476",
    "pirozhnye-dieticheskie": "https://vk.ru/market/product/pirozhnye-dieticheskie-134363661-9155509",
    "ptichka": "https://vk.ru/market/product/ptichka-134363661-11968232",
    "skrembl-pod-syrnym-sousom": "https://vk.ru/market/product/skrembl-pod-syrnym-sousom-134363661-10230295",
    "supy": "https://vk.ru/market/product/supy-134363661-11968281",
    "sendvichi": "https://vk.ru/market/product/sendvichi-134363661-10230225",
    "tort-ptichka-razmer-s": "https://vk.ru/market/product/tort-ptichka-razmer-s-134363661-12074300",
    "tvorozhnoe-kolco": "https://vk.ru/market/product/tvorozhnoe-koltso-134363661-11968099",
    "tort-s-koronoj-i-blestkami-dlya-sduvaniya": "https://vk.ru/market/product/tort-s-koronoy-i-blestkami-dlya-sduvania-134363661-12968006",
    "tort-bomba": "https://vk.ru/market/product/tort-bomba-134363661-12967924",
    "cyplenok-v-slivochno-soevom-souse-na-podushke-iz-ptitima": "https://vk.ru/market/product/tsyplenok-v-slivochno-soevom-souse-na-podushke-iz-ptitima-134363661-11968264",
    "chizkejk-san-sebastian": "https://vk.ru/market/product/chizkeyk-quotsan-sebastianquot-134363661-9155480",
    "chizkejk-san-sebastian-porcionno": "https://vk.ru/market/product/chizkeyk-quotsan-sebastianquot-portsionno-134363661-9155498",
}


def main():
    updated = 0
    not_found = []

    with SessionLocal() as db:
        for slug, vk_url in VK_URLS_BY_SLUG.items():
            product = db.scalar(select(Product).where(Product.slug == slug))

            if product is None:
                not_found.append(slug)
                continue

            product.vk_url = vk_url
            updated += 1

        db.commit()

        products_without_vk = db.scalars(
            select(Product)
            .where(Product.is_active.is_(True))
            .where((Product.vk_url.is_(None)) | (Product.vk_url == ""))
            .order_by(Product.name)
        ).all()

    print(f"Готово. Обновлено товаров: {updated}")

    if not_found:
        print("\nНе найдены товары со slug:")
        for slug in not_found:
            print(f"  - {slug}")

    if products_without_vk:
        print("\nАктивные товары, у которых всё ещё нет VK-ссылки:")
        for product in products_without_vk:
            print(f"  - {product.name} ({product.slug})")
    else:
        print("\nУ всех активных товаров есть VK-ссылка.")


if __name__ == "__main__":
    main()
