# Postęp prac

## [S-00] Szkielet repozytorium — 2026-09-03
Zrobione: Utworzono strukturę katalogów, szkielet dokumentu LaTeX, jedenaście pustych rozdziałów, pliki początkowe i listę zależności Pythona. Zweryfikowano cztery źródła startowe pod wskazanymi adresami. Statycznie sprawdzono kompletność wszystkich 15 instrukcji `\\input{}` oraz zbilansowanie nawiasów klamrowych w 16 plikach `.tex`.
Pliki: `ZADANIE.md`, `SESJE.md`, `DZIENNIK_ZALOZEN.md`, `praca/main.tex`, `praca/tytulowa.tex`, `praca/oswiadczenie.tex`, `praca/streszczenia.tex`, `praca/wykaz-skrotow.tex`, `praca/rozdzialy/*.tex`, `praca/bibliografia.bib`, `kod/requirements.txt` oraz katalogi robocze.
Otwarte kwestie: Nie wykonano kompilacji, ponieważ w środowisku nie ma żadnego kompilatora LaTeX (`pdflatex`, `xelatex`, `lualatex`, `latexmk` ani `tectonic`) ani programu `biber`.
Następny krok: [S-01]

## [S-01] Plan pracy — 2026-09-03
Zrobione: Sformułowano jednozdaniową tezę, trzy falsyfikowalne pytania badawcze, rozwinięty spis treści do poziomu podrozdziałów oraz mapowanie pytań na eksperymenty. Wykonano cztery zapytania kontrolne dotyczące nietrywialności tezy; nie uzyskano przesłanek rozstrzygających, a pełną ocenę pozostawiono zaplanowanym kwerendom literaturowym.
Pliki: `PLAN_PRACY.md`, `DZIENNIK_ZALOZEN.md`, `POSTEP.md`.
Otwarte kwestie: Dostępność wspólnego zbioru testowego i wykonalność porównania kosztowego z LLM wymagają potwierdzenia w kwerendzie oraz sesji danych.
Następny krok: [S-02a]

## [S-02a] Kwerenda: koreferencja neuronowa — 2026-09-03
Zrobione: Opracowano 14 rodzin metod od klasyfikacji par i sit po modele spanowe, słowowe, generatywne i Maverick; każda zawiera opis wejścia, wyjścia, kosztu, ograniczeń oraz wiersz porównawczy. Wykorzystano pełny budżet 14 wyszukiwań i wyłącznie odwiedzone źródła pierwotne.
Pliki: `notatki/01a-coref-neuronowa.md`, `praca/bibliografia.bib`, `POSTEP.md`.
Otwarte kwestie: Część starszych publikacji nie została przepisana liczbowo, ponieważ dostępne fragmenty nie pozwalały jednoznacznie odtworzyć właściwego wariantu tabeli; oznaczono je kreską zamiast wpisywać wartość niepewną.
Następny krok: [S-02b]

## [S-02b] Kwerenda: koreferencja dla polskiego — 2026-09-03
Zrobione: Opisano PCC, wersje CorefUD 1.0–1.2, zjawiska polskiej koreferencji oraz stan dostępu do BARTEK-a, IKAR-a, Rulera, Stanza PL i Herference. Zweryfikowano działanie repozytorium, podręcznika i Mavena BARTEK-a, niedostępność jego demo i dawnego adresu IKAR-a; nie potwierdzono artefaktu o nazwie COREF-PL. Wykorzystano 12 z 14 dopuszczonych wyszukiwań.
Pliki: `notatki/01b-coref-polska.md`, `praca/bibliografia.bib`, `POSTEP.md`.
Otwarte kwestie: Przed eksperymentami trzeba zamrozić konkretny release Polish-PCC i zachować jego plik licencyjny; COREF-PL pozostaje nazwą niezweryfikowaną.
Następny krok: [S-02c]

