# Korpus srebrny ELI-400 i porównanie CorPipe 26

Data wykonania: 2026-09-03.

## Wynik

Utworzono 400 zróżnicowanych fragmentów polskich aktów urzędowych z anotacją
koreferencji dwóch niezależnych modeli. Jako główną etykietę srebrną przyjęto
CorPipe 26 `base`, ponieważ w lokalnej ocenie na złotym Polish-PCC dev wyraźnie
przewyższył dotychczasowy autokoder. Predykcje Stanza zachowano jako drugi głos
i sygnał do ustalania kolejności ręcznej weryfikacji.

Korpus pozostaje **srebrny i nie może być traktowany jako złoty test bez korekty
człowieka**.

## Dane

- 400 dokumentów: 320 train, 40 dev, 40 test;
- 127 542 słowa źródłowe i 155 641 tokenów Stanza;
- lata 2017–2024, po 50 dokumentów na rok;
- 200 dokumentów z Dz.U. i 200 z M.P.;
- 23 typy aktów;
- fragmenty do 450 słów, zamknięte na granicy zdania, gdy była dostępna;
- HTML dla Dz.U., warstwa tekstowa PDF dla M.P.;
- 0 znaków zastępczych Unicode w tekstach i wynikach.

## Anotacje prawne

| Właściwość | Stanza PL | CorPipe 26 base |
|---|---:|---:|
| dokumenty | 400 | 400 |
| klastry | 36 989 | 37 292 |
| wzmianki powierzchniowe | 53 034 | 55 977 |
| wzmianki zerowe | 0 | 298 |
| wszystkie wzmianki | 53 034 | 56 275 |

Oba systemy miały identyczne tokeny wejściowe. Dla wzmianki powierzchniowej
38 082 spany CorPipe miały dokładny odpowiednik wśród unikalnych spanów Stanza.
Odpowiada to precyzji 68,03% względem propozycji Stanza i pokryciu 71,96% spanów
Stanza. Wśród 35 357 par wspólnych spanów należących do klastrów CorPipe oba
modele zgadzały się co do połączenia w 66,52% przypadków.

Oficjalny scorer CorefUD, przy dokładnym dopasowaniu granic i zachowaniu
singletonów, dał zgodność: mention F1 69,65%, CoNLL F1 58,40% i LEA 51,33%.
Są to **metryki zgodności modeli, nie accuracy**, ponieważ klucz Stanza także
jest predykcją.

Klastry CorPipe podzielono według zgodności na:

- `high`: 3 199;
- `medium`: 2 120;
- `low`: 3 522;
- `singleton-supported`: 17 870;
- `singleton-unsupported`: 10 581.

## Porównanie na złotym Polish-PCC dev

Wszystkie liczby poniżej policzono tym samym oficjalnym scorerem CorefUD, bez
singletonów i z dopasowaniem głów wzmianki.

| Model | MUC F1 | B³ F1 | CEAF-e F1 | CoNLL F1 | LEA F1 | BLANC F1 | Mention F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kontrola bez DAE | 65,08 | 55,58 | 47,51 | 56,06 | 50,78 | 49,23 | 100,00 |
| Autokoder DAE | 64,11 | 54,90 | 46,31 | 55,10 | 50,07 | 48,56 | 100,00 |
| CorPipe 26 base | **78,64** | **71,67** | **68,58** | **72,97** | **68,40** | **72,16** | 93,11 |

CorPipe przewyższa DAE o 17,87 punktu CoNLL F1, mimo że działa end-to-end i sam
wykrywa wzmianki. Porównanie nie jest idealnie symetryczne: kontrola i DAE
dostały złote granice wzmianek, a CorPipe ich nie dostał. Z tego powodu przewaga
CorPipe jest tym bardziej praktycznie istotna dla tworzenia danych srebrnych,
ale nie odpowiada czystej ablacji architektury autokodera.

Lokalnie użyto segmentu 1024 z powodu 4 GB VRAM. Oficjalna karta checkpointu
podaje 75,5 CoNLL F1 na polskim teście CorefUD 1.4 przy segmencie 2560. Kod i
checkpoint pochodzą z [oficjalnego repozytorium CorPipe 26](https://github.com/ufal/crac2026-corpipe),
a model Stanza z [oficjalnej implementacji MSCAW/CAW coref](https://stanfordnlp.github.io/stanza/coref.html).

## Zalecana procedura ręcznej korekty

1. Nie dotykać `train` przed ustaleniem zasad anotacji; najpierw przejrzeć kilka
   dokumentów kalibracyjnych z `dev`.
2. W `test` sprawdzić wszystkie klastry, w kolejności: `low`,
   `singleton-unsupported`, `medium`, `high`, `singleton-supported`.
3. W `review_corpipe_mentions.csv` ustawić `mention_valid`, poprawiony
   `corrected_cluster_id` i ewentualnie granice tokenowe.
4. Po korekcie zamrozić `test`; nie używać go do wyboru progu autokodera.
5. Trenować na srebrnym `train`, dostrajać na poprawionym `dev`, a końcowy wynik
   raportować wyłącznie na poprawionym `test`.

Do szybkiej oceny jakości przygotowano `review_sample_100.csv`: po 20 klastrów
z każdej kategorii zgodności, każdy z innego dokumentu.

Najważniejsze pliki znajdują się w `kod/data/processed/legal-silver-400/`.
Główny wariant treningowy CorPipe jest w podkatalogu `corpipe26/`, łącznie z
JSONL, CoNLL-U, podziałami, kolejkami recenzji, manifestem i wynikami zgodności.
