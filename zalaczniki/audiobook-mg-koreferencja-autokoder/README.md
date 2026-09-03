# Audiobook: proste objaśnienie pracy `mg-koreferencja-autokoder`

Ten katalog zawiera niezależne, przystępne objaśnienie pracy magisterskiej
opracowanej w repozytorium
[`kamugo/mg-koreferencja-autokoder`](https://github.com/kamugo/mg-koreferencja-autokoder),
według stanu z commita `f02ed6bbecfa`.

Nie jest to mechaniczne odczytanie pracy ani oficjalna wersja tekstu. Audiobook
przekłada problem, architekturę, dane i wyniki na prosty język. Oddziela również
wyniki raportowane przez autora od ograniczeń wykrytych podczas niezależnego
przeglądu technicznego.

## Pobieranie

[Pobierz płynniejszą wersję MP3 — głos Zofia](https://github.com/kamugo/mg2/releases/download/audiobook-corefseg-ae-natural-v2/audiobook-pelny-naturalny.mp3).

[Pobierz klasyczny audiobook MP3 z GitHub Releases](https://github.com/kamugo/mg2/releases/download/audiobook-corefseg-ae-v1/audiobook-pelny.mp3).

Wydanie GitHub jest zalecaną drogą pobierania. Link do widoku `blob` pokazuje
stronę HTML, natomiast powyższy adres zwraca bezpośrednio cały plik audio.

Pliki:

- `audiobook.md` — pełny tekst lektorski;
- `syntezuj.py` — powtarzalny generator nagrań przez `edge-tts`;
- `czesci/*.mp3` — osobne rozdziały;
- `audiobook-pelny.mp3` — kompletne rozdziały połączone w ustalonej kolejności;
- `audiobook-pelny-naturalny.mp3` — płynniejsza wersja z łagodniejszym głosem;
- `manifest.json` — głos, tempo, rozmiary i sumy SHA-256 wygenerowanych plików.

Domyślnie generator tworzy wersję naturalną głosem `pl-PL-ZofiaNeural`, z tempem
`-2%`, poprawioną wymową skrótów technicznych i wyraźniejszymi pauzami. Pierwsza
wersja głosem `pl-PL-MarekNeural` pozostaje dostępna jako wydanie klasyczne.

```powershell
python -m pip install edge-tts
python syntezuj.py
```

Inny głos lub tempo:

```powershell
python syntezuj.py --voice pl-PL-MarekNeural --rate=-5% --pitch=-1Hz
```

Jeżeli rozdziały zostały już poprawnie wygenerowane, można ponownie zbudować
pełny plik i manifest bez odpytywania usługi syntezy:

```powershell
python syntezuj.py --reuse-parts
```

Merytoryczne uwagi do opisywanej pracy znajdują się w
[`PRZEGLAD_PRACY_INNEGO_AGENTA.md`](../../PRZEGLAD_PRACY_INNEGO_AGENTA.md).
