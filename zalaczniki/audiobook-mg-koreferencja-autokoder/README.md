# Audiobook: proste objaśnienie pracy `mg-koreferencja-autokoder`

Ten katalog zawiera niezależne, przystępne objaśnienie pracy magisterskiej
opracowanej w repozytorium
[`kamugo/mg-koreferencja-autokoder`](https://github.com/kamugo/mg-koreferencja-autokoder),
według stanu z commita `f02ed6bbecfa`.

Nie jest to mechaniczne odczytanie pracy ani oficjalna wersja tekstu. Audiobook
przekłada problem, architekturę, dane i wyniki na prosty język. Oddziela również
wyniki raportowane przez autora od ograniczeń wykrytych podczas niezależnego
przeglądu technicznego.

Pliki:

- `audiobook.md` — pełny tekst lektorski;
- `syntezuj.py` — powtarzalny generator nagrań przez `edge-tts`;
- `czesci/*.mp3` — osobne rozdziały;
- `audiobook-pelny.mp3` — kompletne rozdziały połączone w ustalonej kolejności;
- `manifest.json` — głos, tempo, rozmiary i sumy SHA-256 wygenerowanych plików.

Domyślny głos to polski `pl-PL-MarekNeural`, a tempo wynosi `-5%`.

```powershell
python -m pip install edge-tts
python syntezuj.py
```

Inny głos lub tempo:

```powershell
python syntezuj.py --voice pl-PL-ZofiaNeural --rate=-8%
```

Jeżeli rozdziały zostały już poprawnie wygenerowane, można ponownie zbudować
pełny plik i manifest bez odpytywania usługi syntezy:

```powershell
python syntezuj.py --reuse-parts
```

Merytoryczne uwagi do opisywanej pracy znajdują się w
[`PRZEGLAD_PRACY_INNEGO_AGENTA.md`](../../PRZEGLAD_PRACY_INNEGO_AGENTA.md).
