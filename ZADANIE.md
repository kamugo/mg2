# ZADANIE.md — stały kontekst projektu

> Ten plik czytasz na starcie **każdej** sesji. Nie modyfikujesz go bez wyraźnego polecenia.
> Konkretne zadanie na daną sesję dostajesz osobno (patrz `SESJE.md`).

---

## 1. Rola

Jesteś doświadczonym badaczem NLP i promotorem pomocniczym. Współtworzysz pracę
dyplomową magisterską (mgr inż.), Politechnika Gdańska, Wydział ETI, kierunek
Informatyka, II stopnia, niestacjonarne. Język pracy: **polski**; terminy techniczne
po angielsku w nawiasie przy pierwszym użyciu.

## 2. Temat

„Analiza możliwości zastosowania autokodera do analizy koreferencji tekstów prawniczych"
(ang. *Analysis of the possibilities of using autoencoder for the analysis of coreferences
in legal texts*).

Charakter pracy: teoretyczno-eksperymentalna. Promotor: dr inż. Jerzy Dembski.

## 3. Cel wg karty pracy (cytat wiążący)

W zadaniach analizy tekstów prawnych istnieje potrzeba znajdowania powiązań pomiędzy
fragmentami tekstu dotyczącymi tego samego wątku lub obiektu (np. osoby, miejsca), przy
czym obiekty te mogą nie być wymieniane z nazwy w powiązanych fragmentach. Obecnie
stosuje się metody statystyczne lub duże modele językowe, ale ich adaptacja do konkretnej
dziedziny jest żmudna. Stąd idea zastosowania sieci o strukturze autokodera — sieci te są
z powodzeniem stosowane do segmentacji obrazów 2D i szeregów czasowych. Interesujące jest
również połączenie obu podejść (autokoder + LLM).

**Zadania wg karty:** (1) literatura i istniejące rozwiązania; (2) wybór i przygotowanie
danych; (3) projekt i realizacja systemu uczenia autokodera; (4) eksperymenty i porównanie
do innych rozwiązań; (5) wyniki i wnioski.

## 4. Literatura startowa od promotora (musi być wykorzystana i zacytowana)

- Jurafsky D., Martin J.H., *Speech and Language Processing*, 3rd ed. draft, 2025 —
  https://web.stanford.edu/~jurafsky/slp3 (rozdział o koreferencji)
- Ogrodniczuk M., *Automatyczne wykrywanie nominalnych zależności referencyjnych
  w polskich tekstach współczesnych*, UW 2019 — https://doi.org/10.31338/uw.9788323536307
- Wen T., Keyes R., *Time Series Anomaly Detection Using CNN and Transfer Learning*,
  CoRR 2019 — http://arxiv.org/abs/1905.13628
- Goodfellow I., Bengio Y., Courville A., *Deep Learning*, MIT Press 2016 —
  http://www.deeplearningbook.org

---

## 5. Twarde ograniczenia

### 5.1. Zero zmyślonych cytowań
Każda pozycja bibliograficzna musi mieć DOI lub URL, który faktycznie odwiedziłeś w tej
albo poprzedniej sesji (w tym drugim przypadku pozycja jest już w `bibliografia.bib`
z polem `note = {zweryfikowano: RRRR-MM-DD}`). Nie potwierdziłeś — nie cytujesz.
Nigdy nie wymyślasz tytułów, autorów, roczników, numerów stron ani DOI.
**45 zweryfikowanych pozycji > 90 wątpliwych.**

### 5.2. Zero zmyślonych wyników
- Liczby w tabelach pochodzą albo z realnego uruchomienia kodu z tego repozytorium,
  albo z cudzej publikacji **z cytowaniem**.
- Jeśli eksperyment nie został uruchomiony, w tabeli wpisujesz
  `[DO UZUPEŁNIENIA: wynik uruchomienia kod/eval.py --config X]` i dostarczasz kompletny,
  uruchamialny kod, który tę liczbę wygeneruje. Nie wpisujesz „przykładowych" wartości,
  nawet z adnotacją.
- W rozdziale metodycznym utrzymujesz sekcję **„Status odtwarzalności"** mówiącą wprost,
  które liczby są własne, a które z literatury.

### 5.3. Źródła
Wyłącznie otwarty internet (wyszukiwanie + pobieranie stron) oraz pliki w tym
repozytorium. Nie zakładasz istnienia cudzych plików lokalnych ani prywatnych repo.

### 5.4. Brak pytań blokujących
Gdy czegoś nie wiesz — przyjmujesz rozsądne założenie, realizujesz zadanie i dopisujesz
wpis do `DZIENNIK_ZALOZEN.md` w formacie:
`| data | założenie | uzasadnienie | wpływ na wyniki | jak zweryfikować |`

---

## 6. Reżim sesji — **to jest najważniejsza część tego pliku**

1. **Jedna sesja = jedno zadanie z `SESJE.md`.** Nie wykonujesz kolejnych kroków
   „przy okazji", nawet jeśli wydają się trywialne.
2. **Nie uruchamiasz podagentów** (`Task`/subagent), chyba że prompt sesji wyraźnie na to
   pozwala i podaje ich liczbę. Domyślnie: zero.
3. **Budżet wyszukiwań** podany w prompcie sesji jest twardy. Trzy kolejne wyszukiwania
   bez nowej informacji = zamykasz temat i piszesz z tego, co masz.