## [S-02c] Kwerenda: NLP prawnicze i dane — 2026-09-03
Zrobione: Porównano polskie modele bazowe, modele długiego kontekstu oraz dziewięć źródeł i benchmarków prawniczych pod względem rozmiaru, dostępu, licencji i anonimizacji. Wykorzystano pełny budżet 16 wyszukiwań. Zgodnie z twardą regułą odrzucono do treningu artefakty bez jednoznacznej licencji, w szczególności sprawdzone wagi PolBERT, dokumenty CUAD oraz SAOS bez dodatkowej podstawy prawnej; jako główny enkoder wskazano HerBERT, a jako dane domenowe do dalszego audytu JuDDGES-pl i ELI.
Pliki: notatki/01c-nlp-prawnicze-dane.md, praca/bibliografia.bib, POSTEP.md.
Otwarte kwestie: Przed pobraniem danych trzeba zamrozić wersje i kopie licencji, wykonać audyt PII oraz potwierdzić podstawę prawną ewentualnego użycia SAOS; świeży JuDDGES-pl wymaga szczególnie ostrożnej walidacji jakości.
Następny krok: [S-02d]

## [S-02d] Kwerenda: autokodery — 2026-09-03
Zrobione: Opracowano dziesięć rodzin i zastosowań autokoderów: AE, DAE, VAE, sparse/contractive AE, U-Net, segmentację szeregów, DEC/IDEC oraz autokodery grafowe i tekstowe. Dla każdej opisano wejście, wyjście, koszt, ograniczenia oraz możliwe przeniesienie do koreferencji; wykorzystano pełny budżet 12 wyszukiwań. Jako trzy warianty warte implementacji wskazano DAE reprezentacji wzmianek, konwolucyjną segmentację macierzy oraz cel rekonstrukcyjno-klastrujący inspirowany IDEC.
Pliki: notatki/01d-autokodery.md, praca/bibliografia.bib, POSTEP.md.
Otwarte kwestie: Nie odnaleziono bezpośredniego wyniku dla autokodera w polskiej koreferencji prawniczej; transfer z obrazów, szeregów i grafów pozostaje hipotezą do falsyfikacji, a pełna macierz relacji wymaga ograniczenia kosztu O(n²).
Następny krok: [S-02e]

## [S-02e] Kwerenda: LLM w koreferencji — 2026-09-03
Zrobione: Opracowano zero-shot, few-shot/CoT, długi kontekst, strojenie text-to-text, pseudoetykiety, racjonalizacje i destylację oraz zaprojektowano dwa warianty hybrydy AE+LLM. Wykorzystano pełny budżet 10 wyszukiwań. Oddzielono koreferencję encji od zdarzeń i zapisano tylko wyniki widoczne w źródłach, w tym porównanie CRAC 2025 wskazujące podobną jakość przy mniej niż 10% kosztu dla systemu parowego.
Pliki: notatki/01e-llm-koreferencja.md, praca/bibliografia.bib, POSTEP.md.
Otwarte kwestie: Zamknięte modele LLM wymagają wersjonowania promptu i cennika; wyniki mini-testu oraz koreferencji zdarzeń nie są porównywalne z docelowym testem polskiej koreferencji encji.
Następny krok: [S-02f]

## [S-02f] Scalenie kwerendy i weryfikacja bibliografii — 2026-09-03
Zrobione: Scalono 36 wierszy porównawczych i jawnie oznaczono różnice zbiorów, zadań, metryk, scorerów oraz mini-testów. Audyt wykazał 57 unikatowych wpisów bibliograficznych, wszystkie z URL lub DOI i datą weryfikacji; wszystkie klucze cytowane w notatkach istnieją. Docelowy zakres 45–60 osiągnięto bez dodatkowych pobrań stron.
Pliki: notatki/01f-tabela-porownawcza.md, POSTEP.md.
Otwarte kwestie: Brak publikacji bezpośrednio łączącej autokoder, polską koreferencję i tekst prawny; jest to luka badawcza, ale także ryzyko eksperymentalne.
Następny krok: [S-03]

