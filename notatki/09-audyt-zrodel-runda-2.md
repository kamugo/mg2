# Audyt źródeł — runda 2

**Repozytorium:** `kamugo/mg2`  
**Stan wejściowy:** `9d13850cfc0471834dba5e6a57ab0cb8e939c540`  
**Data:** 2026-09-04  
**Status:** zakończona jedna merytoryczna runda; nie uruchamiano ani nie przerywano zadań GPU  
**Zakres:** wyłącznie ustalenia nowe względem `06-corpipe-vs-corefseg-architektura.md`, `07-audyt-zrodel-runda-1.md` i `08-plan-corefseg-v2.md`.

## Wynik w skrócie

Runda 2 zmienia kolejność planu. Najpierw trzeba naprawić ścieżkę oficjalnej ewaluacji. Następnie najtańszym sensownym modelem jest kierunkowy scorer `antecedent/self` z oknem skupionym na bieżącej wzmiance i pamięcią około 100 wcześniejszych wzmianek. Dopiero później należy testować kontekst 1024 oraz reprezentację całego klastra. DAE nie uzasadnił dalszego skalowania: przy tej samej architekturze i seedzie dał gorszy wynik niż losowa inicjalizacja.

Nowe priorytety:

1. **P0:** scorer na oryginalnym goldzie, bez zmiany `newdoc id`, z główną metryką CRAC: head-match bez singletonów.
2. **P0:** 512 subtokenów, okno skupione na wzmiance, pamięć/top-k 100, jawne `self` albo uczone `epsilon`.
3. **P1:** po uruchomieniu detektora wzmianek jedna runda DAgger na mieszance dokumentów gold/pred 50/50.
4. **P1:** zachować `start/end` jako tożsamość wzmianki; głowę traktować jako cechę i adapter do oficjalnego score'a.
5. **P1:** sprawdzić CorPipe z `--depth 5`, `6` i `10`; nie kopiować wartości 5 bez testu.
6. **P2:** transformer reprezentujący klaster pozostawić jako późniejszą ablację OOD/prawo, a nie rdzeń wersji minimalnej.

## Zamrożone wersje źródeł

| Źródło | SHA użyty w audycie |
|---|---|
| CorPipe 2024 | `aaf90f0bef058054496850ec72ba29b1e41da185` |
| CorPipe 2025 | `ee8474477a4191ee7c1d26da66012574303b24b9` |
| CorPipe 2026 | `3ad2d913bd42f62f0422f0c5fdeb8002981298c8` |
| Maverick | `0dc6554cd66f5d4eecf5b3d75626ef78e835ece6` |
| WL-Coref | `4af0aa04eefad5b68a1fb6ca48a846a449bfa4b0` |
| CAW-Coref | `e815f299ffa80e55687008a1e471643809641a51` |
| DAggerCoref | `92b40bd1403d2e96608f1deec5e6ca3a67dcbb70` |

**Polecenie kontrolne (kod zakończenia 0):**

```powershell
git ls-remote https://github.com/ufal/crac2024-corpipe.git HEAD
git ls-remote https://github.com/ufal/crac2025-corpipe.git HEAD
git ls-remote https://github.com/ufal/crac2026-corpipe.git HEAD
git ls-remote https://github.com/SapienzaNLP/maverick-coref.git HEAD
git ls-remote https://github.com/vdobrovolskii/wl-coref.git HEAD
git ls-remote https://github.com/KarelDO/wl-coref.git HEAD
git ls-remote https://github.com/tgmorton/dagger-coref.git HEAD
```

## 1. Świeży benchmark mierzy szybkość, ale jeszcze nie daje uczciwego porównania jakości

**FAKT / dowód.** Benchmark ukończył się z kodem 0 na 60 pierwszych dokumentach PCC-dev (19 985 tokenów słownych). Ciepła mediana wynosi 31,62 s / 632,1 tok./s / 804 MiB dla `unet_long`, 33,44 s / 597,9 tok./s / 804 MiB dla `unet_long_dae` i 96,80 s / 206,5 tok./s / 1560 MiB dla CorPipe26-base. Na tej maszynie CorefSeg jest więc około 3,06 raza szybszy, a CorPipe zajmuje około 1,94 raza więcej pamięci GPU. Checkpointy i hashe znajdują się w `wyniki/benchmark-inference/results.json`.

