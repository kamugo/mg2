# Benchmark lokalnej inferencji

Data UTC: `2026-09-04T08:38:20.594145+00:00`
Dokumenty: **60**, tokeny slowne: **19985**.

Pomiar obejmuje uruchomienie nowego procesu, wczytanie modelu, inferencje i zapis wyniku. Nie obejmuje zewnetrznej tokenizacji surowego tekstu do CoNLL-U wymaganej przez CorPipe.

| System | Udane | Cold [s] | Warm mediana [s] | dok./s | tokeny/s | peak GPU [MiB] |
|---|---:|---:|---:|---:|---:|---:|
| corefseg-unet-long | 3 | 32.27 | 31.62 | 1.90 | 632.1 | 804 |
| corefseg-unet-long-dae | 3 | 32.06 | 33.44 | 1.80 | 597.9 | 804 |
| corpipe26-base | 3 | 100.21 | 96.80 | 0.62 | 206.5 | 1560 |

## Surowe przebiegi

| System | Powtorzenie | Stan cache | Kod | Czas [s] | dok./s | tokeny/s | log |
|---|---:|---|---:|---:|---:|---:|---|
| corpipe26-base | 1 | cold | 0 | 100.21 | 0.60 | 199.4 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corpipe26-base\repeat-1\process.log` |
| corefseg-unet-long | 1 | cold | 0 | 32.27 | 1.86 | 619.4 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corefseg-unet-long\repeat-1\process.log` |
| corefseg-unet-long-dae | 1 | cold | 0 | 32.06 | 1.87 | 623.4 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corefseg-unet-long-dae\repeat-1\process.log` |
| corefseg-unet-long | 2 | warm-os-cache | 0 | 31.30 | 1.92 | 638.6 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corefseg-unet-long\repeat-2\process.log` |
| corefseg-unet-long-dae | 2 | warm-os-cache | 0 | 32.80 | 1.83 | 609.3 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corefseg-unet-long-dae\repeat-2\process.log` |
| corpipe26-base | 2 | warm-os-cache | 0 | 97.16 | 0.62 | 205.7 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corpipe26-base\repeat-2\process.log` |
| corefseg-unet-long-dae | 3 | warm-os-cache | 0 | 34.07 | 1.76 | 586.5 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corefseg-unet-long-dae\repeat-3\process.log` |
| corpipe26-base | 3 | warm-os-cache | 0 | 96.44 | 0.62 | 207.2 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corpipe26-base\repeat-3\process.log` |
| corefseg-unet-long | 3 | warm-os-cache | 0 | 31.95 | 1.88 | 625.6 | `C:\Users\Kamil\mg2\wyniki\benchmark-inference\runs\corefseg-unet-long\repeat-3\process.log` |
