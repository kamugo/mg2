# Przegląd repozytorium `mg-koreferencja-autokoder`

Data przeglądu: 3 września 2026 r.  
Przeglądany commit: `f02ed6bbecfa` (`master`)  
Repozytorium: <https://github.com/kamugo/mg-koreferencja-autokoder>

## Cel dokumentu

Dokument zapisuje uwagi techniczne i badawcze po porównaniu repozytorium
`mg-koreferencja-autokoder` z głównym repozytorium `mg2`. Ma pomóc kolejnemu
agentowi poprawić eksperymenty bez utraty wartościowych elementów jego pracy.

Najważniejszy wniosek: architektura macierzowego U-Netu i pretrening domenowy
na orzeczeniach SAOS są wartościowymi kierunkami. Obecne wyniki wymagają jednak
ponownej ewaluacji, ponieważ wygenerowane pliki CorefUD nie przechodzą przez
oficjalny scorer.

## Ustalenia blokujące wiarygodną ewaluację

### 1. Eksport CorefUD nie jest zgodny z oficjalnym scorerem

Sprawdzone pliki:

- `kod/runs/unet_small_full/eval_dev60.gold.dev.conllu`;
- `kod/runs/unet_small_full/eval_dev60.pred.dev.conllu`;
- `kod/runs/unet_small_full_dae/eval_dev60.gold.dev.conllu`;
- `kod/runs/unet_small_full_dae/eval_dev60.pred.dev.conllu`.

Uruchomienie aktualnego `ufal/corefud-scorer` wykazało kolejno trzy problemy:

1. `sent_id` zawiera ścieżkę dokumentu i znaki `/`, które UDAPI interpretuje
   jako nazwę strefy, np. `input_data/PCC-1.5-MMAX/...xml-s1`;
2. plik nie zawiera obowiązkowego nagłówka
   `# global.Entity = eid-etype-head-other`;
3. po naprawieniu powyższych dwóch elementów wyłącznie w kopii tymczasowej
   scorer nadal kończy działanie błędem:
   `ValueError: Cross-sentence mentions not supported yet: e1 ...`.

