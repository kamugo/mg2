# Plan CorefSeg-AE v2 po audycie CorPipe i obu repozytoriów

Data: 2026-09-04  
Status: plan roboczy po pierwszej rundzie audytu; żadna nowa liczba nie jest wynikiem końcowym bez wskazanego artefaktu.

## Decyzja projektowa

Główną ścieżką nie będzie dalsze powiększanie tokenowego U-Netu z repozytorium `mg-koreferencja-autokoder`. Ta reprezentacja nie zachowuje jednoznacznie granic sąsiadujących, zagnieżdżonych i nakładających się wzmianek. Dłuższy trening może poprawić surrogate loss, ale nie usunie tego ograniczenia.

Należy wykorzystać istniejącą w `mg2` architekturę **wzmianka–wzmianka** jako punkt wyjścia, dodać osobną detekcję wzmianek i zastąpić symetryczne progowanie kierunkowym wyborem antecedenta. U-Net/DAE pozostaje wkładem badawczym jako moduł uczący lub odszumiający reprezentację relacji, a CorPipe pozostaje zewnętrznym baseline'em i nauczycielem danych srebrnych.

Tokenowy CorefSeg-AE należy zachować jako udokumentowaną ablację negatywną. Nie należy już inwestować wielu godzin GPU w samo zwiększanie liczby jego kanałów lub epok.

## Stan wyjściowy potwierdzony artefaktami

1. `mg2` zawiera model wzmianka–wzmianka z zamrożonym HerBERT-em. Pilot na Polish-PCC osiągnął 56,06 CoNLL F1 dla baseline'u i 55,10 dla DAE, ale używał złotych wzmianek oraz sztucznych dokumentów odpowiadających niepokrywającym się oknom do 48 wzmianek. Wyniku nie wolno porównywać bezpośrednio z end-to-end CorPipe. Artefakt: `wyniki/real-pcc/SUMMARY.json`.
2. DAE poprawił pairwise F1 o 1,78 punktu, lecz pogorszył CoNLL F1 o 0,96 punktu. Dotychczas nie ma więc dowodu, że rekonstrukcja embeddingów poprawia końcowe klastrowanie.
3. Drugi projekt dekoduje wzmianki jako maksymalne dodatnie fragmenty przekątnej tokenowej macierzy i scala klastry przez union-find. Jest to ograniczenie reprezentacyjne, a nie tylko problem pojemności modelu.
4. HerBERT jest w obu obecnych ścieżkach zamrożony. CorPipe dostraja encoder wraz z głowicami.
5. Długi trening `unet_long_dae` nadal trwał podczas tworzenia planu. Pierwszy automatyczny benchmark wystartował za wcześnie, ponieważ obserwował proces nadrzędny zamiast właściwego procesu treningowego. Benchmark został ponownie ustawiony za bezpośrednim PID treningu.
6. Testy `mg2`: 22/22 przeszły przez `python -m unittest discover -s tests -v`. Testy drugiego repozytorium: 8/8 skryptów przeszło uruchamianych osobno. `unittest discover` w drugim repozytorium wykrywa 0 testów, a `pytest` nie znajduje się w zależnościach — należy ujednolicić runner.
7. Na PCC-dev 19 062 z 33 884 złotych par wzmianek tej samej encji, czyli 56,26%, przecina granice niezależnych okien `mg2`. Obecna ewaluacja nie próbuje ich rozwiązać.
8. Heurystyka `_mention_head` zgadza się ze złotą głową CorefUD tylko dla 65,59% ciągłych wzmianek powierzchniowych PCC-dev.
9. Na PCC-dev 54,41% wzmianek należy do singletonów. Muszą uczyć detektor wzmianek, ale nie powinny dominować głównej straty linkowania, skoro główny scorer usuwa singletony.

## Najważniejsze problemy do usunięcia przed nowym modelem

### P0. Uczciwa ewaluacja dokumentowa

Obecny wynik `mg2` jest liczony na pseudo-CorefUD, w którym każda wzmianka staje się jednym pseudotokenem, a każde okno osobnym dokumentem. Trzeba:

- odtworzyć predykcje w oryginalnych dokumentach i zdaniach;
- zachować prawdziwe spany, głowy, zera, części nieciągłe i identyfikatory dokumentów;
- zapisywać liczniki utraconych wzmianek i krawędzi przy każdym oknowaniu;
- dobierać checkpoint i próg na kalibracji według końcowego CoNLL F1, nie tylko pairwise F1 lub BCE/Dice;
- uruchamiać oficjalny `ufal/corefud-scorer` z przypiętym SHA, head match, dependency matching zer i osobnym raportem singletonów/exact match;
- dla end-to-end używać wariantu wejścia CRAC „coreference and zeros from scratch”, a nie wejścia zawierającego złote puste węzły.

Warunkiem przejścia dalej jest candidate recall liczony na pełnym dokumencie. Okna powinny się nakładać i mieć pamięć wcześniejszych antecedentów lub przyrostową reprezentację klastrów. Nie wolno sklejać wyniku złotym `entity_id`; taki zabieg jest dopuszczalny tylko jako pomiar sufitu.

### P0. Zachowanie informacji CorefUD

Konwerter `mg2` nie zachowuje pełnej składni zależnościowej ani jawnej głowy CorefUD. Funkcja `_mention_head` wybiera heurystycznie ostatni `NOUN/PROPN/PRON/DET`. Należy przejść na Udapi albo rozszerzyć schemat JSONL o:

- oryginalne `HEAD`, `DEPREL`, `DEPS` i `MISC`;
- głowę wzmianki wyznaczoną zgodnie z CorefUD;
- listę części wzmianki nieciągłej zamiast wymuszania jednego przedziału;
- pozycję i zależność pustej wzmianki;
- manifest konwersji i round-trip test gold → JSONL → CoNLL-U.

## Architektura docelowa

### 1. Głowica wzmianek

Pierwszy wariant powinien mieć osobne predykcje `start`, `end` i `mention`, ponieważ da się go wdrożyć szybko. Drugi wariant powinien odtwarzać stosowe `PUSH/POP:n` CorPipe z dekodowaniem dynamicznym, aby obsłużyć nakładanie i zagnieżdżenie.

Wyniki trzeba raportować osobno dla:

- zwykłych wzmianek ciągłych;
- wzmianek zagnieżdżonych i nakładających się;
- części nieciągłych;
- singletonów;
- pustych wzmianek.

### 2. Reprezentacja wzmianki

Zamiast średniej z całego spanu porównać trzy warianty:

1. `mean(span)` — kontrola obecna;
2. `start || end` — wariant CorPipe;
3. `head || start || end || attention-pool(span)` — wariant docelowy.

Praca o headword mention representation raportuje średnią przewagę reprezentacji głów nad pełnymi spanami w badanej architekturze, ale na Polish-PCC wariant heads-only był minimalnie słabszy od FullSpan. Prawdziwa głowa CorefUD powinna więc być ablacją, a nie automatycznie przyjętym zwycięzcą ani tylko cechą heurystyczną.

### 3. Kierunkowy wybór antecedenta

Dla wzmianki `i` kandydatami mają być wyłącznie wcześniejsze wzmianki oraz `self`, oznaczające nową encję. Cel treningowy powinien rozdzielać masę po wszystkich poprawnych wcześniejszych antecedentach. Eliminuje to jeden globalny próg i ogranicza szkody pojedynczego fałszywego mostu.

### 4. Rola autokodera

DAE/U-Net nie powinien sam definiować granic wzmianek. Powinien działać na skierowanej macierzy kandydatów wzmianka–antecedent jako:

- pretrening odszumiający cechy relacyjne;
- blok rezydualny przed głowicą antecedenta;
- pomocnicza strata rekonstrukcyjna obok właściwego antecedent cross-entropy.

Obecny tokenowy DAE rekonstruuje cechy wytworzone przez losową, zamrożoną podczas pretreningu projekcję. Co więcej, dla tensora `[h_i,h_j,|h_i-h_j|,h_i*h_j]` lokalnie zamaskowane pole można niemal odtworzyć przez skopiowanie `h_i` z tego samego wiersza i `h_j` z tej samej kolumny. Należy najpierw porównać DAE z bezuczeniowym baseline'em row/column-copy, a następnie z rekonstrukcją całych zamaskowanych wzmianek lub stabilnych embeddingów HerBERT-a. Sam spadek MSE nie jest dowodem nauczenia koreferencji.