**Polecenie (kod 0):**

```powershell
Get-Content wyniki/benchmark-inference/results.json -Raw
Get-Content wyniki/benchmark-inference/status.json -Raw
```

**FAKT / dowód.** Oficjalny scorer nie przyjmuje predykcji CorefSeg przeciwko oryginalnemu benchmarkowemu goldowi, ponieważ eksport zmienił `newdoc id` (`914` → `input_data_PCC-1_5-...`). To nie jest różnica modelu, lecz błąd wyrównania danych.

**Polecenie (kod 1):**

```powershell
python kod/vendor/corefud-scorer/corefud-scorer.py -m muc bcub ceafe -- `
  wyniki/benchmark-inference/data/pl_pcc-corefud-dev.conllu `
  wyniki/benchmark-inference/runs/corefseg-unet-long/repeat-1/evaluation.pred.dev.conllu
```

Wynik: `DataAlignError: Newdoc labels ... key=<914,<ROOT>>, sys=<input_data_PCC...>`.

**EKSPERYMENT.** Ten sam scorer uruchomiony na goldzie już wyeksportowanym i zsanityzowanym przez CorefSeg kończy się kodem 0, ale jest to inny gold. W głównej konfiguracji head-match bez singletonów otrzymano:

| Model | Oficjalny CoNLL na zmienionym goldzie | Wewnętrzny CoNLL z singletonami | Mention F1 wewnętrzne |
|---|---:|---:|---:|
| `unet_long` | 25,68 | 38,25 | 50,83 |
| `unet_long_dae` | 23,72 | 36,62 | 49,96 |

```powershell
python kod/vendor/corefud-scorer/corefud-scorer.py -m muc bcub ceafe -- `
  wyniki/benchmark-inference/runs/corefseg-unet-long/repeat-1/evaluation.gold.dev.conllu `
  wyniki/benchmark-inference/runs/corefseg-unet-long/repeat-1/evaluation.pred.dev.conllu
python kod/vendor/corefud-scorer/corefud-scorer.py -m muc bcub ceafe -- `
  wyniki/benchmark-inference/runs/corefseg-unet-long-dae/repeat-1/evaluation.gold.dev.conllu `
  wyniki/benchmark-inference/runs/corefseg-unet-long-dae/repeat-1/evaluation.pred.dev.conllu
```

Oba polecenia: kod 0. Scorer wypisuje też ostrzeżenia o tych samych spanach przypisanych do kilku klastrów. Eksport usunął odpowiednio 43 i 36 międzyzdaniowych predykowanych wzmianek; gold ma 54 dodatkowe członkostwa wielokrotne. Są to mierzalne straty transformacji, nie reinferencja.

**FAKT / dowód.** `unet_long` i `unet_long_dae` mają tę samą architekturę (7,80 mln trenowanych parametrów), konfigurację i `seed: 42`; wariant DAE tylko inicjalizuje te same wagi z `runs/dae_long/best.pt` (`missing=0, unexpected=0 — głowica DAE pomijana`). DAE nie ma osobnej ścieżki podczas inferencji, więc różnica 31,62 vs 33,44 s jest wariancją trzech pomiarów, nie kosztem DAE. Mimo to inicjalizacja DAE pogorszyła wynik o 1,96 punktu oficjalnego CoNLL na tym samym zmienionym goldzie i o 1,63 punktu wewnętrznego CoNLL.

**Źródła lokalne:** `C:\Users\Kamil\Desktop\mg\kod\runs\unet_long*/history.json`, `train.log`, `configs/unet_long*.yaml`; artefakty: `wyniki/benchmark-inference/runs/.../evaluation.json`.

**Wpływ.** Nie wolno jeszcze zestawiać 25,68 z pełnym wynikiem CorPipe 72,97 jako różnicy modeli: próbki i ścieżka golda są różne. Benchmark czasu jest ważny, ale porównanie jakości czeka na naprawę eksportu. Nie ma też podstaw do kolejnego długiego treningu DAE przed wykonaniem baseline'u bez uczenia opisanego w rundzie 1.

