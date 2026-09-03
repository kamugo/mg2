# Karta reprodukcji

Stan: 2026-09-03. Karta rozdziela odtwarzalne uruchomienia syntetyczne od niewykonanych eksperymentów badawczych.

## Środowisko zarejestrowanego uruchomienia

- Windows 10, Python 3.11.9.
- PyTorch 2.6.0+cu124, CUDA 12.4, NVIDIA GeForce RTX 3050 Laptop GPU.
- Oficjalny CorefUD scorer: commit `4fd7b0e0c661aeeff88bc60c19ef507b84d1b590`, licencja MIT.
- MiKTeX 25.12, pdfTeX 1.40.28, Biber 2.21.
- Seedy modeli: `20260903`, `20260917`, `20261001`, `20261015`, `20261029`.
- Seedy wspólnych danych syntetycznych: train `700001`, test `700002`.

## Instalacja

Z katalogu repozytorium:

```powershell
python -m pip install -r kod/requirements.txt
python kod/scripts/pobierz_scorer.py
```

Scorer jest już obecny w `kod/vendor/corefud-scorer`; skrypt pobierający powinien zachować wskazaną rewizję.

## Testy i próba treningu

```powershell
Set-Location kod
python -m unittest discover -s tests -v
python train.py --config configs/smoke.yaml
```

Oczekiwane minimum: 8 zaliczonych testów oraz pliki `model.pt`, `summary.json` i `train.jsonl` w katalogu wyjściowym konfiguracji. Liczba straty może zależeć od wersji bibliotek i urządzenia; nie jest wynikiem badawczym.

## Odtworzenie E1–E5

```powershell
Set-Location kod
$env:CUBLAS_WORKSPACE_CONFIG=':4096:8'
python scripts/run_reduced_experiments.py --output-root ../wyniki
python scripts/wykresy.py
```

Runner tworzy `wyniki/E1-reduced.json`–`wyniki/E5-reduced.json`, raport `wyniki/s08-reduced-summary.json`, checkpointy i pliki CoNLL-U w `wyniki/s08-runs` oraz raport wykresów `wyniki/s13-wykresy.json`. Wszystkie te wyniki muszą mieć `synthetic_data: true`.

## Kompilacja pracy

```powershell
Set-Location praca
pdflatex -interaction=nonstopmode -halt-on-error main.tex
biber main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Produktem jest `praca/main.pdf`. Log nie powinien zawierać brakujących cytowań ani odwołań.

## Dane naturalne i eksperymenty pełne

Przed E4–E8 na danych naturalnych należy:

1. zamrozić wydanie Polish-PCC/CorefUD i zachować licencję, źródło oraz sumy kontrolne;
2. ukończyć podwójną anotację 24 dokumentów zgodnie z `zalaczniki/protokol-anotacji.md`;
3. wykonać audyt PII i licencji, a następnie utworzyć dokumentowo rozłączne splity;
4. wygenerować tensory HerBERT i uruchomić konfiguracje pełne dla pięciu seedów;
5. dla E6–E7 ustawić klucz API poza repozytorium oraz zamrozić model, prompt i cennik.

Brakujące polecenia ewaluacyjne zapisano w `notatki/05-wyniki-surowe.md` i konfiguracjach `kod/configs/e6-full.yaml`, `e7-full.yaml`, `e8-full.yaml`. Nie należy interpretować braku pliku jako wyniku równego zero.

## Kontrola poprawności

- Porównać wersję scorera i seedy z `wyniki/s08-reduced-summary.json`.
- Sprawdzić, że złoto i system mają te same dokumenty oraz wzmianki.
- Nie dobierać progu ani checkpointu na teście.
- Raportować każdy seed, średnią, odchylenie oraz dokumentowy bootstrap dla danych naturalnych.
- Zachować surowy stdout scorera, konfigurację, checkpoint i informacje o urządzeniu.
- Nie porównywać liczbowo wyników syntetycznych z publikacjami lub Polish-PCC.
