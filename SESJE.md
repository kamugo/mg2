# SESJE.md — prompty startowe

Zasada: **jedna sesja = jeden blok poniżej**. Kopiujesz treść bloku „Prompt" do Claude Code,
ustawiasz model/kontekst/thinking wg nagłówka, czekasz na zakończenie, robisz `/clear`.

Kolumna **Ustawienia** to: model · okno kontekstu · thinking effort.

| Sesja | Zadanie | Ustawienia |
|---|---|---|
| S-00 | Szkielet repo i LaTeX-a | Sonnet · std · low |
| S-01 | Plan pracy, teza, pytania badawcze | Opus/Fable · std · high |
| S-02a | Kwerenda: koreferencja neuronowa | Sonnet · std · medium |
| S-02b | Kwerenda: koreferencja dla polskiego | Sonnet · std · medium |
| S-02c | Kwerenda: NLP prawnicze, dane, licencje | Sonnet · std · medium |
| S-02d | Kwerenda: autokodery | Sonnet · std · medium |
| S-02e | Kwerenda: LLM w koreferencji | Sonnet · std · medium |
| S-02f | Scalenie kwerendy + weryfikacja bibliografii | Sonnet · std · medium |
| S-03 | Sformułowanie problemu, wybór architektur | Opus/Fable · std · high |
| S-04 | Dane: pipeline, protokół anotacji, kod pobierania | Opus/Fable · std · medium |
| S-05 | Implementacja: modele i trening | Opus/Fable · std · high |
| S-06 | Implementacja: ewaluacja i baseline'y | Sonnet · std · medium |
| S-07 | Protokół eksperymentalny (przed wynikami) | Opus/Fable · std · high |
| S-08 | Uruchomienia i wypełnienie tabel | Sonnet · std · medium |
| S-09 | Rozdziały 1–2 | Sonnet · std · medium |
| S-10 | Rozdziały 3–4 | Sonnet · std · medium |
| S-11 | Rozdziały 5–6 | Sonnet · std · medium |
| S-12 | Rozdziały 7–8 | Sonnet · std · medium |
| S-13 | Rozdziały 9–10 | Opus/Fable · std · high |
| S-14 | Rozdział 11, streszczenia, załączniki | Sonnet · std · medium |
| S-15 | Złożenie całości, spójność, kompilacja | Sonnet · std · medium |

> **Okno kontekstu:** standardowe, nie 1M. 1M ma sens przy analizie wielkiego repozytorium,
> nie przy pisaniu tekstu — opóźnia kompakcję i zwiększa koszt każdego zapytania.

---

## S-00 · Szkielet repozytorium

**Prompt**

> Przeczytaj `ZADANIE.md`. Wykonaj wyłącznie S-00.
>
> Utwórz strukturę katalogów z sekcji 7 oraz pliki: `POSTEP.md` (pusty nagłówek),
> `DZIENNIK_ZALOZEN.md` (nagłówek + tabela), `praca/main.tex` z preambułą wg sekcji 8
> i `\input{}` do jedenastu pustych plików rozdziałów (każdy zawiera tylko `\chapter{...}`),
> `praca/tytulowa.tex`, `praca/oswiadczenie.tex`, `praca/bibliografia.bib` z czterema
> pozycjami startowymi z sekcji 4, `kod/requirements.txt`.
>
> Sprawdź, że `main.tex` kompiluje się na pustych rozdziałach. Nie pisz treści merytorycznej.
> Zero wyszukiwań, zero podagentów. Zamknij sesję wg protokołu z sekcji 6.

---

## S-01 · Plan pracy

**Prompt**

> Przeczytaj `ZADANIE.md` i `POSTEP.md`. Wykonaj wyłącznie S-01.
>
> Napisz `PLAN_PRACY.md`: jednozdaniowa teza pracy, 3 pytania badawcze (każde
> falsyfikowalne i możliwe do zaadresowania eksperymentem), rozwinięty spis treści do
> poziomu podrozdziałów z jednozdaniowym opisem zawartości każdego, oraz mapowanie
> „pytanie badawcze → rozdział → eksperyment, który na nie odpowiada".
>
> Maksymalnie 5 wyszukiwań, tylko na potwierdzenie, czy teza nie jest trywialnie
> obalona przez istniejącą pracę. Zero podagentów. Maks. 2 strony. Zamknij sesję.

