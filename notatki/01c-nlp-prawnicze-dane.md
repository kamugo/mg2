# NLP prawnicze i dane: modele, dostęp oraz ograniczenia prawne

Stan weryfikacji: 2026-09-03. Zastosowano regułę konserwatywną: brak jawnej licencji dla konkretnego artefaktu oznacza odrzucenie go jako źródła danych lub wag do eksperymentu. Publiczna możliwość pobrania nie została utożsamiona z prawem do trenowania modelu.

## Modele bazowe

| model | rozmiar / kontekst | licencja | dostęp | dane osobowe i anonimizacja | decyzja |
|---|---:|---|---|---|---|
| HerBERT base cased | BERT-base; słownik 50 tys.; korpus ok. 8,6 mld tokenów | CC BY 4.0 | otwarte wagi i tokenizer w Hugging Face | karta wymienia sześć korpusów ogólnych, lecz nie deklaruje pełnej anonimizacji; możliwe dane osobowe z Webu i napisów | **dopuścić wagi**, nie kopiować automatycznie korpusów źródłowych |
| PolBERT cased/uncased | 12 warstw, 768 wymiarów, 12 głów, ok. 110 mln parametrów; 512 tokenów | brak pola licencji na sprawdzonych kartach modeli | wagi w Hugging Face | karta nie daje gwarancji anonimizacji danych pretrainingowych | **odrzucić**, dopóki właściciel nie wskaże licencji wag |
| Polish RoBERTa | base ok. 100 mln i large ok. 350 mln parametrów; 512 tokenów | LGPL-3.0 w repozytorium projektu | kod i odnośniki do wag w GitHub/Hugging Face | repozytorium nie poświadcza pełnej anonimizacji korpusu pretrainingowego | **dopuścić** po zachowaniu kopii licencji i identyfikatora wersji |
| Longformer / LED | uwaga lokalna i globalna; LED base-16384 przyjmuje do 16 384 tokenów | Apache-2.0 dla sprawdzonego checkpointu LED | otwarty checkpoint Hugging Face | checkpoint jest modelem, nie zbiorem; dokumentacja nie gwarantuje usunięcia PII z danych pretrainingowych | **dopuścić LED** jako porównanie długiego kontekstu |
| Polish Longformer | warianty 1024--4096 tokenów, inicjalizacja z Polish RoBERTa v2 | repozytorium nadrzędne LGPL-3.0, ale przed użyciem trzeba zachować licencję konkretnego checkpointu | odnośniki z oficjalnego repozytorium Polish RoBERTa | brak deklaracji pełnej anonimizacji korpusu | **warunkowo dopuścić** po zamrożeniu checkpointu i licencji |

HerBERT wykorzystuje transfer z modelu wielojęzycznego i trening na sześciu polskich korpusach; karta modelu podaje łącznie około 8,6 mld tokenów oraz licencję CC BY 4.0 \cite{mroczkowski_2021_herbert,allegro_2026_herbert}. PolBERT ma odpowiedni rozmiar do pojedynczej karty GPU, ale sprawdzona karta nie zawiera pola licencji, dlatego techniczna dostępność wag nie spełnia wymagań projektu \cite{kleczek_2020_polbert}. Polish RoBERTa udostępnia modele base i large oraz kod na LGPL-3.0; repozytorium dokumentuje także polskie warianty Longformera \cite{dadas_2020_roberta}. Longformer zastępuje pełną uwagę kombinacją uwagi okienkowej i globalnej, dzięki czemu koszt rośnie liniowo z długością sekwencji, a LED przenosi ten mechanizm do architektury encoder--decoder \cite{beltagy_2020_longformer,allenai_2026_led}.

## Zbiory i źródła danych

| zbiór | rozmiar | licencja | dostęp | anonimizacja |
|---|---:|---|---|---|
| MultiLegalPile | 689 GB; 24 języki, 17 jurysdykcji | zbiór zbiorczy CC BY-NC-SA 4.0; licencje składników różnią się | Hugging Face, streaming, pliki JSONL.XZ | brak wspólnej gwarancji anonimizacji; zawiera orzeczenia, umowy, legislację i dane webowe |
| LexGLUE | 7 zadań; splity od 5 532 do 60 000 przykładów treningowych zależnie od zadania | brak jednolitej licencji danych; prawa trzeba sprawdzać dla każdego z 7 źródeł | Hugging Face i repozytorium | zależna od komponentu; benchmark nie deklaruje jednolitej anonimizacji |
| LegalBench | 162 zadania, 6 typów rozumowania | licencja zależna od zadania | repozytorium/pakiet benchmarku i suplement publikacji | zależna od zadania; nie wolno zakładać anonimizacji całego pakietu |
| CUAD | 510 umów, ponad 13 tys. etykiet, 41 typów klauzul | brak jednoznacznej licencji dla dokumentów bazowych | GitHub/Hugging Face, umowy pochodzą z SEC EDGAR | nieanonimizowany jako całość; zachowuje nazwy stron i inne dane z umów |
| SAOS / API | wielkość zmienna; publiczne orzeczenia i metadane | na sprawdzonej dokumentacji API nie znaleziono jawnej licencji zbioru | otwarte API wyszukiwania i pliki orzeczeń | publikowane orzeczenia są redagowane, lecz nie znaleziono w dokumentacji API gwarancji pełnej anonimizacji |
| ISAP / ELI API | pełny, stale aktualizowany zasób polskich dzienników urzędowych | urzędowe dokumenty i materiały wyłączone z ochrony na mocy art. 4 polskiej ustawy o prawie autorskim; API nie nadaje osobnej licencji | oficjalne REST API Sejmu; metadane, tekst i struktura aktu | akty normatywne nie są zbiorem anonimizowanym; zwykle nie opisują prywatnych stron, lecz wymagają skanu PII |
| EUR-Lex / CELLAR | zasób dynamiczny; akty UE, orzeczenia i metadane; dostęp masowy per język | dokumenty prawne zasadniczo do ponownego użycia komercyjnego i niekomercyjnego; treści redakcyjne CC BY 4.0; metadane CC0; możliwe wyjątki dokumentowe | webservice XML, data dump, REST i SPARQL CELLAR | brak jednolitej gwarancji; dane mogą obejmować orzeczenia i osoby identyfikowalne, więc potrzebna filtracja |
| JuDDGES-pl | 266 370 rekordów, 43,1 GB, 2 konfiguracje | CC BY 4.0 | Hugging Face, Parquet; DOI 10.57967/hf/8774 | orzeczenia źródłowe są redagowane, ale karta zachowuje dane funkcjonariuszy publicznych i nie daje podstaw do uznania całości za pozbawioną PII |

