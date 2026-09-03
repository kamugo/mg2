# Koreferencja dla języka polskiego

## Polish Coreference Corpus (PCC)

Polish Coreference Corpus jest korpusem nominalnej koreferencji zbudowanym na tekstach Narodowego Korpusu Języka Polskiego. Publikacje opisują około 1,8 tys. dokumentów z 14 gatunków, około 540 tys. tokenów, 180 tys. wzmianek i 128 tys. klastrów; anotacja obejmuje m.in. wzmianki zagnieżdżone, nieciągłe i podmioty zerowe. Wzmianki są spanami, ale mają również wskazane głowy semantyczne, a obok identyczności referencji występują relacje quasi-identyczności i relacje bliskie koreferencji. Rozmiar oraz różnorodność czynią PCC podstawowym korpusem treningowym dla polszczyzny, lecz nie jest to korpus prawniczy i wymaga osobnego transferu domenowego. Źródła: [strona PCC](https://zil.ipipan.waw.pl/PolishCoreferenceCorpus), [Ogrodniczuk i in. 2014](https://aclanthology.org/L14-1066/), klucze `ogrodniczuk_2014_pcc`, `ogrodniczuk_2019_referencyjne`.

Aktualna strona wydania PCC 1.5 deklaruje licencję **CC BY-NC 4.0** i udostępnia komplet danych w MMAX, TEI oraz BRAT; wszystkie trzy strony załączników były dostępne podczas weryfikacji. Ograniczenie NC pozwala na badania akademickie, lecz wyklucza automatyczne założenie późniejszego użycia komercyjnego. Wersja Polish-PCC rozprowadzana wewnątrz CorefUD ma na liście zasobów licencję **CC BY 3.0**; różnica wynika z konkretnego wydania i przy publikacji danych należy zachować plik licencyjny pobranej wersji zamiast uogólniać warunki PCC na CorefUD lub odwrotnie.

## CorefUD i polska część kolekcji

CorefUD harmonizuje korpusy koreferencyjne z Universal Dependencies i zapisuje anotację w kolumnie `MISC` formatu CoNLL-U, głównie jako atrybut `Entity`. Polish-PCC jest częścią publicznej kolekcji od wersji 1.0; ta wersja obejmowała 13 zbiorów w 10 językach i około 540 tys. polskich tokenów. Wersja 1.1 stanowiła podstawę shared tasku CRAC 2023, a wersja 1.2 — CRAC 2024; 1.2 obejmuje 21 zbiorów w 15 językach, jawne splity train/dev/test i polskie podmioty zerowe jako puste węzły CoNLL-U. Format pozostaje zgodny między 1.0 i 1.2, ale scoring shared tasków zmieniał główne dopasowanie z partial-match na head-match, dlatego wyników z kolejnych edycji nie wolno porównywać bez przeliczenia jednym scorerem. Źródła: [Nedoluzhko i in. 2022](https://aclanthology.org/2022.lrec-1.520/), [CRAC 2024](https://ufal.mff.cuni.cz/corefud/shared-task/2024), klucz `nedoluzhko_2022_corefud`.

Publiczne wydanie CorefUD 1.2 w LINDAT było dostępne pod trwałym identyfikatorem w chwili weryfikacji. Do pracy zaleca się użycie właśnie wersji Polish-PCC z CorefUD do implementacji i ewaluacji, ponieważ dostarcza gotowy CoNLL-U, podziały oraz oficjalny walidator/scorer. Oryginalne PCC 1.5 pozostaje przydatne do kontroli pełniejszej anotacji i konwersji, ale nie powinno być mieszane ze splitem CorefUD bez mapowania dokumentów.

## Systemy i narzędzia

### BARTEK

BARTEK jest statystyczną adaptacją architektury BART do polszczyzny, trenowaną na PCC i dystrybuowaną z zasobami z Wikipedii oraz plWordNetu. Oficjalna strona deklaruje **CC BY 3.0**, repozytorium Git oraz artefakt Maven `pl.waw.ipipan.zil.core:bartek:1.3`; repozytorium, podręcznik i serwer Maven odpowiadały kodem 200 podczas weryfikacji. Publiczne demo Multiservice nie odpowiedziało w limicie czasu, więc oznaczono je jako niedostępne, mimo działającego kodu źródłowego. System jest wartościowym historycznym baseline'em, ale wymaga starego stosu Java i zasobów językowych, co zwiększa koszt reprodukcji. Źródła: [BARTEK](https://zil.ipipan.waw.pl/Bartek), [Kopeć i Ogrodniczuk 2012](https://aclanthology.org/L12-1635/), klucz `kopec_2012_bartek`.

### IKAR

IKAR łączy drzewa decyzyjne C4.5 z regułami dla nazw własnych, uzgodnionych fraz nominalnych i zaimków, kierując wzmianki do encji zakotwiczonych nazwą własną. Publikacja zapowiadała wydanie GPL pod `nlp.pwr.wroc.pl/en/tools-and-resources/ikar`, ale adres nie odpowiadał podczas weryfikacji i nie znaleziono działającego oficjalnego repozytorium kodu. Dostępny pozostaje artykuł i opis potoku; raportowane na KPWr wyniki C4.5 wynoszą B³ F1 93,89%, MUC F1 83,67% i BLANC F1 83,61%, ale dotyczą węższej definicji anafory oraz nie są porównywalne z end-to-end PCC/CorefUD. IKAR należy więc opisać historycznie, lecz nie planować jako automatycznie uruchamialnego baseline'u. Źródło: [Broda i in. 2012](https://aclanthology.org/C12-3004/), klucz `broda_2012_ikar`.

### Ruler, COREF-PL i współczesne alternatywy

Oficjalna strona Polish Coreference Tools wymienia Ruler jako system regułowy, MentionDetector, Scoreference i konwertery PCC, obok BARTEK-a. Badanie porównawcze Kaczmarka i Marcińczuka oceniało IKAR, Ruler i BARTEK na KPWr i podkreślało, że różne definicje relacji ograniczają porównywalność standardowych metryk. Źródło: [Kaczmarek i Marcińczuk 2015](https://aclanthology.org/W15-5304/), klucz `kaczmarek_2015_evaluation`.

W budżecie kwerendy nie potwierdzono publicznego narzędzia lub modelu o dokładnej nazwie **COREF-PL**. Nazwy tej nie należy umieszczać w pracy jako istniejącego artefaktu bez nowego, bezpośredniego adresu; może być skrótem opisowym mylonym z Polish Coreference Tools albo jednym z nowszych modeli dla Polish-PCC. Potwierdzono natomiast dwie współczesne opcje: Stanza dokumentuje model coreference dla języka `PL` wytrenowany na CorefUD, a repozytorium `ipipan/herference` udostępnia integrację polskiej koreferencji ze spaCy na licencji GPL-3.0. Do S-06 jako adapter pierwszego wyboru należy przyjąć Stanza, ponieważ ma udokumentowane API, bieżący pakiet i jawne źródło danych; Herference pozostaje rezerwą po teście instalacji.

| narzędzie | typ | dane | licencja | stan dostępu 2026-09-03 | decyzja projektowa |
|---|---|---|---|---|---|
| BARTEK 1.3 | statystyczny mention-pair/BART | PCC | CC BY 3.0 | kod, podręcznik i Maven dostępne; demo nie odpowiada | historyczny baseline, opcjonalna reprodukcja |
| IKAR | hybrydowy C4.5 + reguły | KPWr | zapowiedziana GPL | artykuł dostępny, dawny adres wydania martwy | opis bez zależności wykonawczej |
| Ruler | regułowy | PCC | informacja na stronie narzędzi; wymaga sprawdzenia paczki | strona katalogowa dostępna | koncepcyjny baseline regułowy |
| COREF-PL | niepotwierdzony | nieustalone | nieustalona | brak potwierdzonego artefaktu pod tą nazwą | nie używać bez źródła |
| Stanza coref PL | neuronowy word-level/MSCAW | CorefUD Polish-PCC | zgodna z dystrybucją Stanza/modelu | język PL widnieje w aktualnej dokumentacji | adapter neuronowy w S-06 |
| Herference | neuronowy, integracja spaCy | polski | GPL-3.0 | repozytorium GitHub dostępne | wariant rezerwowy |

## Zjawiska specyficzne dla polszczyzny

### Podmiot zerowy i elipsa

Polszczyzna pozwala pominąć zaimek podmiotowy, ponieważ osoba, liczba, a czasem rodzaj są kodowane w formie czasownika, np. „Powód wniósł pozew. Następnie **zażądał** odsetek”, gdzie niewyrażony podmiot drugiego zdania odnosi się do powoda. PCC i CorefUD reprezentują takie wzmianki, przy czym CorefUD używa pustych węzłów; model musi zatem albo przewidywać zera, albo otrzymywać je z osobnego komponentu. Zignorowanie zer zaniży recall i szczególnie zaszkodzi dokumentom narracyjnym, takim jak uzasadnienia orzeczeń.

### Bogata fleksja i uzgodnienie

Ta sama encja występuje w wielu przypadkach i formach, np. „Sąd”, „Sądu”, „Sądowi”, dlatego dopasowanie powierzchniowe jest słabym sygnałem bez lematyzacji. Rodzaj i liczba dostarczają informacji dla zaimków, ale PCC pokazuje, że proste ograniczenia zgodności bywają naruszane przez konstrukcje predykatywne, kolektywne, skróty i relacje semantyczne. Reprezentacja powinna więc kodować cechy morfosyntaktyczne, lecz nie stosować ich jako bezwzględnych filtrów.

### Swobodny szyk i rozdzielone składniki

Funkcja składniowa w polszczyźnie jest słabiej związana z pozycją niż w angielskim, a informacja nowa i znana wpływa na kolejność składników. Kandydat najbliższy liniowo nie zawsze jest poprzednikiem, zaś wzmianki mogą zawierać zagnieżdżenia lub elementy trudne do opisania pojedynczym ciągłym spanem. Zależności UD, głowy wzmianek oraz scoring head-match są z tego powodu ważniejsze niż sama odległość tokenowa.

### Zaimki, formy grzecznościowe i anafora daleka

Zaimki osobowe, dzierżawcze, względne i wskazujące mają odmianę przez przypadek, rodzaj i liczbę, a ich podmiot może być domyślny. Teksty urzędowe dodatkowo używają deskrypcji typu „wnioskodawca”, „skarżąca”, „tenże” i „powyższy”, które zachowują referencję pomimo zmiany głowy leksykalnej. Użycie samego head-match jako cechy wejściowej byłoby niewystarczające, choć jest użyteczne jako kryterium ewaluacyjne granic.

## Konsekwencje dla eksperymentów

Podstawowym zbiorem nadzorowanym powinien być zamrożony release Polish-PCC z CorefUD 1.2, a oryginalny PCC 1.5 może służyć do analizy anotacji i ewentualnego pretrainingu po sprawdzeniu licencji. Należy raportować osobno jakość dla zaimków zerowych, jawnych zaimków, nazw i deskrypcji nominalnych oraz wyraźnie wskazać ustawienie singletonów i typ dopasowania granic. Adapter Stanza należy przetestować na tych samych plikach CoNLL-U; wyniki publikacji IKAR/BARTEK-a pozostają kontekstem historycznym, nie bezpośrednim baseline'em liczbowym.
