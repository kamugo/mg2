# Plan pracy

## Teza

Włączenie autokodera uczonego na danych domenowych do systemu rozstrzygania koreferencji w polskich tekstach prawniczych pozwala uzyskać statystycznie istotną poprawę jakości mierzonej CoNLL F1 względem architektonicznie porównywalnego wariantu bez autokodera, przy niższym koszcie adaptacji niż w rozwiązaniu opartym wyłącznie na dużym modelu językowym (large language model, LLM).

## Pytania badawcze

1. **PB1.** Czy dodanie autokodera uczonego na danych domenowych zwiększa CoNLL F1 i LEA na polskich tekstach prawniczych względem tego samego enkodera i procedury klastrowania bez autokodera, przy identycznym podziale danych i budżecie strojenia? Odpowiedź jest negatywna, jeżeli poprawa CoNLL F1 nie jest istotna w sparowanym teście bootstrapowym przy poziomie istotności 0,05 lub pogarsza LEA.
2. **PB2.** Który sposób użycia autokodera — segmentacja macierzy relacji, kompresja reprezentacji wzmianek czy odszumiające uczenie wstępne — daje najlepszy kompromis jakości, liczby trenowanych parametrów, czasu uczenia i pamięci GPU? Pytanie rozstrzyga porównanie wariantów przy wspólnym enkoderze, danych, metrykach i budżecie obliczeniowym; brak wariantu dominującego lub przewagi na co najmniej dwóch seedach obala hipotezę o jednoznacznie najlepszym rozwiązaniu.
3. **PB3.** Czy hybryda autokodera i LLM ogranicza liczbę tokenów przesyłanych do LLM oraz koszt i czas inferencji bez istotnej utraty CoNLL F1 względem wariantu LLM-only, a zarazem przewyższa wariant bez LLM? Odpowiedź jest negatywna, jeżeli redukcja kosztu nie występuje albo różnica jakości na korzyść LLM-only jest istotna statystycznie.

## Rozwinięty spis treści

### 1. Wstęp

- **1.1. Motywacja i zakres** — przedstawienie potrzeby wiązania wzmianek w długich polskich tekstach prawniczych oraz granic badanego problemu.
- **1.2. Cel, teza i pytania badawcze** — operacjonalizacja celu z karty pracy w postaci falsyfikowalnych twierdzeń.
- **1.3. Wkład własny i układ pracy** — wskazanie projektowanych wariantów, protokołu porównawczego i organizacji rozdziałów.

### 2. Koreferencja — podstawy teoretyczne i lingwistyczne

- **2.1. Definicje i reprezentacja zadania** — omówienie wzmianek, poprzedników, łańcuchów i partycji encji.
- **2.2. Zjawiska koreferencyjne** — rozróżnienie anafory, katafory, koreferencji nominalnej, zaimkowej i zerowej.
- **2.3. Specyfika języka polskiego** — analiza wpływu fleksji, elipsy podmiotu i swobodnego szyku wyrazów.

### 3. Przegląd istniejących rozwiązań

- **3.1. Metody regułowe i statystyczne** — przedstawienie systemów sitowych, mention-pair i mention-ranking.
- **3.2. Metody neuronowe** — porównanie modeli span-based, entity-based i generatywnych.
- **3.3. LLM i narzędzia dla polszczyzny** — ocena dostępnych modeli, ich adaptowalności i ograniczeń kosztowych.

### 4. Autokodery — podstawy i zastosowania

- **4.1. Rodziny autokoderów** — opis AE, DAE, VAE oraz wariantów sparse i contractive.
- **4.2. Segmentacja i klastrowanie** — omówienie U-Net, macierzy relacji i uczenia przestrzeni latentnej.
- **4.3. Transfer do koreferencji** — uzasadnienie użycia autokodera do adaptacji domenowej i redukcji szumu.

### 5. Specyfika tekstów prawniczych i problem badawczy

- **5.1. Cechy dokumentów prawniczych** — analiza terminów definiowanych, anonimizacji, dalekich zależności i szablonowości.
- **5.2. Formalizacja zadania** — zapis wykrywania wzmianek i klastrowania encji wraz z ograniczeniami domenowymi.
- **5.3. Hipotezy projektowe** — przełożenie tezy i pytań badawczych na porównywane warianty systemu.