**Koszt.** Niski: około 0,5–1 dnia na eksport zachowujący identyfikatory i pełny audyt strat; ponowny scoring trwa sekundy.

**Minimalny eksperyment.** Zapisać predykcje bez zmiany komentarzy `newdoc`, tokenów, empty nodes i golda; wymagać kodu 0 score'a przeciw oryginalnemu `pl_pcc-corefud-dev.conllu`; raportować head-match bez singletonów jako wynik główny, a wyniki z singletonami i exact jako pomocnicze. Dopiero wtedy porównać oba CorefSeg i CorPipe na dokładnie tych samych dokumentach.

**Ryzyko.** Usunięcie tylko błędu `newdoc id` nie naprawi automatycznie utraty wzmianek międzyzdaniowych, nieciągłych i wieloczłonkostwa. Każdy licznik strat musi pozostać osobno dla gold i pred.

## 2. Pamięć 100 wzmianek odzyskuje większość potrzebnych ogniw — 1024 nie powinno być pierwszym ruchem

**FAKT / dowód.** Na pełnym PCC-dev 1.4 aktualny czytnik CorefSeg wytwarza 6822 kierunkowe decyzje „bieżąca wzmianka → poprzednia wzmianka tej samej encji”. Zasięg 48 wcześniejszych wzmianek pokrywa 94,49%, 50 — 94,84%, 96 — 98,30%, 100 — 98,42%, a 150 — 98,97%. Odległość słowna do poprzednika ma medianę 14, p90=89, p95=145, p99=425 i maksimum 2405. Budżet 460 poprzednich słów obejmuje 99,09% ogniw; 512 — 99,19%; 1024 — 99,69%.

**Polecenie (kod 0):**

```powershell
$code = @'
from src.data.corefud_reader import read_corefud
from bisect import bisect_right
from pathlib import Path
p=Path(r'C:\Users\Kamil\mg2\kod\data\raw\corefud-1.4\extracted\CorefUD-1.4-public\data\CorefUD_Polish-PCC\pl_pcc-corefud-dev.conllu')
docs=read_corefud(p); rank=[]; word=[]; sent=[]
for d in docs:
    ms=sorted(set(m for c in d.clusters for m in c),key=lambda m:(m.start,m.end))
    pos={m:i for i,m in enumerate(ms)}; starts=[s for s,e in d.sentence_spans]
    for c in d.clusters:
        c=sorted(set(c),key=lambda m:(m.start,m.end))
        for a,b in zip(c,c[1:]):
            rank.append(pos[b]-pos[a]); word.append(b.start-a.start)
            sent.append(bisect_right(starts,b.start)-bisect_right(starts,a.start))
print(len(docs),len(rank))
for k in (48,50,96,100,150): print(k,sum(x<=k for x in rank)/len(rank))
for k in (256,460,512,1024,2560): print(k,sum(x<=k for x in word)/len(word))
'@
$code | python -
```

Uruchomiono w `C:\Users\Kamil\Desktop\mg\kod`; kod 0.

**WNIOSEK.** Liczba 56,26% „utraconych wszystkich par” z rundy 1 jest prawdziwa dla celu symetrycznego K×K, ale zawyża problem po przejściu na kierunkowy antecedent. Do odtworzenia klastra wystarczy co najmniej jedno poprawne wcześniejsze ogniwo, a nie każda para w klastrze. Najtańszy pierwszy wariant to okno 512 skupione na bieżącej wzmiance plus pamięć/top-k 100, nie natychmiastowe podwojenie całego wejścia do 1024.

**Wpływ.** Mniej pamięci i czasu; prostsze porównanie z DAggerCoref/WL-Coref. Kontekst 1024 pozostaje legalną ablację reprezentacji, ale nie jest konieczny do samej widoczności większości poprzedników.

**Koszt.** Niski/średni: zmiana generatora przykładów i maski kandydatów, bez powiększania enkodera.

