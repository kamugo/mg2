# Protokół eksperymentalny

## 1. Cel i zasady zamrożenia

Protokół zapisano przed uruchomieniem eksperymentów badawczych. Jednostką podziału danych i bootstrapu jest dokument, a nie wzmianka ani para. Wszystkie warianty otrzymują te same zamrożone splity CorefUD Polish-PCC oraz, po ukończeniu anotacji, ten sam test prawniczy. Hiperparametry i progi dobiera się wyłącznie na zbiorze deweloperskim. Zbiór testowy wolno ocenić dopiero po zamrożeniu konfiguracji.

Głównym ustawieniem scorera jest oficjalny CorefUD scorer przypięty w repozytorium, head-match, dopasowanie zer metodą zależnościową i pominięcie singletonów w metrykach klastrowych. Detekcję wzmianek raportuje się osobno z singletonami. Dodatkowo wykonuje się analizę exact-match i wariant z singletonami, lecz nie wykorzystuje się ich do wyboru modelu.

## 2. Wspólna procedura

- Dane nadzorowane: zamrożone wydanie Polish-PCC w CorefUD, bez przemieszania dokumentów między splitami.
- Dane domenowe: wyłącznie teksty prawne dopuszczone przez audyt licencji i PII; nie zawierają etykiet ze zbioru testowego.
- Enkoder domyślny: HerBERT base, okno 512 tokenów, zamrożony podczas podstawowego pretrainingu DAE.
- Kandydaci: maksymalnie 128 wzmianek w oknie; okna dokumentu scala się wyłącznie po identyfikatorach wzmianek i ocenach z nakładającego się kontekstu.
- Seedy główne: 20260903, 20260917, 20261001, 20261015 i 20261029.
- Wybór checkpointu: najwyższy CoNLL F1 na dev; przy remisie wyższe LEA, następnie niższy koszt inferencji.
- Wczesne zatrzymanie: brak poprawy CoNLL F1 na dev przez pięć ewaluacji.
- Raportowanie: średnia, odchylenie standardowe i wyniki każdego seedu; żadnego wybierania najlepszego seedu.

## 3. Eksperymenty główne

| ID | Hipoteza | Konfiguracja | Metryka rozstrzygająca | Kryterium sukcesu |
|---|---|---|---|---|
| E1 | Prosty sygnał leksykalny stanowi dolną granicę jakości. | Deterministyczny head/lemma-match, bez uczenia. | CoNLL F1 na teście. | Uzyskanie kompletnego, odtwarzalnego punktu odniesienia; brak progu jakościowego. |
| E2 | Uczony klasyfikator par przewyższa regułę leksykalną. | Regresja logistyczna mention-pair; cechy zgodności i odległości; próg z dev. | Różnica CoNLL F1 E2−E1. | Dolna granica 95% CI różnicy jest większa od 0. |
| E3 | Lekka neuronowa głowica nad niekompresowanymi reprezentacjami przewyższa baseline’y klasyczne. | Wariant baseline z CoreferenceModel, bez DAE; pięć seedów. | Różnica CoNLL F1 E3−E2. | Średnia różnica dodatnia, a 95% sparowany CI nie obejmuje 0. |
| E4 | Domenowo pretrenowany DAE poprawia koreferencję przy małym budżecie parametrów. | DAE 768→384→128→384→768, następnie głowica par; pięć seedów. | Różnica CoNLL F1 E4−E3. | CoNLL F1 rośnie o co najmniej 0,01 bez spadku LEA większego niż 0,005. |
| E5 | Segmentacja macierzy wzmianek wykorzystuje strukturę globalną lepiej niż niezależne pary. | U-Net macierzy M×M, kanały 32–64–128, skip-connections; pięć seedów. | Różnica LEA E5−E3. | LEA rośnie i 95% sparowany CI różnicy nie obejmuje 0; raportuje się również CoNLL F1. |
| E6 | Selektywne zapytania do LLM poprawiają trudne decyzje przy ograniczonym koszcie. | E4 + selektor marginesu/błędu rekonstrukcji, maks. 16 zapytań na dokument. | CoNLL F1 oraz odsetek wysłanych kandydatów. | CoNLL F1 nie mniejsze niż E4 i co najmniej 80% mniej zapytań niż LLM-only. |
| E7 | Few-shot LLM stanowi jakościowy, lecz droższy punkt odniesienia. | Ten sam model API, temperatura 0, wersjonowany prompt: zero-shot oraz 3 demonstracje z train. | CoNLL F1, tokeny i koszt na dokument. | Wynik raportowy; sukces techniczny oznacza poprawny JSON dla co najmniej 99% odpowiedzi po jednej repetycji. |
| E8 | Transfer na tekst prawny ujawni korzyść pretrainingu domenowego silniej niż test ogólny. | Porównanie E3/E4/E5 na zamrożonym, ręcznie anotowanym teście prawnym. | CoNLL F1 i LEA na podzbiorze prawnym. | Różnica E4−E3 jest większa na prawie niż na Polish-PCC; wniosek wymaga dodatniego CI interakcji. |

## 4. Ablacje