## [S-03] Sformułowanie problemu i wybór architektury — 2026-09-03
Zrobione: Sformalizowano wykrywanie wzmianek, relację koreferencji, partycję encji i wspólną funkcję oceny. Na polskich przykładach opisano trudności domeny prawnej. Wybrano macierzowy U-Net, domenowy DAE z lekką głowicą oraz selektywną hybrydę LLM; określono tensory, straty, budżety parametrów, szacunki pamięci i ryzyka, a samodzielne klastrowanie DEC/IDEC odrzucono.
Pliki: notatki/02-problem-i-architektura.md, DZIENNIK_ZALOZEN.md, POSTEP.md.
Otwarte kwestie: Szacunki pamięci nie są wynikami pomiaru; limity M=128, latent=128 i 16 zapytań LLM na dokument wymagają profilowania i doboru wyłącznie na dev.
Następny krok: [S-04]

## [S-04] Dane: pipeline, protokół anotacji i kod — 2026-09-03
Zrobione: Zdefiniowano role korpusów, splity, wspólny JSONL, tokenizację, okna długich dokumentów, scalanie klastrów, kontrolę licencji i PII. Utworzono protokół podwójnej anotacji 24 orzeczeń z Krippendorff α. Zaimplementowano downloader CorefUD/ELI/JuDDGES, konwerter CorefUD i statystyki; kompilacja składniowa przeszła, ELI pobrał jeden rzeczywisty akt, a próbka syntetyczna dała zapisany raport 1 dokumentu, 9 tokenów, 3 wzmianek, 2 klastrów i 1 zera.
Pliki: notatki/03-dane.md, zalaczniki/protokol-anotacji.md, kod/scripts/pobierz_dane.py, kod/src/data/konwersja.py, kod/scripts/statystyki.py, kod/tests/fixtures/sample.conllu, wyniki/s04-data-smoke.json, kod/data/raw/eli-smoke/.
Otwarte kwestie: Pełne dane nie zostały pobrane ani zanotowane; tabela korpusu celowo zachowuje znaczniki DO UZUPEŁNIENIA. Konwerter wymaga walidacji na oficjalnym pełnym wydaniu, szczególnie dla wzmianek nieciągłych i zagnieżdżonych.
Następny krok: [S-05]

## [S-05] Implementacja architektur i treningu — 2026-09-03
Zrobione: Zaimplementowano wspólny model koreferencji w wariantach baseline, domenowy DAE z klasyfikatorem par oraz macierzowy U-Net, a także selektor niepewnych przypadków dla hybrydy LLM. Dodano deterministyczny trening sterowany konfiguracją YAML, logowanie JSONL, checkpointy, obsługę AMP/CUDA i syntetyczny zbiór diagnostyczny. Kompilacja składniowa oraz 3 testy przeszły; niezależny smoke run na 20 przykładach zakończył się stratą 1,1953806877 i zapisał raport. Jest to wyłącznie weryfikacja techniczna, nie wynik eksperymentu pracy.
Pliki: kod/src/models/coreference.py, kod/train.py, kod/configs/baseline.yaml, kod/configs/dae.yaml, kod/configs/matrix_unet.yaml, kod/configs/smoke.yaml, kod/tests/test_smoke.py, wyniki/s05-smoke/.
Otwarte kwestie: Prawdziwy enkoder tekstowy i tensor reprezentacji wzmianek wymagają pełnych danych; zużycie GPU nie zostało zmierzone, ponieważ smoke run celowo wykonano na CPU.
Następny krok: [S-06]