### 6. Dane i ich przygotowanie

- **6.1. Korpusy ogólne i domenowe** — wybór danych z uwzględnieniem licencji, anonimizacji i reprezentatywności.
- **6.2. Konwersja i podział danych** — opis wspólnego formatu, tokenizacji oraz podziału train/dev/test bez przecieku dokumentów.
- **6.3. Anotacja i kontrola jakości** — zdefiniowanie instrukcji anotacji, przypadków spornych i zgodności anotatorów.

### 7. Projekt i implementacja systemu

- **7.1. Architektury** — specyfikacja wariantów autokodera, tensorów wejściowych, głowic i procedury klastrowania.
- **7.2. Uczenie** — opis funkcji strat, strategii strojenia, seedów i ograniczeń pamięciowych.
- **7.3. Implementacja i odtwarzalność** — przedstawienie konfiguracji, logowania, wersji zależności i sposobu uruchamiania.

### 8. Plan i przebieg eksperymentów

- **8.1. Metryki i rozwiązania bazowe** — określenie MUC, B³, CEAF_e, CoNLL F1, LEA, BLANC i jakości wykrywania wzmianek.
- **8.2. Eksperymenty i ablacje** — zaplanowanie porównań architektur, wymiarów latentnych, pretrainingu, skip-connections i długości okna.
- **8.3. Istotność i koszt** — ustalenie bootstrapu, wielu seedów oraz pomiaru parametrów, czasu, pamięci i tokenów API.

### 9. Wyniki i ich analiza

- **9.1. Wyniki główne** — raport jakości wszystkich wariantów na niezmienionym zbiorze testowym.
- **9.2. Ablacje i analiza błędów** — identyfikacja wpływu komponentów oraz klas błędów na przykładach prawniczych.
- **9.3. Efektywność** — zestawienie jakości z kosztem uczenia, inferencji i adaptacji.

### 10. Porównanie z rozwiązaniami alternatywnymi

- **10.1. Porównanie metod** — odniesienie autokoderów do baseline'ów regułowych, klasycznych, neuronowych i LLM.
- **10.2. Kompromis jakość–koszt** — ocena zakresów, w których autokoder lub hybryda są praktycznie uzasadnione.
- **10.3. Ograniczenia trafności** — omówienie wpływu danych, anotacji, domeny i zasobów na możliwość uogólnienia wyników.

### 11. Podsumowanie i wnioski

- **11.1. Odpowiedzi na pytania badawcze** — jawne przyjęcie albo odrzucenie każdego twierdzenia na podstawie wyników.
- **11.2. Wkład, ograniczenia i dalsze prace** — podsumowanie wartości rozwiązania oraz wskazanie kierunków replikacji i rozwoju.

## Mapowanie pytań na rozdziały i eksperymenty

| Pytanie | Rozdziały | Eksperyment rozstrzygający |
|---|---|---|
| PB1 | 5, 7–9 | **E1:** porównanie ablation-pair „ten sam enkoder i klasteryzator bez autokodera” kontra „z autokoderem”, na identycznych splitach i seedach; rozstrzygają CoNLL F1, LEA i sparowany bootstrap. |
| PB2 | 4, 7–9 | **E2:** porównanie segmentacji macierzy, kompresji wzmianek i odszumiającego pretrainingu wraz z ablacjami; oceniane są jakość, parametry trenowane, GPU-hours, pamięć i czas inferencji. |
| PB3 | 3, 7–10 | **E3:** porównanie AE-only, LLM-only i hybrydy przy wspólnym teście; mierzone są CoNLL F1, tokeny API, koszt, opóźnienie oraz istotność różnic jakości. |

Kontrola nietrywialności tezy została ograniczona do czterech zapytań zgodnie z budżetem sesji; nie uzyskano materiału pozwalającego uznać, że identyczny układ „autokoder + polska koreferencja prawnicza + ocena kosztu adaptacji” został już rozstrzygnięty, dlatego weryfikację stanu badań pozostawiono kwerendom S-02a–S-02e.