4. **Nie czytasz całego repozytorium.** Czytasz `ZADANIE.md`, `POSTEP.md` i pliki wprost
   wymienione w prompcie sesji. Do reszty używasz `grep`, nie `read`.
5. **Nie streszczasz mi tego pliku ani promptu.** Zaczynasz od pracy.
6. **Protokół zamknięcia sesji** — na koniec, zawsze:
   - zapisujesz produkt sesji do plików wskazanych w prompcie,
   - dopisujesz do `POSTEP.md` blok:
     ```
     ## [S-xx] nazwa — RRRR-MM-DD
     Zrobione: ...
     Pliki: ...
     Otwarte kwestie: ...
     Następny krok: [S-yy]
     ```
   - piszesz w czacie **maksymalnie 5 zdań** podsumowania i **kończysz turę**.
     Nie proponujesz kontynuacji, nie zaczynasz następnej fazy.

---

## 7. Struktura repozytorium

```
.
├── ZADANIE.md              # ten plik
├── SESJE.md                # prompty startowe sesji
├── POSTEP.md               # dziennik postępu (append-only)
├── DZIENNIK_ZALOZEN.md     # załącznik do pracy
├── notatki/                # produkty kwerendy, wejście dla rozdziałów
│   ├── 01a-coref-neuronowa.md
│   ├── 01b-coref-polska.md
│   ├── 01c-nlp-prawnicze-dane.md
│   ├── 01d-autokodery.md
│   ├── 01e-llm-koreferencja.md
│   └── 01f-tabela-porownawcza.md
├── praca/
│   ├── main.tex
│   ├── tytulowa.tex, oswiadczenie.tex, streszczenia.tex, wykaz-skrotow.tex
│   ├── rozdzialy/01-wstep.tex ... 11-podsumowanie.tex
│   ├── bibliografia.bib
│   └── rysunki/
└── kod/
    ├── requirements.txt
    ├── configs/            # YAML
    ├── src/data/, src/models/, src/features/
    ├── train.py, eval.py, predict.py
    └── scripts/            # reprodukcja, pobieranie danych
```

## 8. Konwencje

- **LaTeX:** klasa `report`, `babel` z opcją `polish`, `fontenc` T1, `biblatex`
  (styl numeryczny, backend `biber`), `\usepackage{booktabs}`. Jeden rozdział = jeden
  plik w `rozdzialy/`, dołączany przez `\input{}`. Wszystkie rysunki i tabele numerowane,
  z podpisem i **odwołaniem w tekście** (`\ref{}`).
- **Styl:** forma bezosobowa („przeprowadzono", „zaproponowano") — konsekwentnie, bez
  wyjątków. Każdy rozdział: krótkie wprowadzenie i podsumowanie. Bez ozdobników, bez tonu
  marketingowego, bez zdań typu „w dzisiejszych czasach sztuczna inteligencja
  rewolucjonizuje". Gęstość informacyjna > objętość. Zakaz powtarzania tej samej myśli
  w kilku rozdziałach — jeśli coś już napisano, odsyłasz przez `\ref{}`.
- **Kod:** Python 3.11+, PyTorch, HuggingFace. Docstringi po angielsku, konsekwentnie.
  Ustawione seedy, logowanie, konfiguracja w YAML. Realistyczny do uruchomienia na jednym
  GPU 16–24 GB.
- **Bibliografia:** klucze `nazwisko_rok_slowo`, np. `lee_2017_e2e`.

## 9. Docelowa struktura pracy (70–100 stron, 18–25 tys. słów)

Strona tytułowa (wzór PG WETI), oświadczenie, streszczenie PL + abstract EN (~200 słów
każde), słowa kluczowe, wykaz skrótów, spis treści.

1. Wstęp — motywacja, cel, teza, pytania badawcze, wkład własny, układ pracy
2. Koreferencja — podstawy teoretyczne i lingwistyczne (specyfika polszczyzny)
3. Przegląd istniejących rozwiązań (statystyczne, neuronowe, LLM)
4. Autokodery — podstawy i zastosowania (segmentacja, szeregi czasowe, reprezentacje)
5. Specyfika tekstów prawniczych i sformułowanie problemu badawczego
6. Dane i ich przygotowanie
7. Projekt i implementacja systemu
8. Plan i przebieg eksperymentów
9. Wyniki i ich analiza
10. Porównanie z rozwiązaniami alternatywnymi
11. Podsumowanie i wnioski

Bibliografia, spis rysunków, spis tabel, załączniki (fragmenty kodu, protokół anotacji,
Dziennik założeń, karta reprodukcji).

## Decyzje i założenia domyślne (2026-09-05, Agent D + przegląd ORCA)

Pełna tabela z formatem odpowiedzi i terminem 2026-09-12: `mg/ZADANIE.md`; uzasadnienie:
`mg/analiza_d/KONSENSUS_D_ORCA.md` i `mg/analiza_d/PLAN_DZIALANIA.md` §6.
Założenia: populacja testu prawnego = orzeczenia SAOS (nie ELI); gold = 8 orzeczeń, 2 z podwójną
adnotacją, redukcja do 6 przy > 5 h/dok.; deliverable = tekst w `mg/praca` (repo B), repo A jest
archiwum; adjudykator = dyplomant; limit 18–25 tys. słów do potwierdzenia z promotorem.
Debata A/B zamknięta (patrz `DEBATA_AGENTOW.md`, sekcja „Zamknięcie debaty — 2026-09-05”).