MultiLegalPile jest dobrym materiałem do dalszego pretrainingu wyłącznie badawczego: jego licencja zbiorcza zawiera warunek niekomercyjny, a autorzy zalecają kontrolę licencji poszczególnych źródeł \cite{niklaus_2023_multilegalpile}. LexGLUE służy do klasyfikacji i rozumienia tekstów, nie do koreferencji; obejmuje ECtHR A/B, SCOTUS, EUR-LEX, LEDGAR, UNFAIR-ToS i CaseHOLD, zatem nie może zastąpić złotego korpusu koreferencyjnego \cite{chalkidis_2022_lexglue}. LegalBench mierzy 162 zadania rozumowania prawniczego i również nie dostarcza anotacji łańcuchów koreferencyjnych \cite{guha_2023_legalbench}. CUAD jest użyteczny jako źródło terminologii umów, lecz brak jednoznacznych praw do dokumentów bazowych eliminuje go z treningu zgodnie z regułą projektu \cite{hendrycks_2021_cuad}.

Dla polskiego materiału domenowego najbardziej użyteczne są dwa rodzaje dokumentów. ISAP/ELI zapewnia oficjalny, maszynowo dostępny tekst ustaw i rozporządzeń, ale nie daje anotacji koreferencji \cite{sejm_2026_eli}; dokumenty urzędowe mają szczególny status w art. 4 ustawy o prawie autorskim \cite{sejm_1994_prawo_autorskie}. SAOS oferuje API orzeczeń, lecz brak odnalezionej licencji oznacza, że może być użyty dopiero po uzyskaniu i zarchiwizowaniu podstawy prawnej. JuDDGES-pl jest najczytelniejszą opcją do legalnego pobrania polskich orzeczeń dzięki CC BY 4.0, ale jest zasobem świeżym, srebrnie wzbogaconym i nadal wymaga automatycznego oraz ręcznego audytu danych osobowych \cite{juddges_2026_pl}. EUR-Lex dopuszcza ponowne użycie większości dokumentów prawnych, udostępnia metadane jako CC0 i treści redakcyjne jako CC BY 4.0, jednocześnie nakazując respektowanie wyjątków i praw osób trzecich \cite{eu_2026_eurlex_reuse}.

## Decyzja dla eksperymentu

1. Złote etykiety koreferencji należy pozyskać z wybranego, licencjonowanego wydania Polish-PCC/CorefUD; żaden z benchmarków prawniczych nie zastępuje takich etykiet.
2. Dodatkowy trening domenowy należy ograniczyć do jawnie licencjonowanego podzbioru JuDDGES-pl oraz aktów z ELI, z zachowaniem identyfikatorów dokumentów, dat pobrania i kopii warunków wykorzystania.
3. MultiLegalPile może służyć jedynie jako opcjonalne źródło badawcze po wybraniu konkretnych polskich komponentów i audycie ich licencji; nie należy mieszać całego 689-GB zbioru z korpusem eksperymentalnym.
4. Do enkodera bazowego wybrano HerBERT base cased. LED pozostaje baseline'em długiego kontekstu, a Polish RoBERTa wariantem rezerwowym. PolBERT zostaje wyłączony do czasu uzyskania jawnej licencji checkpointu.
5. Każdy dokument domenowy przechodzi skan wzorców PESEL, adresów, dat urodzenia, adresów e-mail i numerów telefonu. Wynik skanu nie dowodzi anonimizacji, lecz stanowi warunek wejścia do ręcznej próbki audytowej.

## Ryzyka i ograniczenia

Licencja modelu nie rozstrzyga automatycznie praw do odtworzenia jego korpusu treningowego. Status dokumentu urzędowego nie usuwa obowiązków wynikających z ochrony danych osobowych. Anonimizacja wykonana przez wydawcę orzeczenia może pozostawiać dane sędziów, pełnomocników, spółek oraz informacje umożliwiające identyfikację pośrednią. Z tego powodu w eksperymencie należy przechowywać jedynie identyfikatory i przetworzony tekst, a surowe kopie oddzielić od publicznych artefaktów reprodukcyjnych. Rozmiary zasobów dynamicznych trzeba ponownie zmierzyć w momencie zamrażania migawki danych.
