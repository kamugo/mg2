# Duże modele językowe w rozstrzyganiu koreferencji

Stan weryfikacji: 2026-09-03. Przez LLM rozumie się tu duży model językowy (large language model), używany przez instrukcję, uczenie w kontekście, strojenie generatywne albo jako nauczyciel. Wyniki koreferencji encji i zdarzeń rozdzielono, ponieważ ich bezpośrednie porównanie byłoby błędne.

## 1. Zero-shot prompting jako baseline

W wariancie zero-shot model otrzymuje definicję zadania, dokument i wymagany schemat odpowiedzi bez przykładów demonstracyjnych. Zaletą jest brak treningu i szybkie uruchomienie na nowej domenie; wadami są koszt inferencji, niestabilny format i wrażliwość na brzmienie instrukcji. Gan i in. pokazują, że deklaratywne rozumienie koreferencji przez LLM nie przekłada się automatycznie na wyniki zgodne z tradycyjnymi scorerami \cite{gan_2024_llm_coref}. Autorzy kontrolują osobno wykrywanie wzmianek, ponieważ błąd formatu lub granicy może przesłonić właściwą decyzję referencyjną. Dla polskiego korpusu prawniczego baseline powinien używać temperatury 0, wersjonowanego promptu i walidacji składni wyjścia.

Wiersz porównawczy: LLM zero-shot | eksperymenty na benchmarkach angielskich | tradycyjne metryki koreferencji | brak jednej porównywalnej wartości w abstrakcie | gan_2024_llm_coref

## 2. Few-shot i chain-of-thought

Few-shot prompting dodaje do kontekstu kilka par wejście--złota odpowiedź; wariant chain-of-thought (CoT) prosi również o uzasadnienie. W badaniu Gana i in. few-shot CoT był najbardziej stabilnym wariantem dla rodzin GPT i Llama 2, lecz udostępnianie rozumowania zwiększa długość odpowiedzi i utrudnia parser \cite{gan_2024_llm_coref}. Przykłady muszą być dobierane wyłącznie z treningu, aby nie przeciec do dev/test. Dla polszczyzny powinny obejmować podmiot zerowy, fleksję i długą zależność, a dla prawa dodatkowo terminy definiowane i role procesowe. Uzasadnienie można zachować do analizy błędów, natomiast scorer powinien otrzymywać tylko kanoniczną strukturę klastrów.

Wiersz porównawczy: few-shot CoT | benchmarki angielskie | stabilność i metryki koreferencji | najlepszy jakościowo wariant promptu; liczba nieprzepisana | gan_2024_llm_coref

## 3. Few-shot z długim kontekstem

Sajid i in. umieszczają w długim kontekście przykłady tekst--anotacja i generują oznaczony dokument w formacie text-to-text \cite{sajid_2025_fewshot}. Użyty Gemini 2.5 Pro osiągnął CoNLL F1 61,74 na mini-zbiorze testowym CRAC 2025, a autorzy raportują poprawę wraz z liczbą demonstracji. Wynik nie jest bezpośrednio porównywalny z pełnym testem ani z wynikami innego wydania CorefUD. Podejście nie wymaga strojenia wag, ale każde wywołanie powtarza przykłady, przez co rosną tokeny, opóźnienie i koszt. W hybrydzie autokoder powinien wybrać niewielką liczbę niepewnych par i ich kontekstów, zamiast wysyłać cały dokument.

Wiersz porównawczy: Gemini 2.5 Pro few-shot | CRAC 2025 mini-test, wiele języków | CoNLL F1 | 61,74 [mini-test] | sajid_2025_fewshot

## 4. LLM jako pełny model generatywny