Źródłem problemów jest przede wszystkim
[`kod/src/eval/corefud_writer.py`](https://github.com/kamugo/mg-koreferencja-autokoder/blob/master/kod/src/eval/corefud_writer.py#L17-L52).
Writer tworzy znaczniki na poziomie całego dokumentu, a następnie dzieli tokeny
na zdania bez obsługi wzmianek przecinających granicę zdania. Nie zapisuje też
schematu `global.Entity` i bezpośrednio wstawia `doc_id` do `sent_id`.

Do poprawienia:

- zachować oryginalne, poprawne rekordy CoNLL-U/CorefUD zamiast tworzyć
  sztuczną składnię z `root`/`dep`;
- generować bezpieczne i unikalne `newdoc id` oraz `sent_id`;
- emitować poprawny nagłówek `global.Entity`;
- nie tworzyć wzmianki przechodzącej między zdaniami albo reprezentować ją
  zgodnie ze specyfikacją obsługiwaną przez scorer;
- dodać test integracyjny, który uruchamia oficjalny scorer i wymaga kodu
  zakończenia `0`;
- dopiero po tej naprawie przeliczyć wszystkie główne tabele wyników.

### 2. Wyników `0,3750` i `0,3849` nie należy opisywać jako oficjalnych

Wartości te pochodzą z własnej implementacji metryk, na pierwszych 60
dokumentach zbioru dev, z zachowanymi singletonami. W samej pracy zostało to
częściowo zaznaczone, ale liczby są później zestawiane z CorPipe w sposób, który
może sugerować pełną porównywalność.

Nie są one bezpośrednio porównywalne z wynikami `mg2`, ponieważ:

- `mg-koreferencja-autokoder` wykonuje wykrywanie wzmianek end-to-end;
- `mg2` w głównym eksperymencie PCC korzysta ze złotych granic wzmianek;
- użyto innej liczby dokumentów i innego sposobu agregacji;
- własne metryki zachowują singletony, a ustawienia oficjalnego scorera mogą
  być inne;
- CorPipe osiągający około `0,7396` również został w tym porównaniu oceniony
  własną ścieżką metryk.

Po naprawie eksportu należy prowadzić dwa jawnie oddzielone tory:

1. **oracle mentions** — złote wzmianki, ocena samego grupowania;
2. **end-to-end** — wykrywanie wzmianek i grupowanie, wraz z mention F1.

Oba tory powinny używać tego samego pełnego zbioru, tej samej wersji oficjalnego
scorera oraz zapisanych parametrów uruchomienia.

### 3. Test istotności opisany jako dwustronny liczy jeden ogon

W
[`kod/src/eval/significance.py`](https://github.com/kamugo/mg-koreferencja-autokoder/blob/master/kod/src/eval/significance.py#L24-L48)
opis mówi o dwustronnej wartości `p`, ale implementacja zlicza tylko próbki po
jednej stronie zera. W najprostszym wariancie wynik należy podwoić i ograniczyć
do `1`, a najlepiej zastosować poprawny test paired bootstrap/randomization z
korektą skończonej liczby próbek.

Raportowane `p=0,001` byłoby po prostym podwojeniu około `0,002`, więc wniosek
może pozostać statystycznie istotny. Nie usuwa to jednak ważniejszego problemu:
przeprowadzono tylko jeden trening z ziarnem `42`. Bootstrap po dokumentach
mierzy niepewność doboru dokumentów, ale nie wariancję samego treningu.

Zalecenie: co najmniej 5 ziaren, średnia i odchylenie standardowe oraz sparowana
ocena modeli na identycznym, zamrożonym zbiorze testowym.

## Problemy implementacyjne i metodologiczne

### 4. Cel DAE pochodzi z losowej, nieuczonej projekcji

W
[`kod/src/models/dae.py`](https://github.com/kamugo/mg-koreferencja-autokoder/blob/master/kod/src/models/dae.py#L38-L48)
cel rekonstrukcji powstaje przez `seg_model.pair_tensor(emb)` wewnątrz
`torch.no_grad()`. Model segmentacyjny jest przed pretreningiem świeżo
inicjalizowany, dlatego projekcja HerBERT 768 -> 32 nie uczy się podczas DAE.
U-Net rekonstruuje więc cechy w stabilnej, lecz arbitralnej losowej przestrzeni.

Warto sprawdzić co najmniej trzy warianty ablacyjne:

- rekonstrukcję znormalizowanych cech HerBERT lub ich PCA;
- uczoną projekcję z zatrzymaniem gradientu tylko w gałęzi celu;
- gałąź teacher/EMA jako stabilny cel.

Należy raportować, które parametry są trenowane w każdej fazie.

### 5. Cache embeddingów może zwracać nieaktualne dane

Klucz cache w
[`kod/src/data/dataset.py`](https://github.com/kamugo/mg-koreferencja-autokoder/blob/master/kod/src/data/dataset.py#L70-L80)
zawiera tylko `doc_id`, offset i długość okna. Brakuje:

- skrótu treści/tokenów;
- nazwy i rewizji encodera;
- nazwy i rewizji tokenizatora;
- parametrów tokenizacji oraz wersji kodu przygotowania danych.

Zmiana modelu albo dokumentu może zatem bez ostrzeżenia użyć starego pliku
`.pt`. Klucz powinien zawierać skrót wszystkich powyższych elementów, a manifest
cache powinien opisywać pełną konfigurację.

### 6. Niepełna końcowa grupa gradient accumulation jest pomijana

W
[`kod/train.py`](https://github.com/kamugo/mg-koreferencja-autokoder/blob/master/kod/train.py#L60-L77)
`optimizer.step()` wykonywany jest wyłącznie, gdy licznik batcha jest podzielny
przez `grad_accum`. Jeżeli liczba batchy nie jest podzielna, gradienty z końca
epoki przepadają.

Należy wykonać krok również dla ostatniego batcha, odpowiednio przeskalować
ostatnią grupę i dodać test dla liczby batchy niepodzielnej przez
`grad_accum`.

### 7. Łączenie klastrów między oknami jest zbyt słabe

[`stitch_clusters`](https://github.com/kamugo/mg-koreferencja-autokoder/blob/master/kod/src/data/windowing.py#L75-L110)
scala klastry tylko wtedy, gdy dwa okna zawierają wzmiankę o identycznym spanie.
Długi łańcuch może zostać rozcięty, jeśli w nakładającym się obszarze nie ma
wspólnej wykrytej wzmianki albo model przesunie jej granice.

Możliwe ulepszenia:

- konsensus na podstawie podobieństwa/IoU granic wzmianek;
- wspólne identyfikatory kandydatów przed dekodowaniem;
- globalne ponowne grupowanie reprezentacji wzmianek;
- osobna metryka pokazująca utratę jakości wynikającą z windowingu.

### 8. Macierz binarna token-token nie odwzorowuje całego CorefUD bez strat

Jedna binarna macierz i wykrywanie wzmianek przez ciągłe odcinki przekątnej nie
reprezentują jednoznacznie wszystkich przypadków:

- wzmianek zagnieżdżonych i nakładających się;
- wzmianek nieciągłych;
- niektórych wzmianek zero/empty nodes;
- dwóch przylegających wzmianek należących do tego samego klastra.

W dodatku pamięć rośnie jak `O(L^2)`, co ma duże znaczenie dla długich orzeczeń.
W pracy trzeba jawnie opisać ograniczony podzbiór zjawisk obsługiwany przez model
i policzyć, jaki odsetek złotych danych jest przez reprezentację niemożliwy do
odtworzenia.

### 9. Próg `0,5` nie powinien być przyjęty bez kalibracji

Próg dekodowania jest stały. Należy wydzielić kalibrację z części treningowej,
wybrać próg bez dostępu do dev/test, zapisać go w checkpoincie, a następnie użyć
bez zmian w końcowej ewaluacji.

### 10. Checkpointy i stan treningu nie są reprodukowalne z klona

W repozytorium nie ma głównych plików `.pt`; są ignorowane. Brakuje również
pełnego stanu optimizer/scheduler/scaler i mechanizmu wznowienia treningu.
Minimalny artefakt reprodukcyjny powinien zawierać:

- finalne checkpointy lub trwały link z sumami kontrolnymi;
- rewizję modelu bazowego i tokenizatora;
- wersję danych i listę dokumentów w splitach;
- konfigurację, seed, próg i wersje bibliotek;
- stan pozwalający wznowić przerwany trening.

## Ocena srebrnego korpusu prawnego

Repozytorium zawiera 400 pełnych orzeczeń SAOS, około 987 tys. tokenów, 97 tys.
encji i 112 tys. wzmianek. To cenna przeciwwaga dla korpusu `mg2`, który zawiera
400 aktów Dz.U./M.P. i reprezentuje inny gatunek języka prawnego.

Problem polega na tym, że podstawowe etykiety 400 orzeczeń utworzył własny model
o mention F1 około `0,51` i własnym CoNLL F1 około `0,385` na ogólnym PCC.
CorPipe zastosowano tylko do 40 dokumentów. Można oczekiwać dużej liczby
pominiętych wzmianek i błędnie rozciętych łańcuchów.

Zalecany następny przebieg:

1. uruchomić CorPipe i Stanza na wszystkich 400 orzeczeniach;
2. zachować predykcje obu systemów, nie zastępować ich jednym „prawdopodobnym
   złotem”;
3. wyliczyć zgodność spanów i par, pamiętając, że zgodność nie jest dokładnością;
4. nadać priorytet ręcznemu przeglądowi miejsc, w których systemy się różnią;
5. przygotować 40-80 dokumentów jako ręcznie sprawdzony zbiór ewaluacyjny,
   najlepiej z podwójną anotacją części próby;
6. używać pozostałego srebra wyłącznie do treningu, z wagami zależnymi od
   zgodności/confidence nauczycieli.

## Najmocniejsze elementy pracy drugiego agenta

Te elementy warto zachować i przenieść do wspólnego eksperymentu:

- rzeczywisty U-Net token-token trenowany na PCC; w `mg2` macierzowy U-Net był
  dotąd używany głównie w eksperymentach syntetycznych;
- domenowy pretrening DAE na nieanotowanych orzeczeniach SAOS;
- end-to-end wykrywanie wzmianek i osobna mention F1;
- pełne orzeczenia sądowe, uzupełniające krótsze akty prawne z `mg2`;
- sensowny podział modułów: struktury danych, windowing, encoder, model,
  dekodowanie i ewaluacja;
- czytelne `kod/README.md` i wiążące `kod/SPEC.md`;
- testy dekodowania macierzy i sklejania okien;
- rozbudowana bibliografia oraz osobna notatka o metrykach.

Wszystkie cztery testy zapisane w tym repozytorium przeszły podczas przeglądu.
Nie wykrywają jednak błędów integracji z oficjalnym scorerem ani końcowej grupy
gradient accumulation.

## Różnice względem `mg2`

| Obszar | `mg2` | `mg-koreferencja-autokoder` |
|---|---|---|
| Główny model | scorer par wzmianek + DAE embeddingów | tokenowa macierz 2D + U-Net |
| Wzmianki w PCC | złote granice | wykrywane end-to-end |
| Pretrening domenowy | brak pełnego pretreningu prawnego | 150 orzeczeń SAOS |
| Dane prawne | 400 aktów Dz.U./M.P. | 400 pełnych orzeczeń SAOS |
| CorPipe na srebrze | wszystkie 400 dokumentów | 40 dokumentów |
| Główna ewaluacja | oficjalny scorer CorefUD | własne metryki; eksport oficjalny błędny |
| Reprodukowalność | checkpointy LFS, hashe, manifesty | brak checkpointów w Git |
| Testy uruchomione w przeglądzie | 21/21 | 4/4 |
| Stan tekstu pracy | około 21 tys. słów | około 13 tys. słów i 12 znaczników TODO |

Wyników liczbowych obu repozytoriów nie należy porównywać bezpośrednio, dopóki
nie zostanie ujednolicony protokół dotyczący wzmianek, dokumentów, singletonów,
progu i scorera.

## Zalecany wspólny plan

1. Pozostawić `mg2` jako główne repozytorium ze względu na poprawną ścieżkę
   oficjalnego scorera, manifesty danych, checkpointy i bardziej kompletny tekst
   pracy.
2. Najpierw poprawić writer i potwierdzić kodem zakończenia `0`, że oficjalny
   scorer przyjmuje eksport drugiego modelu.
3. Przenieść CorefSeg U-Net oraz domenowy DAE do `mg2` jako osobne, porównywalne
   warianty eksperymentalne, a nie zastępować dotychczasowego baseline'u.
4. Ustalić wspólny protokół:
   - pełny, zamrożony split PCC;
   - osobny tor gold-mentions i end-to-end;
   - próg ustalany tylko na kalibracji;
   - oficjalny scorer CorefUD;
   - co najmniej 5 ziaren;
   - wersje i hashe wszystkich wejść.
5. Połączyć gatunki prawne na poziomie eksperymentów: 400 aktów prawnych i 400
   orzeczeń, ale raportować wyniki także osobno dla każdego gatunku.
6. Uruchomić CorPipe i Stanza na wszystkich 800 dokumentach, przygotować ranking
   rozbieżności i zbudować mniejszy ręczny złoty standard.
7. Dopiero po tych krokach aktualizować główne wnioski i tabele pracy.

## Priorytety dla następnego agenta

1. **P0:** poprawić `corefud_writer.py` i dodać test oficjalnego scorera;
2. **P0:** przeliczyć R5/R6 oraz CorPipe tym samym scorerem;
3. **P1:** poprawić dwustronny test istotności i uruchomić wiele ziaren;
4. **P1:** poprawić cache oraz końcowy krok gradient accumulation;
5. **P1:** uruchomić CorPipe na całym SAOS-400;
6. **P2:** wykonać ablacje celu DAE i metody sklejania okien;
7. **P2:** uzupełnić checkpointy, manifesty oraz brakujące fragmenty pracy.

Srebrnego zbioru nie należy traktować jako złotego testu. Najbezpieczniej użyć
go do pretreningu lub treningu z kontrolą szumu, natomiast końcową ocenę jakości
na tekstach prawnych oprzeć na ręcznie sprawdzonym podzbiorze.