---

## S-02a · Kwerenda: koreferencja neuronowa

**Prompt**

> Przeczytaj `ZADANIE.md` i `PLAN_PRACY.md`. Wykonaj wyłącznie S-02a.
>
> Kwerenda literaturowa: mention-pair, mention-ranking, entity-based, sieve (Stanford),
> Lee i in. e2e-coref, c2f-coref, SpanBERT, wl-coref, s2e-coref, LingMess, Maverick,
> podejścia seq2seq (Link-Append, ASP).
>
> **Budżet: maks. 14 wyszukiwań. Zero podagentów.**
>
> Produkt — dwa pliki:
> 1. `notatki/01a-coref-neuronowa.md`: dla każdego podejścia 3–6 zdań (idea, wejście/wyjście,
>    złożoność, ograniczenie) + wiersz do tabeli porównawczej w formacie
>    `metoda | dane | metryka | wynik | klucz_bib`. Wyniki wyłącznie takie, które
>    zobaczyłeś na stronie/w PDF-ie.
> 2. dopisz pozycje do `praca/bibliografia.bib`, każda z DOI/URL i polem
>    `note = {zweryfikowano: RRRR-MM-DD}`.
>
> Nie pisz LaTeX-a. Nie przechodź do S-02b. Zamknij sesję.

---

## S-02b · Kwerenda: koreferencja dla polskiego

**Prompt** — jak S-02a, z podmianą zakresu i plików:

> Zakres: Polish Coreference Corpus (PCC), prace Ogrodniczuka i zespołu IPI PAN, CorefUD
> (wersje i zawartość dla PL), narzędzia (Bartek / IKAR / COREF-PL — **sprawdź, co realnie
> istnieje i jest dziś dostępne do pobrania**, odnotuj martwe linki). Osobno: zjawiska
> specyficzne dla polszczyzny w koreferencji (zaimki zerowe, elipsa, bogata fleksja,
> swobodny szyk).
>
> **Budżet: maks. 14 wyszukiwań.** Produkt: `notatki/01b-coref-polska.md` + wpisy do `.bib`.

---

## S-02c · Kwerenda: NLP prawnicze i dane

**Prompt** — jak S-02a, z podmianą zakresu:

> Zakres: HerBERT, PolBERT, Polish RoBERTa, modele long-context (Longformer, LED),
> MultiLegalPile, LexGLUE, LegalBench, CUAD, źródła polskich tekstów prawnych (SAOS/API
> orzeczeń, ISAP, EUR-Lex, zbiory na HuggingFace).
>
> Dla **każdego** zbioru danych i modelu odnotuj: licencję, sposób dostępu, rozmiar, czy
> zawiera dane osobowe / jest zanonimizowany. To trafia wprost do pracy — brak licencji
> = pozycja odpada.
>
> **Budżet: maks. 16 wyszukiwań.** Produkt: `notatki/01c-nlp-prawnicze-dane.md`
> (w tym tabela `zbiór | rozmiar | licencja | dostęp | anonimizacja`) + wpisy do `.bib`.

---

## S-02d · Kwerenda: autokodery

**Prompt** — jak S-02a, z podmianą zakresu:

> Zakres: AE, DAE, VAE, sparse/contractive AE, U-Net, autokodery dla szeregów czasowych
> i segmentacji, uczenie reprezentacji, deep clustering (DEC/IDEC), autokodery nad grafami
> i macierzami przyległości.
>
> Nacisk na to, co **przenosi się na koreferencję**: segmentacja macierzy 2D, klastrowanie
> w przestrzeni latentnej, pretraining domenowy. Pomiń wątki bez związku z tematem pracy.
>
> **Budżet: maks. 12 wyszukiwań.** Produkt: `notatki/01d-autokodery.md` + wpisy do `.bib`.

---

## S-02e · Kwerenda: LLM w koreferencji

**Prompt** — jak S-02a, z podmianą zakresu:

> Zakres: prompting i few-shot w koreferencji, LLM jako baseline, hybrydy
> LLM + model specjalistyczny, destylacja, generowanie pseudo-etykiet.
>
> **Budżet: maks. 10 wyszukiwań.** Produkt: `notatki/01e-llm-koreferencja.md` + wpisy do `.bib`.