### 5. Encoder

Na karcie 4 GB należy zacząć od:

- zamrożonego HerBERT-a jako kontroli;
- LoRA albo odmrożenia ostatnich 2 warstw;
- gradient checkpointingu i mixed precision;
- dopiero po pomiarze pamięci rozważyć 4 ostatnie warstwy.

Pełnego CorPipe nie trzeba trenować od zera, aby sprawdzić tę hipotezę.

### 6. Singletony, padding i długość kontekstu

Detektor powinien mieć osobną `mention loss`, która korzysta także z singletonów, natomiast `antecedent loss` powinien odpowiadać głównemu wynikowi bez singletonów. Dla starego tokenowego U-Netu należy dodać maskę jako kanał, wyzerować cechy po projekcji i zastąpić BatchNorm przez GroupNorm; obecnie bias projekcji oraz BatchNorm pozwalają paddingowi wpływać na ważne pola.

Pierwszym celem długości kontekstu jest 1024, nie 2560. Ablacja CorPipe 25 pokazuje, że większość zysku pojawia się przy 512→1024, a 1024→2560 daje mniej niż pół punktu średnio. Dla naszej karty należy osiągnąć ten zasięg przez pamięć antecedentów, a nie przez tokenową macierz 1024².

## Minimalna macierz eksperymentów

| ID | Wzmianki | Linking | Encoder | AE | Cel |
|---|---|---|---|---|---|
| B0 | CorPipe | CorPipe | umT5-base | nie | zewnętrzny end-to-end baseline |
| O1 | gold | obecny pair scorer `mg2` | HerBERT frozen | nie | pułap linking-only |
| O2 | gold | antecedent/self | HerBERT frozen | nie | wpływ celu i dekodera |
| O3 | gold | antecedent/self | HerBERT frozen | DAE/U-Net | czysty wkład autokodera |
| P1 | CorPipe predicted | antecedent/self | HerBERT frozen | nie | koszt błędów detekcji |
| P2 | CorPipe predicted | antecedent/self | HerBERT frozen | DAE/U-Net | hybryda o niskim ryzyku |
| E1 | własna głowica | antecedent/self | HerBERT frozen | DAE/U-Net | pełny CorefSeg-AE v2 |
| E2 | własna głowica | antecedent/self | HerBERT LoRA/2 warstwy | DAE/U-Net | wpływ adaptacji encodera |
| L1 | jak najlepszy E* | jak najlepszy E* | ten sam | legal DAE | transfer domenowy |

Każdy wariant ma używać identycznych splitów, co najmniej trzech seedów po zamrożeniu konfiguracji oraz dokumentu jako jednostki bootstrapu. Najpierw wystarczy jeden seed do odrzucania wadliwych wariantów.

## Dane prawnicze

Korpus 2000 tekstów oznaczony przez CorPipe jest zbiorem srebrnym, nie testem. Należy:

1. zapisać źródło, datę, hash tekstu, SHA kodu, checkpoint i parametry CorPipe;
2. rozdzielić dokumenty według źródła i czasu przed jakimkolwiek dostrajaniem;
3. automatycznie wykrywać duplikaty i bliskie duplikaty;
4. wybrać mały, warstwowy zbiór `gold-lite` do ręcznego przeglądu — np. 50 dokumentów lub ustaloną liczbę łańcuchów, z nadpróbkowaniem zaimków, ról prawnych, cytatów, długich dystansów i zer;
5. nie oceniać modelu względem jego własnych srebrnych etykiet jako rzekomego złotego standardu;
6. porównać trening na PCC, PCC + legal DAE oraz PCC + legal silver supervised.

## Kolejność realizacji