## [S-06] Implementacja ewaluacji i baseline’ów — 2026-09-03
Zrobione: Zintegrowano niezmodyfikowany oficjalny CorefUD scorer przypięty do commitu 4fd7b0e0c661aeeff88bc60c19ef507b84d1b590. Dodano adapter raportujący MUC, B³, CEAF_e, CoNLL F1, LEA, BLANC i osobną detekcję wzmianek, transparentne metryki kontrolne, dokumentowy bootstrap oraz baseline’y head-match, regresję logistyczną mention-pair, opcjonalny adapter Stanza PL i adapter zero/few-shot do API LLM. Oficjalny smoke test na sztucznym CoNLL-U wygenerował CoNLL F1 0,6464, a test wewnętrzny 0,7282432845; wartości te są wyłącznie diagnostyczne. Kompilacja oraz 7 testów przeszły.
Pliki: kod/eval.py, kod/src/eval/, kod/src/baselines/, kod/scripts/pobierz_scorer.py, kod/configs/eval-smoke.yaml, kod/configs/eval-official-smoke.yaml, kod/tests/test_eval.py, kod/tests/fixtures/s06-*.conllu, kod/vendor/corefud-scorer/, wyniki/s06-internal-smoke.json, wyniki/s06-official-smoke.json.
Otwarte kwestie: Adapter Stanza i adapter LLM nie zostały uruchomione, ponieważ modele Stanza nie są lokalnie pobrane, a klucz API nie został dostarczony; oficjalne liczby eksperymentalne wymagają pełnych danych CorefUD.
Następny krok: [S-07]

## [S-07] Protokół eksperymentalny — 2026-09-03
Zrobione: Przed uruchomieniem eksperymentów zamrożono wspólną procedurę, pięć seedów, osiem eksperymentów głównych E1–E8 oraz siedem ablacji A1–A7. Każdy eksperyment ma hipotezę, konfigurację, metrykę rozstrzygającą i jawne kryterium sukcesu. Zdefiniowano dokumentowy bootstrap, sparowane porównania, korektę Holma, pomiar czasu, parametrów, inferencji, pamięci i kosztu LLM oraz wyjaśniono, dlaczego CoNLL F1 nie wystarcza.
Pliki: notatki/04-protokol-eksperymentow.md, POSTEP.md.
Otwarte kwestie: Pełne uruchomienia wymagają danych Polish-PCC, ukończonej anotacji prawnej, modeli Stanza i dostępu do API LLM; protokół rozdziela te braki od możliwych uruchomień zredukowanych.
Następny krok: [S-08]

## [S-08] Uruchomienia zredukowane — 2026-09-03
Zrobione: Zaimplementowano i trzykrotnie skontrolowano runner wspólnego syntetycznego splitu, ostatecznie rozdzielając seed danych od seedu modelu i włączając deterministyczny tryb CuBLAS. E1 i E2 uruchomiono deterministycznie, a E3–E5 dla pięciu zamrożonych seedów; każdy przebieg wygenerował checkpoint, predykcje CoNLL-U, pełne metryki oficjalnego scorera i pomiary kosztu. Surowe JSON-y i zbiorczy raport wyraźnie oznaczają dane jako syntetyczne. E6–E8 pozostawiono bez liczb z dokładnymi poleceniami i powodami braku.
Pliki: kod/scripts/run_reduced_experiments.py, kod/configs/reduced-e3.yaml, kod/configs/reduced-e4.yaml, kod/configs/reduced-e5.yaml, kod/configs/e6-full.yaml, kod/configs/e7-full.yaml, kod/configs/e8-full.yaml, wyniki/E1-reduced.json–E5-reduced.json, wyniki/s08-reduced-summary.json, wyniki/s08-runs/, notatki/05-wyniki-surowe.md, notatki/04-protokol-eksperymentow.md.
Otwarte kwestie: Brak pełnego Polish-PCC, ukończonej anotacji prawnej i klucza API uniemożliwia badawcze E6–E8 oraz przeniesienie syntetycznych liczb do wniosków pracy. Ablacje A1–A7 nie należały do wskazanego zakresu E1–En tej sesji.
Następny krok: [S-09]

