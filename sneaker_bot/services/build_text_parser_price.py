def build_result_text(fb: dict, fs: dict) -> str:
    parts = []
    shops = [
        ("bunt.by", fb, {"muzhskie": "Мужские", "zhenskie": "Женские"}),
        ("sneakers.by", fs, {"мужские": "Мужские", "женские": "Женские"})
    ]

    for shop_name, data_dict, caps in shops:
        total_found = sum(len(data_dict.get(k, [])) for k in data_dict)

        if total_found == 0:
            parts.append(f"<b>Магазин:</b> {shop_name}")
            parts.append("— Товар не найден.")
            parts.append("")
            continue

        parts.append(f"<b>Магазин:</b> {shop_name}")
        parts.append("")
        for key, title in caps.items():
            items = data_dict.get(key, [])
            if not items:
                continue

            parts.append(f"<b>{title}</b>")
            for idx, (t, price, url) in enumerate(items, start=1):
                parts.append(
                    f"{idx}. {t}\n"
                    f"   Цена: <code>{price}</code>\n"
                    f"   <a href=\"{url}\">Ссылка</a>"
                )
            parts.append("")

        parts.append("")

    return "\n".join(parts).strip()