"""Short-answer suites with automatic grading.
GERMAN: German passive, every form. IQ: reasoning/knowledge for the Bonsai 27B probe.
Each item: (id, category, question, [accepted answers]). Answers are compared after normalization."""

GERMAN_INSTR = ("Du bist Deutschlehrer. Antworte NUR mit dem vollständigen deutschen Satz bzw. der verlangten Form, "
                "ohne Erklärung, in einer Zeile. Formuliere den Satz im Passiv, wenn nicht anders verlangt; "
                "lass den Täter (von/durch ...) weg, außer die Aufgabe verlangt ihn.")

GERMAN = [
 ("g01", "Vorgangspassiv Präsens", "Setze ins Passiv Präsens: Der Mechaniker repariert das Auto.", ["Das Auto wird repariert."]),
 ("g02", "Vorgangspassiv Präteritum", "Setze ins Passiv Präteritum: Man baute die Brücke 1990.", ["Die Brücke wurde 1990 gebaut.", "1990 wurde die Brücke gebaut."]),
 ("g03", "Vorgangspassiv Perfekt", "Setze ins Passiv Perfekt: Man hat den Brief abgeschickt.", ["Der Brief ist abgeschickt worden.", "Der Brief ist abgesendet worden."]),
 ("g04", "Vorgangspassiv Plusquamperfekt", "Setze ins Passiv Plusquamperfekt: Man hatte das Haus verkauft.", ["Das Haus war verkauft worden.", "Das Haus war bereits verkauft worden."]),
 ("g05", "Vorgangspassiv Futur I", "Setze ins Passiv Futur I: Man wird das Problem lösen.", ["Das Problem wird gelöst werden."]),
 ("g06", "Vorgangspassiv Futur II", "Setze ins Passiv Futur II: Man wird die Arbeit bis Montag beendet haben.", ["Die Arbeit wird bis Montag beendet worden sein."]),
 ("g07", "Passiv mit Agens (von)", "Setze ins Passiv Präteritum und behalte den Täter: Der Lehrer lobte die Schüler.", ["Die Schüler wurden von dem Lehrer gelobt.", "Die Schüler wurden vom Lehrer gelobt."]),
 ("g08", "Passiv mit durch", "Setze ins Passiv Präteritum und behalte die Ursache: Ein Sturm zerstörte das Dach.", ["Das Dach wurde durch einen Sturm zerstört.", "Das Dach wurde von einem Sturm zerstört."]),
 ("g09", "Dativ-Passiv (subjektlos)", "Setze ins Passiv Präteritum: Man half mir sofort.", ["Mir wurde sofort geholfen.", "Es wurde mir sofort geholfen."]),
 ("g10", "Unpersönliches Passiv", "Setze ins Passiv Präsens: Man tanzt heute Abend im Saal.", ["Heute Abend wird im Saal getanzt.", "Es wird heute Abend im Saal getanzt.", "Im Saal wird heute Abend getanzt."]),
 ("g11", "Modalverb + Passiv Präsens", "Setze ins Passiv Präsens: Man muss die Rechnung bezahlen.", ["Die Rechnung muss bezahlt werden."]),
 ("g12", "Modalverb + Passiv Präteritum", "Setze ins Passiv Präteritum: Man konnte den Fehler nicht finden.", ["Der Fehler konnte nicht gefunden werden."]),
 ("g13", "Modalverb + Passiv Perfekt", "Setze ins Passiv Perfekt: Man hat das Formular ausfüllen müssen.", ["Das Formular hat ausgefüllt werden müssen."]),
 ("g14", "Passiv im Nebensatz (Perfekt)", "Ergänze den Nebensatz im Passiv Perfekt (Aktiv: man hat den Vertrag unterschrieben): Ich weiß, dass ...", ["Ich weiß, dass der Vertrag unterschrieben worden ist."]),
 ("g15", "Passiv + Modalverb im Nebensatz (Perfekt)", "Ergänze den Nebensatz im Passiv Perfekt (Aktiv: man hat das Auto reparieren müssen): Er sagt, dass ...", ["Er sagt, dass das Auto hat repariert werden müssen."]),
 ("g16", "Zustandspassiv Präsens", "Bilde das Zustandspassiv Präsens: Das Fenster wird geöffnet. (Ergebnis)", ["Das Fenster ist geöffnet."]),
 ("g17", "Zustandspassiv Präteritum", "Bilde das Zustandspassiv Präteritum: Der Laden wurde geschlossen. (Ergebnis)", ["Der Laden war geschlossen."]),
 ("g18", "Zustandspassiv Perfekt", "Bilde das Zustandspassiv Perfekt: Die Tür ist abgeschlossen.", ["Die Tür ist abgeschlossen gewesen."]),
 ("g19", "Konjunktiv II Passiv Gegenwart", "Bilde Konjunktiv II Passiv Gegenwart (würde-Form): Das Haus wird gebaut.", ["Das Haus würde gebaut werden."]),
 ("g20", "Konjunktiv II Passiv Vergangenheit", "Bilde Konjunktiv II Passiv Vergangenheit: Das Haus wurde gebaut.", ["Das Haus wäre gebaut worden."]),
 ("g21", "Konjunktiv I Passiv (indirekte Rede)", "Gib in indirekter Rede mit Konjunktiv I wieder: Die Zeitung schreibt: \"Die Straße wird gesperrt.\" Beginne mit: Die Zeitung schreibt, die Straße ...", ["Die Zeitung schreibt, die Straße werde gesperrt."]),
 ("g22", "Konjunktiv I Passiv Vergangenheit", "Gib in indirekter Rede mit Konjunktiv I wieder: Er sagt: \"Der Dieb ist gefasst worden.\" Beginne mit: Er sagt, der Dieb ...", ["Er sagt, der Dieb sei gefasst worden."]),
 ("g23", "Infinitiv Passiv", "Nenne den Infinitiv Passiv Präsens und den Infinitiv Passiv Perfekt von 'schreiben', getrennt durch ' / '.", ["geschrieben werden / geschrieben worden sein"]),
 ("g24", "Rezipientenpassiv (bekommen)", "Forme mit 'bekommen'-Passiv im Präsens um: Man schenkt ihm ein Buch.", ["Er bekommt ein Buch geschenkt."]),
 ("g25", "Passiversatz: sich lassen", "Forme mit 'sich lassen' um: Das Problem kann gelöst werden.", ["Das Problem lässt sich lösen."]),
 ("g26", "Passiversatz: sein + zu", "Forme mit 'sein + zu + Infinitiv' um: Die Aufgabe muss bis morgen erledigt werden.", ["Die Aufgabe ist bis morgen zu erledigen."]),
 ("g27", "Passiversatz: -bar", "Forme mit einem Adjektiv auf -bar um: Der Text kann gelesen werden.", ["Der Text ist lesbar."]),
 ("g28", "Aktiv aus Passiv", "Setze ins Aktiv Perfekt mit 'die Polizei' als Subjekt: Der Täter ist von der Polizei verhaftet worden.", ["Die Polizei hat den Täter verhaftet."]),
 ("g29", "Form erkennen", "Welche Passivform liegt vor? Antworte nur mit einer dieser Bezeichnungen: Vorgangspassiv Plusquamperfekt / Zustandspassiv Präteritum / Vorgangspassiv Präteritum. Satz: Die Stadt war zerstört worden.", ["Vorgangspassiv Plusquamperfekt"]),
 ("g30", "Fehlerkorrektur", "Korrigiere den Fehler und gib nur den korrekten Satz aus: Das Buch ist von ihm geschrieben geworden.", ["Das Buch ist von ihm geschrieben worden."]),
]