Strojenie modelu text-to-text zamienia dokument w tekst z osadzonymi identyfikatorami wzmianek i klastrów. Hejman i in. dostrajają Llama 3.1-8B, reprezentują wzmiankę przez głowę składniową i uczą generowania pustych węzłów \cite{hejman_2025_llama}. Podejście jest ekspresywne, lecz może zmienić treść, zgubić nawias lub przypisać niespójne identyfikatory. Zbiorcze wyniki CRAC 2025 wskazują, że klasyczne systemy nadal prowadziły mimo potencjału czterech systemów LLM \cite{novak_2025_crac}. Pełne strojenie ośmiomiliardowego modelu przekracza preferowany budżet pojedynczej karty 16--24 GB bez kwantyzacji lub adapterów, dlatego nie jest wariantem głównym.

Wiersz porównawczy: fine-tuned Llama 3.1-8B | CorefUD 1.3, 22 zbiory / 17 języków | CoNLL F1 | — | hejman_2025_llama

## 5. Porównanie generowania i systemu specjalistycznego

GLaRef porównuje klasyczny model par z systemem generatywnym na wspólnym teście CRAC 2025 \cite{seminck_2025_glaref}. Średnie CoNLL F1 wyniosło odpowiednio 61,57 i 62,96, lecz system parowy zużył mniej niż 10% kosztu obliczeniowego wariantu LLM. Autorzy wskazują, że generacja tekstu utrudnia zachowanie globalnie spójnej reprezentacji koreferencji. Jest to bezpośrednie uzasadnienie raportowania nie tylko jakości, lecz także tokenów, czasu i pamięci. W pracy wariant LLM-only ma być górnym punktem odniesienia o kontrolowanym budżecie, nie domyślnym rozwiązaniem produkcyjnym.

Wiersz porównawczy: GLaRef pairwise / generatywny | CRAC 2025 test | średni CoNLL F1 | 61,57 / 62,96; pairwise <10% kosztu LLM | seminck_2025_glaref

## 6. LLM do generowania pseudoetykiet

LLM może pełnić rolę anotatora: zwracać kandydackie łańcuchy, etykiety par lub krótkie uzasadnienia dla danych bez złota. Zhao i in. formułują międzydokumentową koreferencję zdarzeń jako klasyfikację par i stwierdzają, że GPT-4 zero-shot przewyższa crowdworkerów oraz zbliża się do przeszkolonych anotatorów \cite{zhao_2023_gpt}. Jednocześnie model bywa nadmiernie pewny i wymusza decyzję przy niedostatecznej informacji, więc pseudoetykiety nie mogą zostać uznane za złote. Bezpieczny pipeline wymaga progu pewności, zgodności dwóch niezależnych predykcji, kontroli człowieka na próbce i całkowitego wyłączenia dokumentów testowych. Zastosowanie do encji w polskim prawie pozostaje hipotezą, ponieważ przytoczona praca dotyczy angielskiej koreferencji zdarzeń.

Wiersz porównawczy: GPT-4 jako anotator | cross-document event coreference | zgodność / klasyfikacja par | porównywalny z przeszkolonymi anotatorami; brak jednej liczby w abstrakcie | zhao_2023_gpt

## 7. Racjonalizacje i destylacja LLM do modelu specjalistycznego

Nath i in. generują za pomocą LLM swobodne racjonalizacje dla par zdarzeń, a następnie używają ich jako odległego nadzoru dla mniejszego scorera \cite{nath_2024_rationale}. Model studenta działa po kosztownym etapie wytworzenia danych i nie wymaga wywołania LLM dla każdego dokumentu produkcyjnego. Publikacja raportuje stan sztuki w B³ F1 na ECB+ i GVC, ale dotyczy międzydokumentowej koreferencji zdarzeń, więc liczby nie powinny być przenoszone do PCC. Dla projektu analogią jest nauczyciel oceniający wyłącznie niepewne pary wskazane przez AE, przy zachowaniu zwykłych złotych etykiet jako nadrzędnego celu. Racjonalizacje mogą wnosić halucynacje, dlatego student powinien uczyć się ważonym celem i zostać oceniony wyłącznie na nietkniętym złotym teście.

Wiersz porównawczy: LLM-rationales + student | ECB+, GVC, AIDA Phase 1 | B³ F1 | SOTA według autorów; liczba nieprzepisana | nath_2024_rationale

