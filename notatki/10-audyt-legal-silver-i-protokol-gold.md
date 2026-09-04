# Audyt `legal-silver-2000` i protokół zamrożenia testu prawnego

Data audytu: 4 września 2026 r.

Repozytorium: `kamugo/mg2`

Charakter: audyt między rundami, bez zwiększenia licznika odpowiedzi (`17/999`).

## Wynik

Lokalny `legal-silver-2000` nie jest gotowym testem. Surowy manifest ma równą
ramę 2000 publikacji ELI z Dz.U./M.P. z lat 2005–2024, ale przetworzony plik obejmuje tylko
247 dokumentów z lat 2005–2007. Adnotacje są srebrne, nie ręcznie zatwierdzone.
Nie ma końcowego manifestu przetworzenia ani potwierdzonej licencji i zasad
redystrybucji.

Najważniejszy nowy defekt to leakage już w surowym podziale. Spośród 2000
rekordów jest 1990 unikalnych hashy tekstu i dziewięć grup exact-duplicate.
Dwie grupy przecinają podziały:

- SHA-256 `86f924dab1add22d299889dace6a51939e2f22021284cc0d338fd3078c059120`:
  `MP-2007-322` (`train`) i `MP-2007-323` (`test`);
- SHA-256 `0c61370372ea6a940ecefac3aaa21d228db1484d485defabcd07abc126a960de`:
  `MP-2008-226`, `MP-2008-224` (`train`) i `MP-2008-222` (`dev`).

To jest **FAKT o zamrożonych etykietach split w raw manifeście**, nie wynik
modelu. Żaden z pięciu wymienionych rekordów nie występuje jeszcze w niepełnym
pliku processed, ale po dokończeniu konwersji utworzyłby rzeczywisty przeciek.
Near-duplicate nie został jeszcze sprawdzony.

## Zakres danych i provenance

Raw:

- 4001 plików, 9 311 878 bajtów;
- manifest: 2000 rekordów, `train/dev/test = 1600/200/200`;
- `DU/MP = 1000/1000`;
- po 100 dokumentów na każdy rok 2005–2024;
- 1032 fragmenty do 450 whitespace tokens i 968 pełnych tekstów;
- SHA-256 manifestu:
  `c9248430310a4a3ba8a1c9b3bff997aba5c8baf468f238642cbbc24c18a19973`.

Processed:

- 2 pliki, 52 845 687 bajtów;
- 247 dokumentów, `train/dev/test = 200/25/22`;
- tylko lata 2005–2007;
- 121 270 tokenów, 38 427 wzmianek, 27 560 klastrów, 0 zer;
- CoNLL-U SHA-256:
  `966187d38ee8af88983a842d6d0fa15d052c43d319ec94bbdd9399e350de04fd`;
- JSONL SHA-256:
  `a560c6515938ee27aee35bc20f1f33ecf6d9214a068d141b51759022df75fb1b`.

Manifest raw zapisuje URL oraz hash tekstu i źródła, seed `20260903`, zakres
lat, wydawców i wykluczenie starego `legal-silver-400`. Nie zapisuje jednak
pełnej komendy, SHA kodu i zależności. Pole `license_note` każe dopiero sprawdzić
aktualne zasady ponownego użycia i danych osobowych. W repozytorium nie ma
dataset-specific `LICENSE`, a `.gitignore` nie chroni obu lokalnych katalogów.
Przed wyjaśnieniem licencji nie należy commitować artefaktów zawierających pełny
tekst lub tokeny. Minimalne ryzyko do czasu przeglądu prawnego ma publikacja samych
ID, URL, hashy, skryptów i zagregowanych liczników. Stand-off adnotacje bez tekstu
można rozważyć dopiero po osobnym przeglądzie praw do adnotacji i ryzyka PII.

## PROPOZYCJA — dwa rozdzielone benchmarki

DU/MP to mieszana populacja 28 typów publikacji ELI, m.in. 265 oświadczeń
rządowych, 260 obwieszczeń, 163 rekordy typu `Orzeczenie` i 127 ustaw. Nie są to
wyłącznie akty normatywne, a etykieta `Orzeczenie` ELI nie oznacza automatycznie
orzeczenia sądu powszechnego SAOS. Jedna populacja nie może cicho zastąpić
drugiej. Jeżeli pytanie pracy dotyczy szeroko polskich tekstów prawnych, należy
raportować je jako dwa odrębne benchmarki:

1. publikacje ELI DU/MP, ze stratyfikacją i raportem `act_type`;
2. orzeczenia sądów powszechnych SAOS.

Jeżeli zakres pracy pozostaje ograniczony do orzeczeń, `legal-silver-2000` może
służyć do transferu albo analizy domenowej, ale nie zastępuje testu SAOS.

## PROPOZYCJA — pilotażowy test publikacji ELI DU/MP

Najpierw wykonać globalny group-aware exact- i near-dedup, następnie od nowa
obliczyć train/dev/test, a dopiero z nowego testu wybrać osobny pilot DU/MP.
Trzy dokumenty pilota SAOS Agenta B nie należą do tej populacji i nie są jej
wykluczeniem. Po pomiarze czasu pilot DU/MP trzeba wpisać do exposure ledger i
wyłączyć z wyniku głównego. Wstępne minimum to 32 kolejne dokumenty z
przeliczonego testu; ostateczną liczebność należy uzasadnić precyzją estymacji i
raportować z przedziałami ufności.