## [S-09] Rozdziały 1–2 — 2026-09-03
Zrobione: Napisano w formie bezosobowej rozdział wstępny oraz podstawy teoretyczne i lingwistyczne koreferencji, łącznie około 3365 słów według statycznego licznika. Sformułowano zakres, tezę, PB1–PB3 i wkład, a następnie opisano reprezentację zadania, typy referencji, polską fleksję, podmioty zerowe, szyk, PCC i CorefUD. Dwie tabele mają podpisy, etykiety i wcześniejsze odwołania; wszystkie cytowane klucze istnieją, a nawiasy są zbilansowane.
Pliki: praca/rozdzialy/01-wstep.tex, praca/rozdzialy/02-koreferencja.tex, POSTEP.md.
Otwarte kwestie: Nie wykonano kompilacji PDF, ponieważ nadal brak jakiegokolwiek lokalnego silnika LaTeX; kontrolę kompilacyjną trzeba ponowić po instalacji narzędzia, najpóźniej w S-15.
Następny krok: [S-10]

## [S-10] Rozdziały 3–4 — 2026-09-03
Zrobione: Napisano przegląd rozwiązań koreferencji oraz podstawy i zastosowania autokoderów, łącznie około 4746 słów. Uporządkowano metody parowe, rankingowe, encyjne, spanowe, słowowe, generatywne i LLM, a następnie AE, DAE, VAE, regularyzacje, U-Net, DEC/IDEC i modele grafowe. Cztery tabele mają podpisy, etykiety i odwołania, wszystkie cytowane klucze istnieją, nawiasy są zbilansowane i nie dodano bibliografii.
Pliki: praca/rozdzialy/03-przeglad-rozwiazan.tex, praca/rozdzialy/04-autokodery.tex, POSTEP.md.
Otwarte kwestie: Kompilacja pozostaje niemożliwa z powodu braku silnika LaTeX; rozdział zachowuje jawne zastrzeżenia, że wyniki z innych zbiorów i protokołów nie tworzą rankingu.
Następny krok: [S-11]

## [S-11] Rozdziały 5–6 — 2026-09-03
Zrobione: Napisano rozdziały o specyfice dokumentów prawniczych, formalizacji zadania, hipotezach projektowych oraz danych, łącznie około 4218 słów. Opisano role, definicje, anonimizację, cytaty, przesunięcie domenowe, modele bazowe, źródła danych, manifesty, konwersję, okna, splity, anotację, zgodność i prywatność. Dwie tabele mają komplet odwołań, wszystkie cytowania istnieją i nawiasy są zbilansowane.
Pliki: praca/rozdzialy/05-teksty-prawnicze.tex, praca/rozdzialy/06-dane.tex, POSTEP.md.
Otwarte kwestie: W rozdziale danych pozostawiono dwie jawne luki: statystyki pełnego CorefUD-PL oraz statystyki i zgodność dla nieukończonej anotacji 24 dokumentów. Kompilacja nadal zablokowana brakiem silnika LaTeX.
Następny krok: [S-12]

## [S-12] Rozdziały 7–8 — 2026-09-03
Zrobione: Napisano rozdziały o projekcie i implementacji systemu oraz o protokole eksperymentalnym, łącznie około 3120 słów według statycznego licznika. Opisano wspólny interfejs tensorów, kontrolę neuronową, DAE, macierzowy U-Net, selektywną hybrydę, trening, testy, metryki, baseline’y, E1–E8, ablacje, bootstrap i pomiar kosztu. Uzupełniono selektor o opcjonalny próg błędu rekonstrukcji i test tej ścieżki; wszystkie 8 testów przeszło. Zainstalowano MiKTeX, dodano brakujące pakiety matematyczne i csquotes, a pełny cykl pdflatex–biber–pdflatex–pdflatex utworzył 81-stronicowy PDF bez brakujących cytowań i odwołań.
Pliki: praca/rozdzialy/07-system.tex, praca/rozdzialy/08-eksperymenty.tex, praca/main.tex, praca/main.pdf, kod/src/models/coreference.py, kod/tests/test_smoke.py, POSTEP.md.
Otwarte kwestie: Liczby z uruchomień syntetycznych nie są wynikami badawczymi; E6–E8 nadal wymagają pełnych danych, anotacji prawnej i dostępu do API. Kompilator zgłasza ostrzeżenia typograficzne overfull/underfull, które zostaną przejrzane w audycie technicznym.
Następny krok: [S-13]