---

## S-02f · Scalenie i weryfikacja bibliografii

**Prompt**

> Przeczytaj `ZADANIE.md` i wszystkie pliki `notatki/01*.md`. Wykonaj wyłącznie S-02f.
>
> 1. Zbuduj `notatki/01f-tabela-porownawcza.md` — jedna tabela zbiorcza
>    `metoda | dane | metryka | wynik | rok | klucz_bib`, posortowana po zbiorze danych.
>    Zaznacz wiersze, gdzie wyniki nie są porównywalne (inny zbiór, inna wersja scorera).
> 2. Przejdź po `praca/bibliografia.bib` i sprawdź, czy każda pozycja ma pole `note`
>    z datą weryfikacji. Pozycje bez niego: zweryfikuj (maks. 10 pobrań stron) albo usuń.
> 3. Zgłoś w podsumowaniu, ilu pozycji brakuje względem docelowych ~45–60 i w jakim obszarze.
>
> Zero podagentów. Nie pisz LaTeX-a. Zamknij sesję.

---

## S-03 · Sformułowanie problemu i wybór architektury

To jest jedna z dwóch sesji, gdzie warto zapłacić za najmocniejszy model.

**Prompt**

> Przeczytaj `ZADANIE.md`, `PLAN_PRACY.md`, `notatki/01f-tabela-porownawcza.md`,
> `notatki/01d-autokodery.md`. Wykonaj wyłącznie S-03.
>
> Napisz `notatki/02-problem-i-architektura.md`:
> 1. Formalna definicja zadania: wykrywanie wzmianek + klastrowanie encji, z notacją
>    matematyczną (zbiory wzmianek, partycja, funkcja oceny).
> 2. Dlaczego teksty prawnicze są trudne — z **konkretnymi polskimi przykładami**:
>    encje nienazwane („pozwany", „powyższa nieruchomość", „przedmiotowa umowa", „tenże"),
>    terminy definiowane w dokumencie („zwany dalej Wykonawcą"), anonimizacja (X.Y.,
>    [dane usunięte]), odwołania paragrafowe, koreferencja długodystansowa, szablonowość.
> 3. Rozważ cztery warianty: (A) segmentacja macierzy L×L / M×M siecią typu U-Net,
>    (B) autokoder jako kompresor reprezentacji wzmianek + klastrowanie w przestrzeni
>    latentnej, (C) denoising/masked AE jako pretraining domenowy + lekka głowica,
>    (D) hybryda z LLM.
>    **Wybierz 2–3 i dopracuj je**, resztę odrzuć z jednoakapitowym uzasadnieniem.
>    Dla wybranych podaj: wymiary tensorów, funkcje straty, budżet parametrów, szacowane
>    zużycie pamięci na GPU 24 GB, ryzyka.
> 4. Uzasadnij wybór wprost przez cel z karty pracy (sekcja 3 `ZADANIE.md`) —
>    argumentem ma być tania adaptacja domenowa, nie sam wynik F1.
>
> Maks. 6 wyszukiwań (tylko domykanie luk). Zero podagentów. Zamknij sesję.

---

## S-04 · Dane

**Prompt**

> Przeczytaj `ZADANIE.md`, `notatki/01b-coref-polska.md`, `notatki/01c-nlp-prawnicze-dane.md`,
> `notatki/02-problem-i-architektura.md`. Wykonaj wyłącznie S-04.
>
> 1. `notatki/03-dane.md`: pipeline danych — korpus treningowy (PCC / CorefUD-PL) + korpus
>    domenowy prawniczy; podział train/dev/test; tokenizacja; obsługa dokumentów dłuższych
>    niż okno modelu (okna przesuwne, sklejanie klastrów na granicach); format CoNLL-U /
>    CorefUD; problem transferu domeny; kwestie RODO i licencji.
> 2. `zalaczniki/protokol-anotacji.md`: protokół ręcznej anotacji 20–30 orzeczeń —
>    definicje wzmianki i relacji, przypadki sporne, sposób liczenia zgodności
>    (Krippendorff α), instrukcja dla anotatora.
> 3. Kod: `kod/scripts/pobierz_dane.py` i `kod/src/data/konwersja.py` — pobieranie
>    i konwersja do wspólnego formatu. Kod ma się uruchamiać; jeśli zbiór wymaga ręcznego
>    pobrania, skrypt wypisuje instrukcję i kończy się czytelnym błędem.
> 4. Tabela statystyk korpusu w `notatki/03-dane.md` z polami `[DO UZUPEŁNIENIA: wynik
>    uruchomienia kod/scripts/statystyki.py]`, plus sam skrypt.
>
> Maks. 6 wyszukiwań. Zero podagentów. Zamknij sesję.