**Minimalny eksperyment.** Na złotych wzmiankach porównać tę samą głowicę przy `(fixed-512,k=50)`, `(centered-512,k=50)`, `(centered-512,k=100)` i dopiero `(centered-1024,k=100)`. Raportować recall co najmniej jednego gold antecedenta przed trenowaniem oraz oficjalny CoNLL po trenowaniu.

**Ryzyko.** To wyliczenie korzysta z obecnego przybliżonego czytnika (części wzmianek nieciągłych są upraszczane, empty nodes liczone jak tokeny). Po P0 trzeba je powtórzyć na kanonicznych obiektach Udapi. Widoczność gold antecedenta nie gwarantuje, że encoder 512 nauczy się go wybrać.

## 3. DAggerCoref dostarcza tani etap pomiędzy gold mentions a pełnym pipeline'em

**FAKT / dowód.** Oficjalny artykuł DAggerCoref raportuje kumulacyjną ablację dev: fixed-grid 512, k=50: 64,09; okna skupione na wzmiance: 66,17 (+2,08); k=100 podczas inferencji: 66,77 (+0,60, k=150 bez dalszego zysku); jedna runda DAgger: 67,87 (+1,10). Gold-mention ceiling wynosił 77,90. DAgger powstał przez uruchomienie detektora na train, zmieszanie dokumentów gold/pred 50/50 po podziale dokumentowym i trzy epoki fine-tuningu. Fałszywie dodatnie wzmianki dostają uczoną decyzję `epsilon/new entity`.