## [S-13] Rozdziały 9–10 i wykresy — 2026-09-03
Zrobione: Napisano około 3530 słów wyników, analizy i porównania rozwiązań. Zestawiono E1–E5 bez nadawania syntetycznym liczbom statusu badawczego, opisano koszt, zmienność seedów, składowe metryk i konkretny przypadek nadmiernego scalenia. Dodano skrypt matplotlib oraz dwa wykresy o pojedynczych tezach: porównanie E3–E5 i t-SNE kodów DAE; oba zapisano jako PDF i PNG, oznaczono jako syntetyczne i skontrolowano wizualnie. Omówiono warunki, w których DAE, U-Net, LLM-only i hybryda mają sens, oraz zagrożenia dla trafności. Pełny cykl kompilacji utworzył 94-stronicowy PDF bez brakujących cytowań i odwołań.
Pliki: praca/rozdzialy/09-wyniki.tex, praca/rozdzialy/10-porownanie.tex, kod/scripts/wykresy.py, praca/rysunki/s13-jakosc-syntetyczna.pdf, praca/rysunki/s13-jakosc-syntetyczna.png, praca/rysunki/s13-tsne-latent-syntetyczny.pdf, praca/rysunki/s13-tsne-latent-syntetyczny.png, wyniki/s13-wykresy.json, praca/main.pdf, POSTEP.md.
Otwarte kwestie: Analiza błędów na konkretnych tekstach prawnych pozostaje oznaczona jako % LUKA, ponieważ nie istnieją ukończone złoto i predykcje dla legal-test. PB1–PB3 pozostają nierozstrzygnięte; E6–E8 nie zostały zastąpione symulowanymi liczbami.
Następny krok: [S-14]

## [S-14] Podsumowanie, streszczenia i załączniki — 2026-09-03
Zrobione: Napisano rozdział 11 z jawnym statusem PB1–PB3 i tezy, wkładem, ograniczeniami oraz kolejnością dalszych badań. Dodano streszczenie polskie i abstract angielski po około 200 słów, słowa kluczowe oraz wykaz 22 skrótów. Utworzono załącznik LaTeX i samodzielną kartę reprodukcji z wersjami, seedami, poleceniami, artefaktami i warunkami wykonania E4–E8. Dziennik założeń rozszerzono o status wyników syntetycznych, brak E6–E8, ograniczenia t-SNE i nieznane dane autora. Pełna kompilacja utworzyła 100-stronicowy PDF bez brakujących cytowań i referencji.
Pliki: praca/rozdzialy/11-podsumowanie.tex, praca/streszczenia.tex, praca/wykaz-skrotow.tex, praca/zalaczniki.tex, praca/main.tex, praca/main.pdf, zalaczniki/karta-reprodukcji.md, DZIENNIK_ZALOZEN.md, kod/requirements.txt, POSTEP.md.
Otwarte kwestie: Teza pozostaje niepotwierdzona i nieobalona w zaplanowanym teście z powodu brakujących danych naturalnych i E6–E8. Na stronie tytułowej pozostaje nieznane imię i nazwisko autora; kompilacja ma ostrzeżenia typograficzne overfull, ale nie ma brakujących odwołań.
Następny krok: [S-15]