Warstwy: `publisher {DU,MP} × okres {2005–09, 2010–14, 2015–19, 2020–24}`,
po cztery dokumenty w każdej z ośmiu warstw. W obrębie warstw kontrolować
`act_type` i udział fragment/pełny tekst. Losowanie musi być model-agnostic,
deterministyczne i zapisać seed, kod, polecenie, listę wykluczeń oraz ewentualne
wagi. Osobny challenge set 8–10 dokumentów może nadpróbkować zaimki, zera,
długi dystans lub disagreement, ale nie wolno mieszać go z wynikiem głównym.

## PROPOZYCJA — adjudykacja bez przecieku systemowego

1. Zamrozić rzeczywiste UD CoNLL-U i jego SHA przed anotacją.
2. Pierwszy pełny pass wykonać od zera, bez widocznych predykcji: spany,
   `segments`, klaster i zera; anotator zatwierdza lub koryguje warstwę UD potrzebną
   do wyznaczenia głowy, a `head` wynika z jawnej reguły CorefUD.
3. Dopiero drugi pass pokazuje anonimowe systemy X/Y jako pomoc recall.
4. Pilotażowo co najmniej 8/32 dokumenty anotują niezależnie dwie osoby; konflikty
   przechodzą ślepą adjudykację, a raport zawiera IAA i niepewność estymacji.
5. Mapowanie X/Y na CorefSeg/CorPipe ujawnić dopiero po zamrożeniu golda.
6. Każdy dokument wymaga `full_document_review`, zamrożonych ID kandydatów i
   okien oraz osobno zamrożonego hasha kanonicznej projekcji systemowego wejścia.
7. Walidacja końcowa: `MentionKey` z pełnymi segmentami, głowy, empty nodes,
   zero strat eksportu gold i niezależny round-trip Udapi.
8. Head wyprowadzać deterministycznie z adjudykowanego drzewa UD według jawnej
   reguły CorefUD; zamrozić parser/model/wersję albo ręcznie zatwierdzić składnię.

Wynik główny: head-match bez singletonów. Exact-match bez singletonów jest
dodatkowy; oba warianty z singletonami trafiają do suplementu. Mention detection
i clustering trzeba raportować osobno. Samoporównanie golda `100,00` pozostaje
tylko smoke testem czytelności.

## Najmniejszy następny sprawdzalny krok

Nie dokańczać jeszcze kosztownej konwersji 2000 dokumentów. Najpierw:

1. potwierdzić zasady użycia i redystrybucji danych ELI/SAOS;
2. utworzyć skrypt globalnego exact/near-dedup, który działa **przed** splitem;
3. przeliczyć podział i dowieść `0` grup przecinających train/dev/test;
4. zamrozić listę ID/URL/hash oraz protokół wyboru osobnego pilota DU/MP;
5. dopiero potem przetworzyć mały pilot i zmierzyć czas pełnej anotacji.

## Polecenia audytu

Katalog roboczy dla wszystkich poleceń: `C:\Users\Kamil\mg2`. Wszystkie kody
zakończenia: `0`. Pełne wyniki zagregowane zapisano w
`wyniki/legal-gold-audit/2026-09-04/verification.json`.

```powershell
Get-FileHash -Algorithm SHA256 `
  kod/data/raw/legal-silver-2000/manifest.json, `
  kod/data/processed/legal-silver-2000/*

python -c "import json,pathlib,collections; p=pathlib.Path(r'kod/data/raw/legal-silver-2000/manifest.json'); x=json.loads(p.read_text(encoding='utf-8')); r=x['records']; g=collections.defaultdict(list); [g[z['sha256']].append((z['doc_id'],z['split'])) for z in r]; print(len(r),len(g),[(h,v) for h,v in g.items() if len({q[1] for q in v})>1])"

python -c "import json,pathlib,collections; p=pathlib.Path(r'kod/data/processed/legal-silver-2000/legal-silver-2000.jsonl'); r=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]; print(len(r),collections.Counter(x['split'] for x in r),min(x['source']['year'] for x in r),max(x['source']['year'] for x in r),sum(len(x['tokens']) for x in r),sum(len(x['mentions']) for x in r),sum(len(x['clusters']) for x in r))"

python -c "import json,pathlib,collections; r=json.loads(pathlib.Path(r'kod/data/raw/legal-silver-2000/manifest.json').read_text(encoding='utf-8'))['records']; print(collections.Counter(x['act_type'] for x in r).most_common())"
```

## Nadal niezweryfikowane

- licencja i warunki redystrybucji pełnych tekstów oraz adnotacji;
- near-duplicate leakage;
- kompletność i jakość 1753 nieprzetworzonych dokumentów;
- ręczna jakość choć jednego dokumentu;
- czas anotacji i zgodność międzyanotatorska;
- reprezentatywność zaproponowanych 32 dokumentów po deduplikacji;
- head-match CorefSeg/CorPipe/linkera na zamrożonym teście prawnym.