---

## S-05 · Implementacja: modele i trening

**Prompt**

> Przeczytaj `ZADANIE.md`, `notatki/02-problem-i-architektura.md`, `notatki/03-dane.md`.
> Wykonaj wyłącznie S-05.
>
> Zaimplementuj wybrane w S-03 architektury: `kod/src/models/`, `kod/train.py`,
> `kod/configs/*.yaml`. Wymagania: docstringi po angielsku, ustawione seedy, logowanie,
> konfiguracja w YAML, uruchamialność na jednym GPU 16–24 GB.
>
> Napisz do tego smoke test (`kod/tests/test_smoke.py`) przechodzący na 20 sztucznych
> przykładach i **uruchom go**. Zero wyszukiwań, zero podagentów. Nie pisz `eval.py`
> — to S-06. Zamknij sesję.

---

## S-06 · Implementacja: ewaluacja i baseline'y

**Prompt**

> Przeczytaj `ZADANIE.md`, `kod/src/models/`, `notatki/02-problem-i-architektura.md`.
> Wykonaj wyłącznie S-06.
>
> 1. `kod/eval.py` + `kod/src/eval/`: MUC, B³, CEAF_e, CoNLL F1, LEA, BLANC oraz osobno
>    mention detection P/R/F1. Użyj oficjalnego scorera koreferencyjnego (zintegruj,
>    nie przepisuj), a własną implementację traktuj tylko jako test spójności.
> 2. Baseline'y w `kod/src/baselines/`: (a) heurystyka regułowa / head-match,
>    (b) mention-pair + regresja logistyczna lub gradient boosting na cechach,
>    (c) adapter do gotowego modelu neuronowego dla PL, jeśli taki istnieje wg
>    `notatki/01b-coref-polska.md`, (d) LLM zero/few-shot przez API.
> 3. Bootstrap resampling i przedziały ufności w `kod/src/eval/istotnosc.py`.
>
> Uruchom `eval.py` na sztucznych danych, żeby potwierdzić, że liczy. Maks. 4 wyszukiwania.
> Zero podagentów. Zamknij sesję.

---

## S-07 · Protokół eksperymentalny

**Prompt**

> Przeczytaj `ZADANIE.md`, `notatki/02-problem-i-architektura.md`, `kod/eval.py`.
> Wykonaj wyłącznie S-07.
>
> Napisz `notatki/04-protokol-eksperymentow.md` — **przed jakimikolwiek wynikami**:
> lista eksperymentów z identyfikatorami (E1, E2, …), dla każdego: hipoteza, konfiguracja,
> metryka rozstrzygająca, kryterium sukcesu. Ablacje: bez skip-connections, bez
> pretrainingu domenowego, różne wymiary przestrzeni latentnej, różne enkodery, długość
> okna. Plan wielokrotnych seedów i testów istotności. Osobna sekcja o koszcie:
> czas uczenia, liczba parametrów, czas inferencji, zużycie pamięci.
>
> Wyjaśnij, dlaczego samo CoNLL F1 nie wystarcza. Zero wyszukiwań, zero podagentów.
> Zamknij sesję.

---

## S-08 · Uruchomienia

**Prompt**