## 8. Destylacja klasycznego nauczyciela

F-coref pokazuje tańszy odpowiednik idei nauczyciel--uczeń bez konieczności generatywnego LLM \cite{otmazgin_2022_fcoref}. Twarda destylacja przenosi srebrne etykiety LingMess do modelu o 91 mln parametrów zamiast 494 mln i korzysta z efektywnego batchingu. System przetwarza 2,8 tys. dokumentów OntoNotes w 25 s na V100, wobec 6 min LingMess i 12 min modelu AllenNLP. Wynik dowodzi praktycznej wartości pseudoetykiet, ale nie przesądza, czy droższy LLM byłby lepszym nauczycielem dla polskiego prawa. F-coref wyznacza obowiązkowy baseline kosztowy dla każdej proponowanej destylacji LLM.

Wiersz porównawczy: F-coref | OntoNotes | czas 2,8 tys. dokumentów | 25 s; LingMess 6 min; AllenNLP 12 min | otmazgin_2022_fcoref

## 9. Stan dla języka polskiego

Saputa i in. oceniają modele instrukcyjne na Polish Coreference Corpus przez zgodność instrukcja--odpowiedź \cite{saputa_2024_pcc_llm}. Ta praca jest najbliższa językowo planowanemu badaniu, lecz nie dotyczy osobno tekstów prawniczych ani autokodera. Wyniki promptowe należy traktować jako baseline domeny ogólnej i odtworzyć na tym samym zamrożonym podziale co modele własne. Nie wolno zestawiać bezpośrednio wyniku z ich procedury z CoNLL F1 innej wersji PCC. Własny prompt powinien jednoznacznie mapować tokeny i wzmianki do formatu scorera.

Wiersz porównawczy: LLM instrukcyjny | Polish Coreference Corpus | instruction--answer alignment | — | saputa_2024_pcc_llm

## Projekt hybrydy AE + LLM

Najbardziej wykonalna hybryda jest kaskadą selektywną. Enkoder i głowica bazowa wyznaczają kandydatów oraz prawdopodobieństwa par, DAE dostarcza domenową reprezentację i błąd rekonstrukcji, a LLM rozstrzyga tylko przypadki o małym marginesie lub wysokim błędzie rekonstrukcji. Odpowiedź LLM ma postać zamkniętego JSON z identyfikatorami istniejących wzmianek; parser odrzuca inne identyfikatory i wymusza symetrię oraz przechodniość dopiero w klasteryzatorze. Porównaniu podlegają: specjalista bez AE, specjalista z AE, LLM-only i hybryda przy wspólnym zbiorze testowym.

Druga możliwość to tryb offline: LLM generuje pseudoetykiety wyłącznie dla nieetykietowanego treningu domenowego, po czym uczeń AE+scorer działa lokalnie. Redukuje to koszt inferencji, ale wprowadza ryzyko utrwalenia błędów nauczyciela. Każda pseudoetykieta musi zawierać identyfikator promptu, modelu, datę, parametry dekodowania i wynik walidacji schematu. Zbiór dev/test pozostaje całkowicie wyłączony z promptów, selekcji demonstracji i destylacji.

## Miary kosztu i kryterium odrzucenia

Oprócz MUC, B³, CEAF_e, CoNLL F1 i LEA należy rejestrować liczbę tokenów wejścia i wyjścia, liczbę wywołań, odsetek niepoprawnych odpowiedzi, medianę i p95 opóźnienia oraz koszt według zamrożonego cennika. Dla modeli lokalnych raportuje się parametry trenowane, szczytową pamięć GPU i czas dokumentu. Hybryda nie spełnia PB3, jeżeli nie redukuje tokenów względem LLM-only albo jeżeli jej utrata jakości jest statystycznie istotna. Literatura CRAC 2025 pokazuje, że podobna jakość może ukrywać ponad dziesięciokrotną różnicę kosztu, dlatego koszt jest wynikiem pierwszorzędnym, nie komentarzem pobocznym \cite{seminck_2025_glaref}.