## [S-15] Złożenie całości, spójność i kompilacja — 2026-09-03
Zrobione: Wykonano końcowy cykl pdflatex–biber–pdflatex–pdflatex. Powstał 100-stronicowy praca/main.pdf (SHA-256: 13551367231E1E018AE9CD38433B4CD9549C05EDC8528308BACC5107146CCA27). Log nie zawiera ostrzeżeń o brakujących cytowaniach lub referencjach, pustej bibliografii, nieobsługiwanym typie wpisu, zduplikowanej kotwicy strony ani overfull hbox. Wszystkie 57 pozycji bibliografii jest cytowanych, nie ma kluczy niezdefiniowanych; 15 tabel i rysunków ma odwołania w tekście. Nie znaleziono zduplikowanych etykiet, brakujących referencji, niezbilansowanych klamer ani pierwszoosobowych sformułowań autorskich. Skróty z wykazu sprawdzono względem kolejności dokumentu i rozwinięto przy pierwszym użyciu. Kompilacja składniowa kodu i 8 testów zakończyły się powodzeniem.
Liczba słów według statycznego licznika po usunięciu komentarzy i części poleceń LaTeX: R1 1149; R2 2335; R3 2510; R4 2355; R5 2046; R6 2278; R7 1302; R8 1328; R9 1642; R10 1661; R11 1017; razem 19 623, czyli w docelowym zakresie 18–25 tys. Streszczenie PL ma 200 słów, abstract EN 230 słów.
Lista jawnych braków z przeszukania praca/: (1) dane autora na stronie tytułowej — praca/tytulowa.tex:8–9; (2) aktualna treść oświadczenia wydziałowego — praca/oswiadczenie.tex:3–4; (3) statystyki pełnych splitów CorefUD-PL — praca/rozdzialy/06-dane.tex:146; (4) statystyki i zgodność anotatorów korpusu prawnego — praca/rozdzialy/06-dane.tex:147; (5) analiza błędów na uzgodnionych przykładach prawnych i predykcjach E3–E8 — praca/rozdzialy/09-wyniki.tex:111. Nie znaleziono znaczników TODO ani XXX.
Pliki: praca/main.tex, praca/main.pdf, praca/main.log, praca/main.bbl, praca/bibliografia.bib, praca/streszczenia.tex, praca/tytulowa.tex, praca/oswiadczenie.tex, praca/rozdzialy/02-koreferencja.tex, praca/rozdzialy/06-dane.tex, praca/rozdzialy/07-system.tex, praca/rozdzialy/08-eksperymenty.tex, praca/rozdzialy/11-podsumowanie.tex, praca/zalaczniki.tex, POSTEP.md.
Otwarte kwestie: Do formalnego złożenia trzeba podać imię i nazwisko autora oraz aktualny wzór oświadczenia. Do uzyskania wyników badawczych i rozstrzygnięcia tezy nadal trzeba pobrać pełny CorefUD-PL, ukończyć podwójną anotację prawną i wykonać E4–E8; obecny PDF uczciwie raportuje te braki.
Następny krok: [KONIEC]
## [S-16] Trening na Polish-PCC i transfer do ELI — 2026-09-03
Zrobione: Pobrano i zamrożono CorefUD 1.4 (SHA-256 archiwum: 51814a8e2996f459cf3f4fa491c161b4fd59991d3390b4484dac901600cd9173), zachowano licencję CC BY 3.0 i skonwertowano Polish-PCC: train 1463 dokumenty, 446 420 tokenów i 154 166 fragmentów wzmianek; dev 183 dokumenty, 55 820 tokenów i 19 300 fragmentów. Poprawiono parser sąsiadujących zamknięć i identyfikatorów części nieciągłych, dodając testy regresyjne. Zamrożony HerBERT utworzył 3339 okien treningowych, 559 kalibracyjnych i 500 dev; kontrolę oraz DAE wytrenowano po 5 epok dla seedu 20260903. Na dev kontrola uzyskała CoNLL F1 0,5606 i LEA 0,5078, a DAE 0,5510 i 0,5007; DAE poprawił parowy F1 z 0,5585 do 0,5763, ale nie metrykę główną. Na Dz.U. 2024 poz. 1984 wykonano jakościowy transfer z kandydatami Stanza; po usunięciu treści JavaScript z ekstraktora ELI DAE zwrócił 14 łańcuchów, ujawniając poprawne powtórzenia nazw i nadmierne scalanie redakcyjnych powtórzeń. Wyniki zagregowano i wprowadzono do rozdziałów 6, 9 i 11.
Pliki: PLAN_TRENINGU_I_TRANSFERU.md, kod/src/data/konwersja.py, kod/src/data/tensorization.py, kod/train.py, kod/scripts/prepare_corefud_tensors.py, kod/scripts/evaluate_corefud_model.py, kod/scripts/predict_legal_coreference.py, kod/scripts/summarize_real_pilot.py, kod/scripts/pobierz_dane.py, kod/configs/real-pcc-*.yaml, kod/tests/test_data_conversion.py, kod/tests/test_real_pipeline.py, kod/data/raw/corefud-1.4/, kod/data/processed/corefud-1.4/, wyniki/real-pcc/, praca/rozdzialy/06-dane.tex, praca/rozdzialy/09-wyniki.tex, praca/rozdzialy/11-podsumowanie.tex, DZIENNIK_ZALOZEN.md, POSTEP.md.
Otwarte kwestie: Jest to pilot jednego seedu z oceną klastrowania na złotych wzmiankach w oknach, nie pełny wynik end-to-end. Akt ELI nie ma złotej anotacji, dlatego nie obliczono dla niego F1. PB1 wymaga pięciu seedów, bootstrapu, domenowej adaptacji i uzgodnionego legal-test; E6--E8 pozostają niewykonane według pełnego protokołu.
Następny krok: podwójna anotacja legal-test i pełne uruchomienie wielu seedów.

