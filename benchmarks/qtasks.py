"""Quality tasks: 5 categories x 3. Graders return (score, max, reason).
0/1 for checkable tasks; 1-5 for free answers with an explicit keyword rubric."""
import json, re

TEXT_RU = (
    "В марте 2026 года городская библиотека Твери открыла после ремонта свой главный корпус на улице Советской. "
    "Реконструкция длилась два года и обошлась в 184 миллиона рублей, из которых 120 миллионов выделил областной бюджет, "
    "а остальное — частный фонд «Верхневолжье». Главным изменением стал новый цифровой зал на втором этаже: в нём установили "
    "40 компьютеров, три 3D-принтера и студию звукозаписи, которой читатели могут пользоваться бесплатно по предварительной записи. "
    "Кроме того, в здании появился лифт, а вход оборудовали пандусом, поэтому библиотека впервые стала полностью доступной для людей "
    "на колясках. Фонд пополнили на 12 тысяч книг, в основном это учебная и научно-популярная литература. Часть старых изданий "
    "не выбросили, а передали сельским библиотекам области. Изменился и режим работы: теперь библиотека открыта до 22 часов, а по "
    "воскресеньям — до 18 часов; раньше она закрывалась в 19 часов и не работала в воскресенье. Директор библиотеки Ирина Соколова "
    "рассказала, что за первый месяц после открытия читательские билеты получили 2300 новых посетителей, причём больше половины из "
    "них моложе 25 лет. По её словам, самым популярным местом оказалась студия звукозаписи: свободные часы в ней расписаны на три недели "
    "вперёд. В ближайших планах библиотеки — запустить вечерние курсы программирования для школьников и открыть летом читальный зал "
    "во внутреннем дворе. Горожане в соцсетях в основном хвалят обновлённое здание, но жалуются на нехватку парковочных мест рядом с ним."
)

EN_SRC = ("The maintenance window has been moved to Saturday night, so the invoice service will be unavailable "
          "for about two hours. Please save your drafts before 11 p.m.")
RU_SRC = "Мы перенесли встречу с поставщиком на четверг, потому что образцы ещё не прибыли на склад."

IMG_DIR = "/work/images"


def _num(text):
    m = re.findall(r"-?\d+(?:[.,]\d+)?", text.replace(" ", " ").replace(" ", ""))
    return m[-1].replace(",", ".") if m else None


def _final_line(text):
    m = re.findall(r"ОТВЕТ\s*:\s*(.+)", text, flags=re.I)
    return m[-1].strip() if m else text.strip().splitlines()[-1] if text.strip() else ""


def g_summary(ans):
    facts = {"ремонт/реконструкция": r"ремонт|реконструк", "184 млн": r"184", "цифровой зал/студия": r"цифров|студи",
             "доступность/лифт/пандус": r"лифт|пандус|коляс|доступн", "режим до 22": r"22"}
    hit = [k for k, p in facts.items() if re.search(p, ans, re.I)]
    words = len(ans.split())
    s = max(1, len(hit) - (1 if words > 80 else 0))
    return s, 5, f"факты {len(hit)}/5 ({', '.join(hit)}); слов {words}{' >80, -1' if words > 80 else ''}"


def g_translate(ans):
    terms = {"техобслуживание": r"обслуживан|техническ", "суббот": r"суббот", "счет/инвойс": r"сч[её]т|инвойс",
             "черновик": r"черновик", "EN: supplier": r"supplier|vendor", "EN: Thursday": r"thursday",
             "EN: samples": r"sample", "EN: warehouse": r"warehouse|stock"}
    hit = [k for k, p in terms.items() if re.search(p, ans, re.I)]
    s = max(1, round(len(hit) * 5 / len(terms)))
    return s, 5, f"термины {len(hit)}/{len(terms)}; нет: {', '.join(k for k in terms if k not in hit) or '—'}"


def g_exact(expected):
    def f(ans):
        got = _final_line(ans)
        ok = expected.lower() in got.lower()
        return int(ok), 1, f"ответ «{got[:60]}», ожидалось {expected}"
    return f


def g_number(expected):
    def f(ans):
        got = _num(_final_line(ans))
        ok = got is not None and abs(float(got) - expected) < 1e-6
        return int(ok), 1, f"ответ {got}, ожидалось {expected}"
    return f