**Źródła:** [artykuł DAggerCoref](https://aclanthology.org/2026.codi-1.28.pdf), [oficjalny kod](https://github.com/tgmorton/dagger-coref/tree/92b40bd1403d2e96608f1deec5e6ca3a67dcbb70). Potwierdzone w kodzie: `configs/antecedent_dagger_r1.yaml`, `src/data/prep_antecedent_data_predicted.py`, `src/data/merge_dagger_shards.py`, `src/models/antecedent_scorer.py`, `src/inference/antecedent_inference.py`.

**Polecenie kontroli źródła (kod 0):**

```powershell
git clone --depth 1 https://github.com/tgmorton/dagger-coref.git dagger-coref
git -C dagger-coref rev-parse HEAD
rg -n "50/50|max_antecedents|learned epsilon|centered" dagger-coref
```

**Wpływ.** Plan v2 nie powinien kończyć treningu linkera na złotych wzmiankach. Po pojawieniu się pierwszego detektora trzeba dodać pojedynczy, jawnie wersjonowany etap 50/50. Warto też porównać obecne diagonalne `self` z osobnym uczonym wynikiem `epsilon`, bo `epsilon` może odrzucać fałszywie dodatnie wzmianki bez dopinania ich do cudzej encji.

**Koszt.** Średni: jeden przebieg detektora po train i krótki fine-tuning; brak nowego dużego enkodera. Na A100 autorzy podają 2 h dla trzech epok, ale czasu RTX 3050 nie należy z tego ekstrapolować bez lokalnego pilota.

**Minimalny eksperyment.** Najpierw jeden seed: gold-only vs 50/50 gold/pred przy zamrożonym podziale dokumentów i identycznym scorerze. Jeżeli delta jest dodatnia, powtórzyć trzy seedy. Osobno podać F1 detekcji wzmianek, recall gold antecedenta, CoNLL end-to-end i liczbę false-positive przypisaną do `epsilon`.

**Ryzyko.** Wyniki źródłowe dotyczą XLM-R-large i 27 zbiorów, nie polskiego HerBERT-a i PCC. Mieszanie należy wykonać dopiero po podziale na train/dev; wygenerowanie predykcji przed podziałem spowoduje leakage. Jeden etap DAgger nie odzyska false negatives detektora.

## 4. Głowa nie jest bezpieczną tożsamością wzmianki; reguła CAW pomaga tylko częściowo na PCC

**FAKT / dowód.** Kanoniczne obiekty Udapi na pełnym PCC-dev zawierają 17 019 niezerowych wzmianek. W 796 pozycjach głowy co najmniej dwie wzmianki należące do różnych encji mają tę samą głowę; dotyczy to 1660 wzmianek (9,75%). Nawet ograniczając się do encji niesingletonowych, pozostaje 68 kolizyjnych głów i 136 wzmianek. W 572/796 kolizjach przynajmniej jeden span zawiera `CCONJ`/`cc`, więc koordynacja jest dominującym, lecz nie jedynym źródłem problemu.

**EKSPERYMENT.** Na 16 854 ciągłych wzmiankach zaadaptowano dokładną ideę CAW do UPOS (`CC` → `CCONJ`, koniunkcja na głębokości <2). Zmieniła 84 głowy i zmniejszyła liczbę kolizyjnych pozycji tylko z 737 do 699 (−5,16%), a liczbę uwikłanych wzmianek z 1505 do 1426 (−5,25%). Reguła jest użyteczna jako cecha/ablacja, ale nie naprawia nieiniektywności head-only.

**Polecenie (kod 0; sedno audytu):**

```python
doc = Conllu(files=[PCC_DEV]).read_documents()[0]
# grupa: (zdanie, mention.head.ord) -> różne mention.entity.eid
# CAW: dla ciągłego spanu wybierz pierwsze CCONJ o względnej
# głębokości zależności < 2, w przeciwnym razie mention.head
```

Uruchomienie pełnego skryptu przez `$code | python -` zwróciło:

```text
all_mentions 17019; collision_heads 796; involved_mentions 1660
nonsingleton collision_heads 68; involved_mentions 136
continuous_mentions 16854; heads_changed 84
gold collision_heads/involved 737/1505
CAW  collision_heads/involved 699/1426
```

**Źródła:** [CAW-Coref paper](https://aclanthology.org/2023.crac-main.2.pdf), [CAW-Coref kod `convert_to_heads.py`](https://github.com/KarelDO/wl-coref/blob/e815f299ffa80e55687008a1e471643809641a51/convert_to_heads.py), [WL-Coref](https://github.com/vdobrovolskii/wl-coref/tree/4af0aa04eefad5b68a1fb6ca48a846a449bfa4b0). CAW raportuje wzrost 80,7 → 81,6 na angielskim OntoNotes, ale sam artykuł zaznacza, że nie da się przypisać unikalnej głowy każdemu spanowi, np. przy sekwencyjnych koordynacjach.

**Wpływ.** Nie należy zastępować w planie `start/end` jedną głową tylko dlatego, że WL-Coref używa modelu word-level, a CRAC ocenia head-match. Span jest tożsamością wewnętrzną; głowa może być dodatkową cechą, celem pomocniczym i sposobem dopasowania w scorerze.

**Koszt.** Niski dla cechy `is_coord`/alternatywnej głowy; wysoki koszt migracji i strata informacji dla pełnego head-only.

**Minimalny eksperyment.** Na tych samych złotych wzmiankach porównać `(start,end)`, `(gold head)`, `(start,end,gold head)` i `(start,end,CAW head)`. Raportować collision rate przed uczeniem oraz official head/exact CoNLL po uczeniu.

**Ryzyko.** Adaptacja CAW używa UPOS zamiast tagsetu OntoNotes; to kontrolowany eksperyment, nie wierna reprodukcja angielskiego modelu. Oficjalny head-match może premiować poprawną głowę mimo gorszych granic, dlatego exact-match musi pozostać metryką diagnostyczną.

## 5. CorPipe 2024→2025 zmienił semantykę `depth`; w 2025/2026 domyślne 5 daje stany 0–4

**FAKT / dowód.** CorPipe24 buduje automat przez `allowed_tag_transitions(tags, args.depth + 1)` i replikuje logits `args.depth + 1` razy. Po przepisaniu na PyTorch CorPipe25, a następnie CorPipe26, oba miejsca używają tylko `args.depth`. We wszystkich trzech wersjach domyślna wartość CLI pozostała równa 5. Ponieważ prefiksy stanów są tworzone przez `range(depth)`, checkpoint CorPipe26 z `depth: 5` ma stany 0,1,2,3,4, czyli może przenosić między tokenami najwyżej cztery otwarte wzmianki. Treningowy cross-entropy tagów nie korzysta z automatu; ograniczenie działa podczas Viterbi w inferencji.

**Źródła kodu:**

- [CorPipe24 `corpipe24.py`](https://github.com/ufal/crac2024-corpipe/blob/aaf90f0bef058054496850ec72ba29b1e41da185/corpipe24.py), linie 200–210, 318, 460;
- [CorPipe25 `corpipe25.py`](https://github.com/ufal/crac2025-corpipe/blob/ee8474477a4191ee7c1d26da66012574303b24b9/corpipe25.py), linie 189–200, 350, 432;
- [CorPipe26 `corpipe26_onestage.py`](https://github.com/ufal/crac2026-corpipe/blob/3ad2d913bd42f62f0422f0c5fdeb8002981298c8/corpipe26_onestage.py), linie 186–199, 368, 479.

```powershell
rg -n "allowed_tag_transitions|logits.*tile|depth" corpipe24.py
rg -n "allowed_tag_transitions|logits.*tile|depth" corpipe25.py
rg -n "allowed_tag_transitions|logits.*tile|depth" corpipe26_onestage.py
```

Każde polecenie: kod 0.

**EKSPERYMENT.** Po zastosowaniu dokładnej normalizacji ciągłego spanu i deduplikacji z CorPipe26 pełny PCC-dev ma 16 982 powierzchniowe wzmianki; maksymalna liczba aktywnych wzmianek pomiędzy tokenami wynosi 9 (maksymalny overlap na tokenie 10). Minimalna liczba przedziałów, które trzeba odrzucić, aby zmieścić gold w limicie 4, to 170/16 982 (1,00%) w 103 zdaniach. Dla limitu 5 jest to 62 (0,37%) w 42 zdaniach; dla 8 — 3; dla 9 — 0. Parametr CorPipe jest o jeden większy od tej pojemności: `--depth 5` daje limit 4, a `--depth 10` limit 9.

**Polecenie (kod 0):** skrypt Udapi odtwarza linie 86–105 `corpipe26_onestage.py`, a następnie dla każdego zdania liczy `sum(start <= i < end)` i optymalnie usuwa najpóźniej kończący się przedział przy przekroczeniu pojemności. Wynik:

```text
surface_mentions 16982; duplicate_surface_dropped 37
max_token_overlap 10; max_gap_depth 9
cap 4: min_drops 170 (1.0011%), sentences_over 103
cap 5: min_drops 62  (0.3651%), sentences_over 42
cap 8: min_drops 3   (0.0177%), sentences_over 3
cap 9: min_drops 0
```

**WNIOSEK.** Nie jest jeszcze dowiedzione, że to regresja wynikowa, ale jest to sprawdzalna różnica implementacyjna i ukryty limit reprezentacji. Warto testować samą inferencję z większym `--depth`, ponieważ parametr zmienia automat, a nie wagi modelu.

**Wpływ.** Bardzo tani potencjalny wzrost recall zagnieżdżonych wzmianek, szczególnie ważnych w długich nazwach instytucji i koordynacjach prawniczych. Dla własnego stack-taggera głębokość należy wyznaczyć z train i logować overflow na dev/legal.

**Koszt.** Niski: trzy przebiegi inferencji i score; liczba stanów DP rośnie liniowo. Nie wymaga treningu.

**Minimalny eksperyment.** Ten sam checkpoint CorPipe26, ten sam niezmieniony PCC-dev, `--depth 5`, `--depth 6`, `--depth 10`; porównać oficjalny head CoNLL, mention recall, recall wyłącznie w zdaniach o gold depth>4 oraz czas. Wagi i wszystkie inne opcje muszą mieć te same hashe.

**Ryzyko.** Większa przestrzeń może dopuścić więcej fałszywych PUSH/POP i pogorszyć precision. Wyliczone `min_drops` jest dolną granicą reprezentacyjną, nie prognozą wzrostu F1. Warto też zgłosić różnicę upstream zamiast nazywać ją błędem bez odpowiedzi autorów.

## 6. Maverick: pełna pamięć klastra nie jest dobrym pierwszym wdrożeniem na 4 GB

**FAKT / dowód.** Maverick-MES używa sześciu wyspecjalizowanych kategorii par (`pron-pron-comp`, `pron-pron-no-comp`, `pron-ent`, exact lexical match, containment, other) oraz siódmego ogólnego scorera. Kod tworzy osobne interakcje start/end i maski kategorii na podstawie tokenów, list zaimków i stopwords (`maverick/common/util.py`, `maverick/common/constants.py`, `maverick/models/model_mes.py`). Maverick incremental przekazuje bieżącą wzmiankę i wzmianki klastra do jednowarstwowego transformera, ale podczas treningu przycina klaster do 30 wzmianek: pierwsza, ostatnia i losowe 28 (`model_incr.py:244–267`). Wszystkie warianty są trenowane teacher forcing: gold starts, gold mentions, a incremental także gold clusters.

**Źródła:** [Maverick paper](https://aclanthology.org/2024.acl-long.722.pdf), [kod Maverick](https://github.com/SapienzaNLP/maverick-coref/tree/0dc6554cd66f5d4eecf5b3d75626ef78e835ece6).

```powershell
rg -n "teacher forcing|Maverickincr|Maverickmes" maverick-paper.txt
rg -n "max_length.*30|random.sample|CATEGORIES|num_cats" maverick -g '*.py'
```

Kod 0. Artykuł pokazuje, że MES jest nieco lepszy i znacznie szybszy in-domain: dla DeBERTa-base MES 81,4 CoNLL i 6 s inferencji, incremental 81,0 i 22 s; dla large MES 83,6 i 14 s, incremental 83,5 i 29 s. Incremental ma przewagę dopiero w części ustawień długich/OOD, np. LitBank 78,3 vs MES 78,0 oraz LitBank bez singletonów z gold mentions 84,0 vs 82,8. Transformer klastra poprawia własny starszy wariant reprezentacji o 3,9 punktu, lecz nie bije MES in-domain.

**WNIOSEK.** „Cluster memory” z planu v2 nie jest obowiązkowym P1. Najpierw należy dowieść kierunkowy pair scorer z top-k 100. Reprezentację klastra warto dodać dopiero jako ukierunkowaną hipotezę transferu PCC→prawo. Jeżeli powstanie, losowe 28 z Mavericka trzeba zastąpić deterministycznym wyborem (np. pierwsza + ostatnie + najwyższa pewność), aby manifest i wynik były odtwarzalne, a trening rozszerzyć o predicted clusters/DAgger.

**Wpływ.** Istotne uproszczenie pierwszego modelu i mniejsze ryzyko teacher-forcing gap. Tanie kategorie MES sugerują wcześniejszą ablację cech: typ wzmianki, lemma match, containment, odległość i zgodność morfologiczna — bez kopiowania angielskich list zaimków i stopwords.

**Koszt.** Pair categories: niski/średni. Transformer klastra: wysoki czasowo i implementacyjnie; w źródle był 2–3,7 raza wolniejszy od MES.

**Minimalny eksperyment.** Po stabilnym baseline antecedent/self dodać wyłącznie polskie, automatyczne cechy `upos/lemma/Case/Gender/Number`, exact/containment i bucket odległości. Dopiero jeśli legal-dev nadal cierpi na fragmentację długich encji, porównać deterministic cluster transformer z tą samą liczbą kandydatów i identycznym encoderem.

**Ryzyko.** Maverick jest angielski i używa innego schematu anotacji. Liczb z OntoNotes nie wolno przenosić jako oczekiwanej delty PCC. Losowe próbkowanie klastra bez jawnego seedowania jest dodatkowym źródłem wariancji.

## 7. CorefUD 1.4 / CRAC 2026 precyzuje właściwy protokół końcowy

**FAKT / dowód.** Oficjalny CRAC 2026 korzysta z CorefUD 1.4. Główną metryką jest head-match CoNLL bez singletonów; partial, exact i head z singletonami są metrykami dodatkowymi. Oficjalne mini-dev/test dla większości korpusów ograniczono do 25 tys. słów przez losowanie dokumentów. Wejście symulujące realne użycie ma usunięte koreferencje i empty nodes, a gold morfoskładnię zastąpioną wynikiem UDPipe 2. Lokalny benchmark wybrał pierwsze 60 dokumentów pełnego PCC-dev, więc nie jest oficjalnym mini-dev i nie odtwarza realistic-input.

**Źródło:** [oficjalna strona CRAC 2026](https://ufal.mff.cuni.cz/node/2933), sekcje 2.2, 3.3, 3.7 i tabela wyników; [CorefUD releases](https://ufal.mff.cuni.cz/corefud).

**Polecenie kontroli lokalnej (kod 0):**

```powershell
Get-Content wyniki/benchmark-inference/results.json -Raw
Get-FileHash kod/data/raw/corefud-1.4/extracted/CorefUD-1.4-public/data/CorefUD_Polish-PCC/pl_pcc-corefud-dev.conllu -Algorithm SHA256
```

Lokalny source hash: `e426f7d4fdd61ff633b04c685376e0153c3c3c092ab7a2a9cee0141ed1d0b1be`; wycinek 60 dokumentów: `c76ba3de6505e73043c3a2cc752dd5f3cdc63f5e5818521ca16d51bc7833d804`.

**Wpływ.** Trzeba utrzymywać dwa jawne tory: (A) pełny oryginalny PCC-dev do pracy magisterskiej i analiz polskich oraz (B) oficjalny CRAC 2026 mini-dev/input do porównywalności międzynarodowej. Nie wolno mieszać ich wyników ani nazywać pierwszych 60 dokumentów oficjalnym minidevem.

**Koszt.** Niski: pobranie oficjalnego pakietu, manifest dokumentów i dwa targety ewaluacji.

**Minimalny eksperyment.** Dla obu torów zapisać hash wejścia, listę `newdoc id`, liczbę tokenów/wzmianek/empty nodes oraz polecenie score. Warunkiem akceptacji jest kod 0 score'a na oryginalnym goldzie bez sanityzacji.

**Ryzyko.** Oficjalny realistic-input zawiera predykowaną morfoskładnię, więc cechy oparte na gold UD mogą zawyżać wynik. Licencje poszczególnych zbiorów CorefUD trzeba sprawdzić przed redystrybucją modelu/danych poza zastosowaniem naukowym.

## Falsyfikacje i decyzje tej rundy

| Element planu v2 | Wynik rundy 2 | Decyzja |
|---|---|---|
| `context=1024` jako pierwszy wzrost | 512/460 słów widzi 99,09–99,19% kolejnych gold links, a k=100 widzi 98,42% po randze | najpierw centered-512 + k=100; 1024 jako ablation |
| cluster transformer jako P1 | Maverick pokazuje podobny/gorszy wynik in-domain przy 2–3,7× wolniejszej inferencji i teacher forcing | przesunąć do P2 OOD/legal |
| dalsze skalowanie DAE | DAE init pogarsza oba dostępne CoNLL przy tej samej architekturze/seedzie | zatrzymać do baseline'u no-learning i poprawnego score'a |
| head-only jako uproszczenie | 9,75% wzmianek PCC uczestniczy w kolizji głowy; CAW redukuje kolizje tylko o ok. 5% | zachować span ID, head tylko jako cecha/adapter |
| kopiowanie `depth=5` z CorPipe | 2025/26 ma stany 0–4, inaczej niż 2024; gold PCC wymaga miejscami 9 | wykonać beztreningową ablację 5/6/10 |
| gold-only linker wystarczy przed E2E | DAgger daje +1,10 po jednej rundzie na przewidywanych wzmiankach | dodać 50/50 gold/pred po pierwszym detektorze |

## Najmniejszy następny sprawdzalny krok

Naprawić wyłącznie eksport 60-dokumentowego benchmarku tak, aby oficjalny `corefud-scorer` zakończył się kodem 0 przeciwko **oryginalnemu** plikowi gold i nie zmienił żadnego `newdoc id`, tokenu ani empty node. Zapisać liczniki strat gold/pred i cztery wyniki: head bez singletonów (główny), partial bez singletonów, exact bez singletonów, head z singletonami. Bez tego kolejny trening nie rozstrzyga, czy poprawiono model, czy tylko transformację danych.

Następny niezależny test, niewymagający treningu: CorPipe26 na tym samym wejściu z `--depth 5`, `6`, `10` i z tym samym SHA checkpointu.
