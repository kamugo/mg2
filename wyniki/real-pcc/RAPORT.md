# Pilot treningu na Polish-PCC i transferu do tekstu prawnego

Data wykonania: 2026-09-03.

## Dane i procedura

Użyto Polish-PCC z CorefUD 1.4 (CC BY 3.0). Archiwum ma 123 369 695 B i SHA-256
`51814a8e2996f459cf3f4fa491c161b4fd59991d3390b4484dac901600cd9173`.
Plik licencji ma SHA-256
`e6bc9e9c474700b708f568bac9e5a8a9bcb2b1dad53442f5ba449fcb848b8e76`.

Oryginalny `train` liczy 1463 dokumenty, 446 420 tokenów i 154 166 fragmentów
wzmianek; `dev` liczy odpowiednio 183, 55 820 i 19 300. `Train` podzielono
dokumentowo na 1244 dokumenty uczące oraz 219 kalibracyjnych (seed 20260903).
Oficjalnego `dev` nie użyto do uczenia ani wyboru progu. Zamrożony HerBERT
`allegro/herbert-base-cased` w rewizji
`50e33e0567be0c0b313832314c586e3df0dc2297` utworzył reprezentacje wzmianek.

W tym pilocie oceniono klastrowanie przy złotych granicach wzmianek w
niepokrywających się oknach po maksymalnie 48 wzmianek. Jest to projekcja
mention-level, a nie pełny wynik end-to-end na niepodzielonych dokumentach.
Detekcja wzmianek ma 100% z definicji wejścia i nie jest wynikiem modelu.

## Wyniki na odłożonym Polish-PCC-dev

| Wariant | Parowy F1 | MUC F1 | B³ F1 | CEAF_e F1 | LEA F1 | BLANC F1 | CoNLL F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| kontrola bez DAE | 0,5585 | 0,6508 | 0,5558 | 0,4751 | 0,5078 | 0,4923 | **0,5606** |
| DAE | **0,5763** | 0,6411 | 0,5490 | 0,4631 | 0,5007 | 0,4856 | 0,5510 |
| DAE minus kontrola | +0,0178 | -0,0097 | -0,0068 | -0,0120 | -0,0071 | -0,0067 | **-0,0096** |

Oba modele wybrały na kalibracji próg 0,94. DAE zwiększył parowy F1 o 1,78 punktu
procentowego, głównie przez wyższą precyzję, lecz pogorszył wszystkie miary
partycji i CoNLL F1 o 0,96 punktu. W pojedynczym seedzie nie potwierdzono zatem
korzyści autokodera według metryki głównej. Bez wielu seedów i bootstrapu nie jest
to jeszcze test istotności PB1.

Kontrola miała 232 321 trenowanych parametrów, trenowała się 26,72 s i osiągnęła
szczyt 174 600 704 B pamięci CUDA. DAE miał 595 073 parametrów, 37,34 s i
182 927 360 B. Czasy nie obejmują jednorazowego kodowania zamrożonym HerBERT-em.

## Transfer na Dz.U. 2024 poz. 1984

Stanza wykryła 104 kandydatów w 332 tokenach. DAE zwrócił 14 łańcuchów
niejednoelementowych, a kontrola 11. Brak złotej anotacji oznacza, że nie można
obliczyć P/R/F1. Ręczny przegląd DAE, który nie jest anotacją referencyjną, ujawnił:

- prawdopodobnie użyteczne powiązanie `samorządom` oraz zgodne powtórzenia fragmentów
  nazwy instytucji: `Ministrów`, `Funduszu`, `Rehabilitacji`, `Osób`;
- niepoprawne kandydatury i łączenia jednostek lub wyrazów funkcyjnych: `r`, `zł`,
  `się`, `dnia`, `ust`;
- łączenie szablonowych, ale różnych treści: `brzmienie`/`brzmieniu`;
- nadmierne scalenie form `rozporządzenie`, ponieważ dokument odróżnia akt zmieniający
  z 2024 r. od aktu zmienianego z 2003 r.;
- kandydatury obejmujące tylko fragmenty pełnych nazw własnych, co pokazuje, że
  detektor wzmianek jest wąskim gardłem transferu.

Wniosek z transferu jest jakościowy: model przenosi podobieństwo leksykalne i
fleksyjne, ale nie rozróżnia dostatecznie referencji prawnych od powtórzeń
redakcyjnych i jednostek miary. Pełna ocena wymaga podwójnie zanotowanego testu
prawnego zgodnego z `zalaczniki/protokol-anotacji.md`.

## Artefakty

- `summary.json` — agregat maszynowy;
- `baseline/` i `dae/` — konfiguracje pośrednie, logi, checkpointy i wyniki scorera;
- `legal/DU-2024-1984-*.json` — pełne predykcje na akcie ELI;
- `kod/data/processed/corefud-1.4/herbert-real/manifest.json` — splity, hashe i rewizja enkodera.