## [S-17] Srebrny korpus prawny ELI-400 i CorPipe 26 — 2026-09-03
Zrobione: Utworzono deterministyczny korpus 400 fragmentów aktów ELI z lat 2017–2024, po 200 z Dz.U. i M.P., w 23 typach aktów oraz podziale dokumentowym 320/40/40. Zapisano 127 542 słowa źródłowe bez błędów kodowania. Stanza PL oznaczyła 53 034 wzmianki w 36 989 klastrach; parser odtworzył z CoNLL-U dokładnie 53 034 wzmianki. Pobrano i uruchomiono CorPipe 26 base na identycznych tokenach: 55 977 wzmianek powierzchniowych, 298 zerowych i 37 292 klastry. Dokładnie wspólnych było 38 082 spanów, a zgodność par wspólnych spanów wyniosła 66,52%; oficjalna zgodność systemów wyniosła mention F1 69,65%, CoNLL 58,40% i LEA 51,33%, co nie jest accuracy. Na złotym Polish-PCC dev CorPipe end-to-end uzyskał CoNLL 72,97%, LEA 68,40% i mention F1 93,11%, wobec DAE 55,10%, 50,07% i 100% przy złotych wzmiankach. CorPipe przyjęto jako główny nauczyciel srebrny, Stanza jako sygnał zgodności. Utworzono CorefUD, JSONL, osobne splity, manifesty, 37 292 wiersze przeglądu klastrów i 56 275 wierszy przeglądu wzmianek. Wszystkie 21 testów przechodzi.
Pliki: kod/scripts/build_legal_silver_corpus.py, kod/scripts/rebuild_legal_conllu.py, kod/scripts/prepare_corpipe_legal_pilot.py, kod/scripts/build_corpipe_legal_json.py, kod/scripts/finalize_legal_silver_corpus.py, kod/scripts/evaluate_corefud_pair.py, kod/data/raw/legal-silver-400/, kod/data/processed/legal-silver-400/, kod/models/corpipe26-onestage-corefud1.4-base-260702/, kod/vendor/corpipe26/, wyniki/corpipe26-pcc-dev/, wyniki/legal-silver-400/RAPORT.md.
Otwarte kwestie: Korpus pozostaje srebrny. Przed raportowaniem wyniku prawnego trzeba ręcznie poprawić co najmniej całe dev/test, zamrozić test i dopiero wtedy trenować oraz ewaluować autokoder. Checkpoint CorPipe ma licencję CC BY-NC-SA 4.0; warunki redystrybucji trzeba zachować.
Następny krok: ręczna korekta legal-dev/test, następnie trening domenowy na `corpipe26/splits/train.jsonl`.