> Przeczytaj `ZADANIE.md`, `notatki/04-protokol-eksperymentow.md`. Wykonaj wyłącznie S-08.
>
> Uruchom eksperymenty E1–En w zredukowanej skali, jaka mieści się w dostępnym sprzęcie.
> Zapisz surowe wyniki do `wyniki/*.json` i zbiorczo do `notatki/05-wyniki-surowe.md`.
>
> Dla eksperymentów, których **nie udało się** uruchomić, wpisz jawnie
> `[DO UZUPEŁNIENIA: kod/eval.py --config X]` i podaj powód (brak GPU, brak dostępu do
> zbioru, czas). Nie wpisuj żadnej liczby, której nie wygenerował kod z tego repozytorium.
>
> Uzupełnij sekcję „Status odtwarzalności" w `notatki/04-protokol-eksperymentow.md`.
> Zero wyszukiwań, zero podagentów. Zamknij sesję.

---

## S-09 … S-14 · Pisanie rozdziałów

Szablon promptu — podstawiasz numery i pliki źródłowe:

> Przeczytaj `ZADANIE.md`, `PLAN_PRACY.md` oraz **wyłącznie** te notatki: `<lista>`.
> Wykonaj wyłącznie S-xx.
>
> Napisz `praca/rozdzialy/NN-nazwa.tex` i `praca/rozdzialy/MM-nazwa.tex`.
> Materiał bierzesz z podanych notatek — **nie prowadzisz nowych wyszukiwań** (budżet: 0)
> i nie dopisujesz nowych pozycji do bibliografii. Jeśli notatki czegoś nie pokrywają,
> wstawiasz `% LUKA: <opis>` i odnotowujesz w podsumowaniu.
>
> Objętość łącznie: <X> tys. słów. Forma bezosobowa. Każdy rozdział: wprowadzenie
> i podsumowanie. Wszystkie tabele i rysunki z podpisem i `\ref{}` w tekście.
> Zakaz powtarzania treści z wcześniej napisanych rozdziałów — odsyłaj przez `\ref{}`.
>
> Skompiluj `main.tex` i napraw błędy. Zero podagentów. Zamknij sesję.

Przypisanie źródeł:

- **S-09** → rozdz. 1–2, źródła: `01a`, `01b`, `PLAN_PRACY.md` (~3,5 tys. słów)
- **S-10** → rozdz. 3–4, źródła: `01a`, `01d`, `01e`, `01f` (~5 tys. słów)
- **S-11** → rozdz. 5–6, źródła: `01c`, `02`, `03`, protokół anotacji (~4,5 tys. słów)
- **S-12** → rozdz. 7–8, źródła: `02`, `04`, kod (~4 tys. słów)
- **S-13** → rozdz. 9–10, źródła: `05-wyniki-surowe.md`, `01f`, `04` (~4 tys. słów).
  Dodatkowo: wykresy w `kod/scripts/wykresy.py` (matplotlib, **jeden wykres = jedna teza**),
  wizualizacja przestrzeni latentnej (UMAP/t-SNE), analiza błędów na konkretnych
  przykładach z tekstów prawnych. Uczciwa dyskusja: kiedy autokoder wygrywa, kiedy przegrywa
  z LLM, czy hybryda ma sens; ograniczenia i zagrożenia dla trafności wniosków.
- **S-14** → rozdz. 11, streszczenie PL + abstract EN (~200 słów każde), słowa kluczowe,
  wykaz skrótów, załączniki, `DZIENNIK_ZALOZEN.md`, karta reprodukcji

---

## S-15 · Złożenie całości

**Prompt**

> Przeczytaj `ZADANIE.md`. Wykonaj wyłącznie S-15.
>
> 1. Skompiluj całość (`biber` + dwa przebiegi), usuń wszystkie ostrzeżenia o brakujących
>    referencjach i cytowaniach.
> 2. `grep` po `praca/` za: `% LUKA`, `[DO UZUPEŁNIENIA`, `TODO`, `XXX` — zestaw listę
>    w `POSTEP.md`.
> 3. Sprawdź spójność: czy forma bezosobowa jest wszędzie, czy każda tabela i rysunek ma
>    odwołanie w tekście, czy wszystkie pozycje `.bib` są zacytowane i odwrotnie, czy skróty
>    z wykazu są rozwinięte przy pierwszym użyciu.
> 4. Policz słowa na rozdział i zestaw z docelowymi 18–25 tys.
>
> Nie przepisuj treści merytorycznej — tylko raportuj i poprawiaj usterki techniczne.
> Zero wyszukiwań, zero podagentów. Zamknij sesję.
