# Wie die Ergebnisse entstanden sind

Andere Sprachen: [English](METHODOLOGY.en.md) · [Русский](METHODOLOGY.ru.md) · Die Zahlen: [results-public/RESULTS.md](../results-public/RESULTS.md)

## Die Kette: Kern → Supervisor → Ergebnisse → dieses Repository

```
 Serverkern                        Supervisor                          Ergebnisse                        Veröffentlichung
 Gateway (llama-swap + llama.cpp)  Claude (Anthropic, Claude-Code-     bench_results/results*.jsonl      dieses Repository:
 Konsole, Berichtsgenerator,       Sitzungen auf demselben PC, im      → Berichtsgenerator → SQLite-     Code, Doku, results-public/
 Git-Versionierer                  Auftrag des Autors)                 Archiv + Live-Bericht             (Git-Tags v0001 … final-<Datum>)
 [dieses Repository, Code]         bereitet Tests vor, führt sie       → Versionen im lokalen Gitea
                                   aus und prüft sie
```

1. **Serverkern** – der Code dieses Repositorys: das llama-swap-Gateway auf festgelegten llama.cpp-Builds, die Konsole, der Berichtsgenerator (führt Ergebnisdateien zusammen, ohne ältere zu löschen) und der Versionierer, der jede Berichtsversion in Git speichert. Er beurteilt von sich aus nichts.
2. **Supervisor** – Claude, eingesetzt als Programmier- und Betriebsassistent auf dem PC des Autors (siehe [AI_OPERATOR.de.md](AI_OPERATOR.de.md)). Im Auftrag des Autors schrieb und passte er die Testskripte an, führte sie auf dem Gateway Modell für Modell aus, beobachtete die Läufe, wiederholte verdächtige, wertete die Ergebnisdateien aus und schrieb Berichte und Schlussfolgerungen.
3. **Ergebnisse** – eine JSON-Zeile pro Modell und Test in `bench_results/results*.jsonl` (Format: [RESULTS_FORMAT.md](RESULTS_FORMAT.md)); der Berichtsgenerator macht daraus den Live-Bericht und ein SQLite-Archiv; der Versionierer speichert jede Änderung im lokalen Gitea.
4. **Veröffentlichung** – [results-public/](../results-public/) wird aus den Live-Daten durch `scripts/make_public_results.py` erzeugt (ohne rohe Prompts und Antworten) und zusammen mit dem Code veröffentlicht.

## Vom Autor gesetzte Regeln (sie prägen jede Zahl)

- **Nur GPU.** Ein Modell, das nur mit Überlauf in RAM/CPU (1–3 Tokens/s) läuft, gilt nicht als funktionsfähig.
- **Stabiler GPU-Kontext von mindestens 64K** ist Voraussetzung für die späteren Phasen. 23 Modelle durchliefen die ersten Phasen; 8 erreichten auf der GPU keine 64K und wurden aus den späteren Tests entfernt (sie stehen mit Grund in der Tabelle); 15 wurden zugelassen.
- **Ein Modell gleichzeitig im Videospeicher**; das Gateway wechselt Modelle, der Supervisor startet nie zwei GPU-Jobs zugleich.
- **Nichts wird überschrieben**: Ein wiederholter Test fügt eine neue Zeile hinzu; Archiv und Git behalten frühere Werte.

## Was gemessen wurde (Phasen in der Reihenfolge der Läufe)

| Phase | Was gemessen wird |
|---|---|
| Allgemeintest (Kontext 8K) | Russisch, Logik, Code, Befolgen von Anweisungen, Sehen; Prompt- und Generierungsgeschwindigkeit, Videospeicher-Spitze |
| Deutsch: Passiv | 30 Formen des deutschen Passivs, Prüfung der exakten Antwort |
| Maximaler stabiler Kontext | größtes Fenster, bei dem der Server startet, 3 von 3 versteckten Fakten bei 80 % Füllung findet und die Geschwindigkeit hält; KV-Cache auf der GPU als f16, q8 und q4 getestet |
| Beschleuniger und Embeddings | Geschwindigkeit mit und ohne MTP, DFlash oder Entwurfsmodell (14 Profile); zwei Embedding-Modelle |
| Mathe und Physik, 11. Klasse | 40 generierte Aufgaben (20 + 20) mit berechneter Antwort; einige Modelle auch mit aktiviertem Denken |
| Zuverlässigkeit (Soak) | jedes Gateway-Profil durchläuft eine Schrittfolge: Start, Antworten bei verschiedenen Kontextgrößen, Videospeicher-Spitze, freier Host-Speicher |
| Code, 20 Aufgaben | 20 Programmieraufgaben in drei Schwierigkeitsstufen, Prüfung durch Ausführen von Tests |
| Chemie, 11. Klasse | 10 Aufgaben mit berechneter Antwort |
| Endgültige Profile und Bericht | gemessene Kontexte werden in die Gateway-Profile übernommen und geprüft |

Umgebung: NVIDIA GeForce RTX 3080 (10 GB), Windows 10 + Docker Desktop (WSL2), llama.cpp-Commit `81bc6b83f827df746eb129235488d325c49cae52`, PrismML-Fork `adfffbe41b2cabcd51fff326ab045662265062bb` (nur Bonsai-Modell), llama-swap v260. Die Läufe fanden zwischen dem 30.09.2026 und dem 06.10.2026 statt.

## Grenzen, die Sie kennen sollten

- **Eine Maschine, kleine Aufgabensätze.** 10–40 Aufgaben pro Test: Unterschiede von wenigen Prozent sind Rauschen. Die Tabellen sind ein Anhaltspunkt, kein Ranking der Modellqualität.
- **Tests wurden von einem KI-Supervisor geschrieben und geprüft.** Ein Prüfer kann Fehler enthalten; der Supervisor suchte Aufgaben, an denen alle Modelle scheitern (Zeichen eines falschen Prüfers), und wiederholte verdächtige Läufe, aber kein Mensch hat jede Antwort neu bewertet.
- **Aufgaben sind von uns generiert oder geschrieben**, nicht aus öffentlichen Benchmarks kopiert; sie sind daher nicht mit veröffentlichten Ranglisten vergleichbar.
- **Einstellungen zählen**: Quantisierung, Kontextgröße, KV-Cache-Typ und Denkmodus gehören zu jedem Ergebnis; sie stehen in den Zeilen und in `config/llama-swap.yaml`.
- **Die Benchmark-Skripte selbst sind nicht Teil dieser Version** (sie enthalten noch maschinenspezifische Pfade); die Ergebnisdateien, ihr Format und der Phasenplan sind es, sodass jedes Werkzeug vergleichbare Zeilen erzeugen kann.

## Eine Kopie des Repositorys mit den Ergebnissen verknüpfen

Wenn Sie einen Fork veröffentlichen, tragen Sie dessen Adresse in `.env` als `PUBLIC_REPO_URL=https://github.com/HomenSAI/homensai-local-ai-lab` ein: In den Fußzeilen von Konsole und Bericht erscheint dann ein „GitHub“-Link, und die Konsole meldet ihn in `/api/version`.