| ID | Ablacja | Porównanie | Hipoteza i kryterium |
|---|---|---|---|
| A1 | Bez skip-connections | E5 z konkatenacjami pominiętymi, ten sam budżet kroków | Skip-connections są użyteczne, jeśli pełny E5 ma wyższy średni LEA i dodatni CI różnicy. |
| A2 | Bez pretrainingu domenowego | Architektura E4 z losowo zainicjalizowanym DAE | Pretraining jest użyteczny, jeśli E4 przewyższa A2 w CoNLL F1 przy tej samej liczbie parametrów. |
| A3 | Przestrzeń latentna | 64, 128 i 256 wymiarów | Wybiera się najmniejszy wymiar mieszczący się w 0,005 CoNLL F1 od najlepszego na dev; test raportuje się tylko dla wyboru. |
| A4 | Enkoder | HerBERT base, HerBERT large i wielojęzyczny enkoder użyty w CorefUD | Enkoder rozstrzyga się na dev według CoNLL F1, a koszt stanowi kryterium drugorzędne. |
| A5 | Długość okna | 256, 512 i 1024 tokeny; dla 1024 wyłącznie zgodny enkoder | Dłuższy kontekst jest użyteczny, jeśli poprawia recall długich zależności i LEA przy akceptowalnej pamięci. |
| A6 | Bez straty rekonstrukcji przy fine-tuningu | E4 z λ_rec=λ_cos=0 po pretrainingu | Cel wspólny jest użyteczny, jeśli pełny E4 ma wyższy CoNLL F1 bez destabilizacji między seedami. |
| A7 | Bez kary przechodniości | E5 z λ_tri=0 | Kara jest użyteczna, jeśli zmniejsza liczbę naruszeń przed union-find i poprawia LEA. |

## 5. Plan istotności statystycznej

Dla każdego systemu wyznacza się 95-procentowy przedział ufności przez 10 000 losowań dokumentów z powtórzeniami. Systemy porównuje się sparowanym bootstrapem: w każdej replice oba systemy otrzymują identyczny multizbiór dokumentów. Raportuje się różnicę, przedział percentylowy i dwustronną wartość p; poziom α=0,05 koryguje się metodą Holma osobno w rodzinach: modele główne, ablacje i domeny. Dodatkowo podaje się rozrzut między pięcioma seedami. Jeżeli w teście prawnym liczba dokumentów będzie mniejsza niż 20, przedziały opisuje się jako eksploracyjne i nie formułuje mocnego wniosku o braku efektu.

## 6. Metryki i powód raportowania więcej niż CoNLL F1

CoNLL F1 jest średnią F1 z MUC, B³ i CEAF_e. Sama średnia ukrywa różne błędy: MUC słabo karze nadmierne łączenie dużych klastrów i pomija singletony, B³ waży wynik wzmiankami, a CEAF_e wymusza globalne dopasowanie klastrów. Dwa systemy mogą zatem uzyskać podobną średnią mimo odmiennego zachowania praktycznego.

LEA eksponuje poprawność powiązań ważoną rozmiarem encji, BLANC rozdziela decyzje koreferencyjne i niekoreferencyjne, a precision/recall detekcji wzmianek odróżnia błąd wykrycia od błędu klasteryzacji. Osobno raportuje się zera, nazwy, deskrypcje nominalne, zaimki jawne, odległość poprzednika i długość dokumentu. Wniosek o użyteczności nie może opierać się na CoNLL F1, jeżeli LEA lub recall detekcji wskazuje istotną regresję.

## 7. Pomiar kosztu

Dla każdego uruchomienia zapisuje się:

- czas uczenia całkowity i na epokę mierzony zegarem monotonicznym;
- liczbę wszystkich i trenowanych parametrów;
- medianę, średnią i percentyl 95 czasu inferencji na dokument po pięciu rozgrzewkach;
- szczytową pamięć GPU z torch.cuda.max_memory_allocated, a na CPU maksymalny RSS procesu;
- liczbę tokenów wejścia/wyjścia, liczbę zapytań i koszt według zamrożonego cennika dla LLM;
- wersję GPU, sterownika, CUDA, PyTorch, scorera, danych i commit kodu.

Porównanie kosztowe wykorzystuje ten sam sprzęt, batch, precyzję i kolejność dokumentów. Pomiar GPU poprzedza synchronizacja CUDA. Prekomputacja embeddingów jest raportowana oddzielnie, aby nie ukrywać kosztu enkodera.

## 8. Status odtwarzalności

Na moment zamrożenia protokołu istnieją konfiguracje YAML, seedy, trening syntetyczny, baseline’y, oficjalny scorer i testy techniczne. Wyniki smoke z S-05 i S-06 potwierdzają wyłącznie działanie kodu i nie rozstrzygają hipotez E1–E8 ani A1–A7. Nie pobrano pełnego Polish-PCC, nie ukończono anotacji prawnej, nie uruchomiono Stanza ani API LLM i nie wykonano jeszcze pięciu seedów. Każdy brakujący wynik musi pozostać oznaczony jako DO UZUPEŁNIENIA do chwili wygenerowania przez kod z repozytorium.

### Aktualizacja po uruchomieniach zredukowanych S-08

Potok E1–E5 wykonano na wspólnych sztucznych splitach; E3–E5 uruchomiono dla wszystkich pięciu zaplanowanych seedów, a wynik każdego przebiegu przeliczono oficjalnym scorerem. Runner zapisuje wersje środowiska, oddzielne seedy danych, konfigurację deterministycznego CuBLAS, checkpointy, predykcje CoNLL-U i pełne wyjście scorera. Są to testy integracyjne, nie wyniki badawcze. E6–E8 i wszystkie eksperymenty na pełnym CorefUD lub danych prawnych pozostają jawnie nieuruchomione z poleceniami reprodukcji w notatki/05-wyniki-surowe.md.