IQ_INSTR = "Решай задачу. В последней строке ответа напиши строго: ОТВЕТ: <ответ>"

IQ = [
 ("q01", "арифметика", "В магазине 3 коробки по 12 яблок и ещё 7 яблок. Продали 29. Сколько яблок осталось?", ["14"]),
 ("q02", "проценты", "Товар стоил 2000 руб. Цену повысили на 25%, а затем снизили на 20%. Сколько рублей он стоит теперь?", ["2000"]),
 ("q03", "движение", "Поезд прошёл 180 км за 2 ч 15 мин. Какова его средняя скорость в км/ч?", ["80"]),
 ("q04", "комбинаторика", "Сколькими способами можно выбрать 2 дежурных из 6 учеников (порядок не важен)?", ["15"]),
 ("q05", "логика", "Все кошки — животные. Некоторые животные — чёрные. Следует ли отсюда, что некоторые кошки чёрные? Ответь да или нет.", ["нет"]),
 ("q06", "логика", "Аня выше Бори, Боря выше Вити, Витя выше Гали. Кто второй по росту? Ответь именем.", ["Боря"]),
 ("q07", "ловушка", "Бита и мяч вместе стоят 110 руб. Бита дороже мяча на 100 руб. Сколько рублей стоит мяч?", ["5"]),
 ("q08", "последовательность", "Продолжи ряд: 2, 6, 12, 20, 30, ... Какое следующее число?", ["42"]),
 ("q09", "дата", "Если 1 марта 2026 года — воскресенье, какой день недели будет 1 апреля 2026 года? Ответь словом.", ["среда"]),
 ("q10", "знания", "Какой химический элемент имеет символ W? Ответь названием по-русски.", ["вольфрам"]),
 ("q11", "знания", "Сколько сторон у правильного додекагона?", ["12"]),
 ("q12", "единицы", "Сколько секунд в 2,5 часах?", ["9000"]),
 ("q13", "логика", "На столе 5 свечей горели. 2 из них задули. Сколько свечей останется в итоге, если оставшиеся догорят полностью?", ["2"]),
 ("q14", "задача", "Трое рабочих делают 3 детали за 3 минуты. Сколько минут потребуется 100 рабочим, чтобы сделать 100 деталей?", ["3"]),
 ("q15", "русский язык", "Сколько раз буква «н» пишется в слове «деревя_ый» (прилагательное)? Ответь цифрой.", ["2"]),
]
