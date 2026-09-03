# Surowe wyniki uruchomień zredukowanych

## Zakres i interpretacja

Wszystkie poniższe liczby zostały wygenerowane przez kod/scripts/run_reduced_experiments.py i zapisane w plikach JSON. Użyto sztucznych reprezentacji i sztucznych klastrów: 24 dokumentów treningowych oraz 12 testowych. Wyniki potwierdzają działanie potoku, ale nie mierzą jakości na polszczyźnie ani w domenie prawnej i nie rozstrzygają hipotez pracy.

Środowisko zapisane przez runner: Python 3.11.9, PyTorch 2.6.0+cu124, CUDA 12.4 i NVIDIA GeForce RTX 3050 Laptop GPU. Dane train i test były identyczne dla wszystkich modeli, odpowiednio z seedami 700001 i 700002. Dla modeli neuronowych wykonano seedy 20260903, 20260917, 20261001, 20261015 i 20261029, przy CUBLAS_WORKSPACE_CONFIG=:4096:8. Oceny wygenerował oficjalny CorefUD scorer z rewizji 4fd7b0e0c661aeeff88bc60c19ef507b84d1b590, head-match, bez singletonów w metrykach klastrowych.

## Wyniki E1–E5

| ID | Wariant zredukowany | Liczba przebiegów | CoNLL F1 średnia | CoNLL F1 odch. stand. | LEA F1 średnia | LEA F1 odch. stand. |
|---|---|---:|---:|---:|---:|---:|
| E1 | head/lemma-match | 1 | 0,97080 | 0,00000 | 0,96830 | 0,00000 |
| E2 | mention-pair, regresja logistyczna | 1 | 1,00000 | 0,00000 | 1,00000 | 0,00000 |
| E3 | lekka głowica bez DAE | 5 | 0,94632 | 0,03265 | 0,94034 | 0,03638 |
| E4 | DAE + głowica par | 5 | 0,85544 | 0,02842 | 0,82396 | 0,03220 |
| E5 | macierzowy U-Net | 5 | 0,89270 | 0,05866 | 0,87164 | 0,07066 |

Wysokie wyniki klasycznych baseline’ów wynikają z konstrukcji generatora: jawne cechy leksykalne są skorelowane ze sztucznym identyfikatorem klastra. Nie wolno ich porównywać z publikacjami ani traktować jako oszacowania wyniku na CorefUD. Pełne wyniki każdego seedu, wszystkie składowe metryk, surowy tekst scorera, straty, czasy, parametry i szczyt pamięci znajdują się w wynikach E1-reduced.json–E5-reduced.json.

## Uruchomienia niewykonane

### E6 — selektywna hybryda LLM

[DO UZUPEŁNIENIA: python kod/eval.py --config kod/configs/e6-full.yaml]

Nie uruchomiono, ponieważ brakuje ukończonego, zaudytowanego zbioru prawnego i predykcji hybrydy, a w środowisku nie ma klucza do API LLM. Nie zastąpiono decyzji LLM losową symulacją.

### E7 — zero/few-shot LLM

[DO UZUPEŁNIENIA: python kod/eval.py --config kod/configs/e7-full.yaml]

Nie uruchomiono, ponieważ nie dostarczono klucza API, nie zamrożono identyfikatora modelu i cennika oraz nie pobrano pełnego testu Polish-PCC. Adapter wymaga także ponownego audytu PII przed wysłaniem danych.

### E8 — transfer na ręcznie anotowany test prawny

[DO UZUPEŁNIENIA: python kod/eval.py --config kod/configs/e8-full.yaml]

Nie uruchomiono, ponieważ planowany korpus 24 orzeczeń nie został jeszcze podwójnie zanotowany i uzgodniony. Plik kod/data/processed/legal-test.gold.conllu nie istnieje, więc nie ma legalnej jednostki ewaluacji.

## Status hipotez

Żadnej z hipotez E1–E8 nie uznano za potwierdzoną ani obaloną. E1–E5 mają status „potok zweryfikowany na danych syntetycznych”, natomiast E6–E8 mają status „nieuruchomione”. W szczególności niższy syntetyczny wynik E4 od E3 nie jest dowodem przeciwko domenowemu pretrainingowi, ponieważ w tym przebiegu nie użyto ani rzeczywistych embeddingów HerBERT, ani nieetykietowanego tekstu prawnego.