1. **Integralność pomiaru:** prawdziwy writer dokumentowy, round-trip, wariant „from scratch”, liczniki strat i naprawiony runner benchmarku.
2. **Dekompozycja błędu:** gold mentions → linking oraz CorPipe mentions → nasz linking.
3. **Pamięć dokumentowa:** usunięcie niezależnych okien 48 oraz pomiar recall osiągalnych antecedentów.
4. **Antecedent/self:** zastąpienie symetrycznego threshold + union-find.
5. **Reprezentacja head/start/end:** ablacja bez zmiany encodera.
6. **Test skrótu DAE:** row/column-copy kontra wytrenowany DAE.
7. **DAE/U-Net na macierzy wzmianka–antecedent:** dopiero po ustaleniu mocnego baseline'u bez AE.
8. **Częściowe dostrojenie HerBERT-a:** LoRA lub ostatnie warstwy.
9. **Detektor własny:** prosty start/end, potem wariant stosowy i osobna mention loss singletonów.
10. **Transfer prawny:** legal DAE i legal silver oraz ewaluacja na `gold-lite`.
11. **Końcowe 3 seedy, bootstrap, szybkość, VRAM i rozmiar całego systemu.**

## Kryteria zatrzymania i upraszczania

- Jeśli DAE/U-Net nie poprawi CoNLL F1 względem tego samego antecedent baseline'u w dwóch z trzech seedów, pozostaje wynikiem negatywnym pracy, bez kolejnego zwiększania modelu.
- Jeśli własny detektor jest znacznie słabszy od CorPipe, wersją użytkową zostaje hybryda CorPipe mentions + CorefSeg linking, a własny detektor jest ablacją.
- Jeśli LoRA nie mieści się stabilnie w 4 GB lub nie poprawia dev, encoder pozostaje zamrożony.
- Nie uruchamiać kolejnego wielogodzinnego treningu, dopóki poprzedni checkpoint nie ma oficjalnej ewaluacji i manifestu.
- Nie utrzymywać dwóch niezależnych implementacji tego samego eksperymentu. `mg2` powinno być repozytorium integracyjnym, a drugi projekt źródłem historycznej ablacji tokenowej do czasu świadomej migracji.

## Protokół kolejnych rund audytu

W każdej nowej rundzie:

1. wykonać `git fetch` obu repozytoriów i sprawdzić nowe SHA;
2. sprawdzić HEAD oficjalnych repozytoriów CorPipe, CorefUD scorer, Maverick i WL-Coref;
3. przeczytać nowe diffy, issues, wydania, artykuły i lokalne artefakty;
4. szukać nowego błędu, ograniczenia, prostszej ablacji albo mocniejszego baseline'u;
5. zapisać tylko nowe twierdzenia wraz z poleceniem, kodem zakończenia i ścieżką dowodu;
6. nie tworzyć pustej rundy, jeżeli SHA i artefakty się nie zmieniły i nie znaleziono nowego źródła;
7. nie przerywać aktywnego treningu, chyba że wykryty błąd unieważnia jego wynik.

Źródła startowe i SHA z tej rundy:

- `ufal/crac2026-corpipe`: `3ad2d913bd42f62f0422f0c5fdeb8002981298c8`;
- `ufal/crac2025-corpipe`: `ee8474477a4191ee7c1d26da66012574303b24b9`;
- `ufal/crac2024-corpipe`: `aaf90f0bef058054496850ec72ba29b1e41da185`;
- `ufal/corefud-scorer`: `4fd7b0e0c661aeeff88bc60c19ef507b84d1b590`;
- `SapienzaNLP/maverick-coref`: `0dc6554cd66f5d4eecf5b3d75626ef78e835ece6`;
- `vdobrovolskii/wl-coref`: `4af0aa04eefad5b68a1fb6ca48a846a449bfa4b0`.

## Najbliższy sprawdzalny krok

Po zakończeniu aktywnego treningu należy ukończyć benchmark czasu, a następnie — przed kolejnym treningiem — naprawić ewaluację dokumentową `mg2`, zachować prawdziwe głowy i wykonać dwa szybkie pomiary na tym samym Polish-PCC dev:

1. gold mentions + obecny pair scorer;
2. gold mentions + antecedent/self.

Jeśli wariant 2 nie poprawi jakości klastrowania albo przynajmniej nie zmniejszy fałszywych mostów, dalsza integracja U-Net/DAE z tym dekoderem nie ma uzasadnienia.

Pełny rejestr nowych dowodów i poleceń z tej rundy znajduje się w `notatki/07-audyt-zrodel-runda-1.md`.
