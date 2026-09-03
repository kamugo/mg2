# Polish Legal Coreference Silver 400

## Status i przeznaczenie

To jest **korpus srebrny, nie złoty standard**. Etykiety zostały wygenerowane
automatycznie i służą do przyspieszenia ręcznej korekty, eksperymentów z
dostrojeniem domenowym i wyboru przykładów do anotacji. Nie wolno przedstawiać
wyniku modelu mierzonego na niezweryfikowanych etykietach jako jakości na danych
rzeczywistych.

Najbezpieczniejszy plan pracy:

1. używać części `train` jako danych srebrnych;
2. ręcznie sprawdzić całe `dev` i `test`, zaczynając od łańcuchów oznaczonych
   jako `low`;
3. zamrozić poprawiony `test` przed doborem progu i hiperparametrów;
4. raportować MUC, B³, CEAF-e, ich średnią CoNLL oraz LEA oficjalnym scorerem
   CorefUD.

## Dobór dokumentów

Korpus zawiera 400 fragmentów polskich aktów urzędowych z Sejm ELI:

- lata 2017–2024, po 50 dokumentów na rok;
- po 200 dokumentów z Dziennika Ustaw (`DU`) i Monitora Polskiego (`MP`);
- po 25 dokumentów z każdej warstwy rok × wydawca;
- maksymalnie 450 słów na dokument, z domknięciem na granicy zdania, gdy jest
  dostępna;
- deterministyczny dobór rotacyjny po typach aktu;
- odfiltrowane tytuły serii zdominowanych przez listy nadań, nominacji i danych
  osób prywatnych.

Podział dokumentowy ma 320 plików `train`, 40 `dev` i 40 `test`. Ten sam akt nie
występuje w więcej niż jednej części.

## Modele anotujące

- Stanza `pl/udcoref_xlm-roberta-lora`: niezależny model MSCAW/CAW oparty na
  XLM-RoBERTa; generuje także singletony.
- CorPipe 26 `corpipe26-onestage-corefud1.4-base-260702`: wielojęzyczny model
  umT5-base trenowany m.in. na `pl_pcc`; checkpoint ma licencję
  CC BY-NC-SA 4.0.

Zgodność modeli jest sygnałem do ustalania kolejności ręcznego przeglądu, a nie
skalibrowanym prawdopodobieństwem poprawności.

## Pliki

- `legal-silver-400.conllu` — predykcje Stanza w składni CorefUD; format do
  oficjalnego scorera.
- `legal-silver-400.jsonl` — tekst, tokeny, granice znakowe, wzmianki, klastry,
  źródło i split; format do treningu.
- `review_chains.csv` — jeden wiersz na proponowany klaster, konteksty i puste
  pola decyzji recenzenta.
- `review_documents.csv` — kolejka postępu na poziomie dokumentów.
- `corpipe26/input.conllu` — identyczne tokeny bez etykiet, podane CorPipe.
- `corpipe26/corpipe26-silver.conllu` — główny komplet automatycznych etykiet.
- `corpipe26/corpipe26-silver.jsonl` — główny wariant treningowy z polami
  zgodności Stanza.
- `corpipe26/review_corpipe_chains.csv` i `review_corpipe_mentions.csv` — kolejki
  ręcznej korekty głównych etykiet.
- `corpipe26/review_sample_100.csv` — szybka próbka po 20 klastrów z każdej
  kategorii zgodności, po jednym z 100 różnych dokumentów.
- `corpipe26/splits/` — gotowe train/dev/test w JSONL i CoNLL-U.
- `corpipe26/stanza-silver.conllu` — predykcje Stanza w tej samej kolejności,
  użyte wyłącznie do analizy zgodności.
- `manifest.json` i `corpipe26/manifest.json` — wersje, parametry, statystyki i
  skróty SHA-256.

Ze względu na wynik na złotym Polish-PCC dev (CorPipe 72,97 CoNLL F1 wobec
55,10 dla DAE) do treningu zalecany jest `corpipe26/splits/train.jsonl`.
Stanza służy jako niezależny sygnał zgodności, nie jako drugi złoty standard.

W `review_chains.csv` pole `decision` powinno przyjmować `accept`, `reject` lub
`edit`. W `corrected_mentions` można zapisać poprawiony podział jako JSON, np.
`[["DOC-m0001","DOC-m0003"],["DOC-m0002"]]`. Puste pole oznacza brak
przeglądu, nie akceptację.

## Schemat JSONL

Każdy wiersz jest dokumentem. Najważniejsze pola:

- `tokens[*].token_index` — globalny, zerowy indeks tokenu;
- `mentions[*].start_token`, `end_token` — półotwarty przedział `[start, end)`;
- `mentions[*].start_char`, `end_char` — półotwarty przedział w oryginalnym
  tekście;
- `mentions[*].cluster_id` — identyfikator encji wewnątrz dokumentu;
- `mentions[*].is_zero` — wzmianka zerowa bez powierzchni tekstowej;
- `clusters[*].mention_ids` — komplet wzmianek proponowanego klastra;
- `review_priority_band` — heurystyka `high`/`medium`/`low`/`singleton`, nie
  prawdopodobieństwo modelu.

Aliasowe pola `start`, `end`, `entity_id`, `sentence_id`, `lemma`, `upos` i
`feats` zapewniają zgodność z obecnym tensorizerem autokodera. Wzmianki zerowe
są zachowane w JSONL, ale pomijane przy kodowaniu HerBERT, ponieważ nie mają
tokenu powierzchniowego.

## Pochodzenie i ograniczenia

Teksty pochodzą z oficjalnego API Sejm ELI. Dla HTML wyodrębniono treść, a dla
PDF użyto istniejącej warstwy tekstowej bez OCR. Manifest źródłowy przechowuje
URL, metadane ELI i SHA-256 pobranego źródła. Ekstrakcja PDF może pozostawić
pojedyncze błędy odstępów i musi być kontrolowana podczas przeglądu.

Akty normatywne są dokumentami urzędowymi, ale przed publiczną redystrybucją
całego pakietu należy ponownie sprawdzić aktualne warunki ELI, zasady dotyczące
danych osobowych oraz warunki checkpointów anotujących. Sam korpus zawiera
publiczne nazwiska występujące m.in. w orzeczeniach.

## Odtworzenie

```powershell
python scripts/build_legal_silver_corpus.py --stage collect --max-words 450
python scripts/build_legal_silver_corpus.py --stage annotate
python scripts/prepare_corpipe_legal_pilot.py --limit 400 `
  --output data/processed/legal-silver-400/corpipe26
python vendor/corpipe26/corpipe26_onestage.py `
  --load models/corpipe26-onestage-corefud1.4-base-260702 `
  --exp data/processed/legal-silver-400/corpipe26/run `
  --test data/processed/legal-silver-400/corpipe26/input.conllu `
  --batch_size 1 --segment 512
```

Pełne środowisko CorPipe jest opisane w
`vendor/corpipe26/requirements.txt`; lokalny kod repozytorium jest przypięty w
historii Git projektu.