def g_json(ans):
    try:
        d = json.loads(ans.strip())
        ok = (set(d) == {"name", "age", "skills"} and isinstance(d["name"], str) and isinstance(d["age"], int)
              and isinstance(d["skills"], list) and len(d["skills"]) == 3 and d["age"] == 34 and "Марина" in d["name"])
        return int(ok), 1, "валидный JSON по схеме" if ok else f"JSON не по схеме: {str(d)[:80]}"
    except Exception as e:
        return 0, 1, f"не JSON ({str(e)[:40]}): {ans.strip()[:50]!r}"


def g_bullets(ans):
    lines = [l for l in ans.strip().splitlines() if l.strip()]
    ok = len(lines) == 5 and all(l.startswith("- ") for l in lines)
    return int(ok), 1, f"строк {len(lines)}, все с '- ': {all(l.startswith('- ') for l in lines)}"


def g_one_word(ans):
    a = ans.strip().rstrip(".!")
    ok = a.lower() == "канберра"
    return int(ok), 1, f"ответ {a[:40]!r}"


def g_vision_desc(ans):
    keys = {"красный": r"красн|red", "круг": r"круг|circle", "синий": r"син|blue", "квадрат": r"квадрат|square",
            "зелёный": r"зел[её]н|green", "треугольник": r"треугольн|triangle"}
    hit = [k for k, p in keys.items() if re.search(p, ans, re.I)]
    return max(1, round(len(hit) * 5 / 6)), 5, f"найдено {len(hit)}/6: {', '.join(hit)}"


# (id, category, prompt, grader, kind) ; kind: text | code:<name> | image:<file>
TASKS = [
    ("ru_sum", "Русский", "Перескажи текст в 2–3 предложениях (не более 60 слов), сохранив главные факты.\n\n" + TEXT_RU, g_summary, "text"),
    ("ru_tr", "Русский", "Переведи первый текст на русский, а второй на английский. Выведи только два перевода, каждый с новой строки.\n\n1) "
     + EN_SRC + "\n2) " + RU_SRC, g_translate, "text"),
    ("ru_qa", "Русский", "Ответь по тексту: сколько новых посетителей получили читательские билеты за первый месяц? "
     "В последней строке напиши: ОТВЕТ: <число>\n\n" + TEXT_RU, g_number(2300), "text"),
    ("lg_bat", "Логика", "Бита и мяч вместе стоят 110 рублей. Бита дороже мяча на 100 рублей. Сколько стоит мяч? "
     "В последней строке напиши: ОТВЕТ: <число>", g_number(5), "text"),
    ("lg_train", "Логика", "Из городов A и B, расстояние между которыми 300 км, одновременно навстречу друг другу выехали два поезда: "
     "из A со скоростью 70 км/ч, из B со скоростью 80 км/ч. Через сколько минут они встретятся? В последней строке напиши: ОТВЕТ: <число>",
     g_number(120), "text"),
    ("lg_price", "Логика", "Цену товара 2000 рублей сначала повысили на 25%, затем снизили на 20%, затем снова повысили на 10%. "
     "Сколько рублей стоит товар? В последней строке напиши: ОТВЕТ: <число>", g_number(2200), "text"),
    ("cd_lru", "Код", None, None, "code:lru"),
    ("cd_calc", "Код", None, None, "code:calc"),
    ("cd_csv", "Код", None, None, "code:csv_line"),
    ("in_json", "Инструкции", "Верни ТОЛЬКО JSON без markdown и пояснений по схеме {\"name\": string, \"age\": integer, "
     "\"skills\": [ровно 3 строки]} для человека: Марина Орлова, 34 года, умеет готовить, водить автомобиль, говорит по-испански.",
     g_json, "text"),
    ("in_bul", "Инструкции", "Назови ровно 5 советов по экономии электричества дома. Формат: ровно 5 строк, каждая начинается с \"- \", "
     "без вступления и заключения.", g_bullets, "text"),
    ("in_one", "Инструкции", "Столица Австралии? Ответь одним словом, без вступления и пояснений.", g_one_word, "text"),
    ("vi_desc", "Зрение", "Опиши, какие фигуры и каких цветов изображены на картинке.", g_vision_desc, "image:shapes.png"),
    ("vi_ocr", "Зрение", "Прочитай код заказа на изображении. В последней строке напиши: ОТВЕТ: <код>", g_exact("QX-4721"), "image:ocr.png"),
    ("vi_cnt", "Зрение", "Сколько чёрных кружков на изображении? В последней строке напиши: ОТВЕТ: <число>", g_number(7), "image:dots.png"),
]
