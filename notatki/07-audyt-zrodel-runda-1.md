# Audyt źródeł — runda 1: nowe usprawnienia po analizie CorPipe 24–26, CorefUD, scorera i Mavericka

Data: 2026-09-04  
Repozytorium: `C:\Users\Kamil\mg2`, HEAD `9d13850cfc0471834dba5e6a57ab0cb8e939c540`  
Zakres: wyłącznie nowe ustalenia, których nie opisano w `notatki/06-corpipe-vs-corefseg-architektura.md`. Analiza statyczna i lekkie audyty CPU; bez treningu i bez użycia GPU.

## Najważniejszy wynik tej rundy

Przed przebudową modelu trzeba naprawić **kontrakt eksperymentu**. Aktualny potok w `mg2` nie mierzy dokumentowej koreferencji end-to-end: dostaje złote wzmianki, usuwa zera, dzieli wzmianki na niezależne, niepokrywające się okna po 48 elementów i zapisuje każde okno jako osobny pseudodokument. Na PCC-dev aż **56,26% par wzmianek tej samej encji leży między takimi oknami**, więc obecna ewaluacja w ogóle ich nie sprawdza. Jest to większy problem metodologiczny niż wybór 20 MB kontra 1,1 GB.

Drugi krytyczny problem to głowy wzmianek. Konwerter zachowuje surowy `descriptor`, ale tensorizer nie odczytuje z niego złotej głowy CorefUD. Zastępuje ją heurystyką „ostatni NOUN/PROPN/PRON/DET”, zgodną ze złotem tylko dla **65,59% ciągłych wzmianek powierzchniowych PCC-dev**. Tymczasem oficjalny wynik CRAC jest liczony przez head-match.

## Źródła pierwotne

- Milan Straka, [CorPipe at CRAC 2026](https://aclanthology.org/2026.codi-1.27/) i [oficjalny kod](https://github.com/ufal/crac2026-corpipe).
- Milan Straka, [CorPipe at CRAC 2025](https://aclanthology.org/2025.crac-1.11/) i [oficjalny kod](https://github.com/ufal/crac2025-corpipe).
- Milan Straka, [CorPipe at CRAC 2024](https://aclanthology.org/2024.crac-1.9/).
- Pražák i Konopík, [End-to-end Multilingual Coreference Resolution with Headword Mention Representation](https://aclanthology.org/2024.crac-1.10/).
- Martinelli, Barba i Navigli, [Maverick](https://aclanthology.org/2024.acl-long.722/) i [oficjalne repozytorium](https://github.com/SapienzaNLP/maverick-coref).
- [Oficjalny CorefUD scorer](https://github.com/ufal/corefud-scorer) w lokalnej rewizji `4fd7b0e0c661aeeff88bc60c19ef507b84d1b590`.
- [Reguły CRAC 2026](https://ufal.mff.cuni.cz/cs/node/2933) oraz lokalne dane CorefUD 1.4 o SHA-256 archiwum `51814a8e2996f459cf3f4fa491c161b4fd59991d3390b4484dac901600cd9173`.

## 1. P0 — rozdzielić trzy różne zadania i trzy wyniki

**Dowód.** CRAC 2026 rozróżnia wejścia: „coreference and zeros from scratch”, „coreference from scratch” z dostarczonymi zerami oraz wariant dopracowujący baseline. Oficjalny scorer liczy head-match, domyślnie usuwa singletony i dopasowuje zera zależnościowo. Z kolei Maverick oficjalnie udostępnia tryb `predefined_mentions`, czyli clustering-only. Aktualny `mg2/kod/src/data/tensorization.py:144–183` koduje wyłącznie złote wzmianki, `:151–155` usuwa wszystkie puste wzmianki, a `kod/scripts/evaluate_corefud_model.py:231–236` deklaruje wynik jako „gold mentions; clustering in non-overlapping windows”. Nie jest to żaden wynik end-to-end CRAC, tylko oracle-mentions clustering.

**Spodziewany wpływ.** Brak automatycznego wzrostu modelu, ale usunięcie największego błędu interpretacyjnego. Otrzymamy uczciwe odpowiedzi na dwa osobne pytania: jakość detekcji wzmianek oraz jakość klastrowania przy danych wzmiankach.

**Koszt.** Niski: zmiana raportów, nazw eksperymentów i runnera; średni, jeżeli trzeba zachować oryginalne CoNLL-U przy zapisie.

**Minimalny eksperyment.** Na tym samym PCC-dev raportować obok siebie:

1. CorPipe 26 „coref+zeros from scratch”;
2. CorPipe 26 przy wejściu ze złotymi zerami;
3. CorefSeg-AE z gold mentions, nazwany jawnie `clustering-only`;
4. Maverick `predefined_mentions` na dokładnie tych samych wzmiankach jako kontrolę interfejsu klastrowania (zero-shot tylko diagnostycznie albo po osobnym treningu na PCC).

**Ryzyko.** Publiczne modele Mavericka są trenowane na angielskich OntoNotes/LitBank/PreCo, więc ich wynik na PCC nie może być przedstawiony jako uczciwy polski SOTA. Ma sens jako kontrola algorytmu i formatu albo po treningu/adaptacji na PCC.

## 2. P0 — przywrócić dokumentowe linki przecięte przez okna 48 wzmianek

**Dowód.** `tensorize_encoded_document` tworzy niepokrywające się fragmenty `mentions[start:start+max_mentions]` (`kod/src/data/tensorization.py:236–275`). Ewaluator zapisuje każde okno jako nowy dokument (`kod/scripts/evaluate_corefud_model.py:181–192`), więc złoto także zostaje sztucznie rozcięte. Audyt istniejących artefaktów dał:

```text
train:       gold_pairs=202340, cross_window_pairs_lost=104578 (51.68%), docs_affected=1197/1244
calibration: gold_pairs=32653,  cross_window_pairs_lost=15524  (47.54%), docs_affected=211/219
dev:         gold_pairs=33884,  cross_window_pairs_lost=19062  (56.26%), docs_affected=178/183
```

Polecenie zakończyło się kodem 0 i grupowało encje z `kod/data/processed/corefud-1.4/herbert-real/{train,calibration,dev}.metadata.jsonl` według `source_doc_id`, licząc pary tej samej encji wewnątrz i między `window_id`. Manifest potwierdza `max_mentions=48`, 500 okien i 183 dokumenty dev.

CorPipe zachowuje poprzednie wzmianki mieszczące się w kontekście jako kandydatów antecedenta. Maverick proponuje alternatywnie model przyrostowy, który porównuje nową wzmiankę z reprezentacjami już utworzonych klastrów; artykuł wskazuje tę konstrukcję jako przydatną dla długich dokumentów i danych spoza domeny (sekcja 3.2).

**Spodziewany wpływ.** Bardzo wysoki dla prawdziwej koreferencji dokumentowej. Liczba 56,26% nie jest prognozą wzrostu F1, lecz pokazuje część złotych relacji całkowicie niewidoczną dla obecnego eksperymentu.

**Koszt.** Średni. Najprostsze rozwiązanie to pokrywające się okna plus pamięć antecedentów/klastrów; pełny globalny model jest droższy.

**Minimalny eksperyment.** Bez zmiany sieci: zwiększyć `max_mentions` 48→96 i użyć stride 48, a klastry skleić przez wspólne identyfikatory **tylko w oracle-mentions diagnostic**. Potem zastąpić identyfikatory przewidzianymi linkami do pamięci poprzedniego okna. Raportować recall złotych par osiągalnych przez candidate set.

**Ryzyko.** Sklejanie po złotym `entity_id` byłoby wyciekiem etykiety; wolno go użyć jedynie do wyliczenia sufitu i testu mechaniki, nigdy do wyniku systemowego.

## 3. P0 — zachować prawdziwe głowy CorefUD i oryginalną tokenizację

**Dowód.** Oficjalny scorer w trybie domyślnym uznaje wzmianki za zgodne według głów, a pełne spany wykorzystuje głównie do rozstrzygania kolizji. README scorera wprost ostrzega, że ustawienie head=`1` wymaga późniejszego oszacowania głowy z drzewa zależnościowego. CorPipe tworzy wzmianki na zachowanych węzłach CoNLL-U i uruchamia `udapi.block.corefud.movehead.MoveHead` (`kod/vendor/corpipe26/corpipe26_onestage.py:277–303`).

Aktualny konwerter `mg2` zachowuje deskryptor z polem head (`kod/src/data/konwersja.py:75–82`), lecz `_mention_head` go nie czyta: wybiera ostatni rzeczownik, nazwę własną, zaimek albo określnik (`kod/src/data/tensorization.py:56–65`). Na PCC-dev:

```text
ciągłe wzmianki powierzchniowe z odczytywalnym head: 16570
zgodność heurystyki ze złotym head: 65.59%
błędne głowy: 5701
```

Dodatkowo starszy eksport CorefSeg-AE (`C:\Users\Kamil\Desktop\mg\kod\src\eval\corefud_writer.py:181–228`) nadaje każdej wzmiance `head=1`, fabrykuje zależności `root/dep` i porównuje predykcję z ponownie wyeksportowanym złotem w przestrzeni subtokenów. Taki head-match nie jest porównywalny z oficjalnym wynikiem CorPipe na oryginalnym PCC.

**Spodziewany wpływ.** Krytyczny dla wiarygodności head-match; dodatkowo potencjalny wzrost jakości pair features, bo obecne lemma, gender, number i odległość są pobierane z często błędnego tokenu.

**Koszt.** Niski–średni. Trzeba parsować pole head z `descriptor`, zachować mapę części nieciągłych i modyfikować kopię oryginalnego CoNLL-U zamiast budować sztuczny plik.

**Minimalny eksperyment.** Na dev porównać trzy reprezentacje przy niezmienionym klastererze: (a) obecna heurystyka, (b) złota głowa z CorefUD, (c) głowa wyznaczona `MoveHead` z zachowanej składni. Osobno uruchomić `--match head` i `--match exact`; self-score oryginalnego gold przeciw jego kopii musi dać 100.

**Ryzyko.** Użycie złotej głowy w end-to-end inferencji jest oracle. Do finalnego systemu potrzebna jest głowa z parsera albo własna głowica; złoto wolno wykorzystać do treningu i diagnostyki clustering-only.

## 4. P1 — nie wybierać automatycznie „heads-only”; zrobić polską ablacją head/span

**Dowód.** Praca Pražáka i Konopíka redukuje przestrzeń kandydatów z kwadratowej do liniowej i raportuje średnio około +2,24 pkt dla heads-only względem FullSpan (`71,57` vs `69,33`). Jednak w tej samej tabeli dla Polish-PCC heads-only jest minimalnie gorsze (`74,88` vs `75,04`). Autorzy podkreślają też różnice między małymi i dużymi zbiorami. Aktualny `mg2` robi średnią wszystkich słów spanu (`tensorization.py:159–162`), CorPipe konkatenację początku i końca, a paper24 — samą głowę.

**Spodziewany wpływ.** Umiarkowany, ale eksperyment jest tani i może wyłonić reprezentację lepszą dla długich polskich nazw organów, ustaw i ról procesowych.

**Koszt.** Niski po poprawieniu mapowania głowy.

**Minimalny eksperyment.** Przy identycznych złotych wzmiankach i candidate set porównać: `mean(span)`, `head`, `start+end`, `start+end+head+attention-pool`. Trzy seedy, oficjalny head-match i exact-match.

**Ryzyko.** Head-only może sztucznie dobrze pasować do głównej metryki i jednocześnie pogorszyć pełne granice potrzebne w zastosowaniu prawnym. Dlatego exact-match pozostaje obowiązkową metryką uzupełniającą.

## 5. P1 — sprawdzić, czy DAE nie rozwiązuje zadania skrótem algebraicznym

**Dowód.** W starszym CorefSeg-AE tensor par ma kanały `[h_i, h_j, |h_i-h_j|, h_i*h_j]`. DAE maskuje lokalne bloki 16×16 z `p=0.3`, ale cel pozostaje tym samym tensorowym rozwinięciem (`C:\Users\Kamil\Desktop\mg\kod\src\models\dae.py:38–54`). Dla zamaskowanej komórki `(i,j)` pierwszą grupę kanałów `h_i` można skopiować z dowolnej niezamaskowanej komórki tego samego wiersza, `h_j` z kolumny, a pozostałe grupy obliczyć dokładnie. Przy 16 blokach w wierszu prawdopodobieństwo zamaskowania całego coarse-row wynosi `0.3^16 ≈ 4,3e-9`. Pretekst prawie na pewno nie wymaga nauczenia koreferencji ani języka prawa.

Nowy model `mg2` używa innego DAE na embeddingach wzmianek, co usuwa ten konkretny przeciek, ale nadal rekonstruuje **zamrożone** embeddingi HerBERT-a i wybiera tylko końcowy checkpoint bez walidacji (`kod/train.py:169–177`, `246–315`).

**Spodziewany wpływ.** Wysoki dla sensowności tezy o autokoderze: możemy wykazać, czy zysk pochodzi z domenowej struktury, czy z trywialnego kopiowania/redukcji wymiaru.

**Koszt.** Niski dla testu skrótu, średni dla nowego pretekstu.

**Minimalny eksperyment.** Zaimplementować bezuczeniowy rekonstruktor `row/column copy` i zmierzyć MSE na dokładnie tej samej masce. Jeśli osiąga wynik zbliżony do DAE, odrzucić block-mask. Dla nowego DAE porównać: losowy DAE, wytrenowany DAE i projekcję o tej samej liczbie parametrów; wybór na oddzielnym SAOS-dev.

**Ryzyko.** Maskowanie pełnych wierszy/kolumn może uczynić zadanie zbyt trudnym. Należy stroić udział maskowanych całych wzmianek, a nie wracać do łatwego maskowania komórek.

## 6. P1 — wyrównać cel z oficjalnym traktowaniem singletonów

**Dowód.** Oficjalny scorer domyślnie usuwa singletony, ale umożliwia osobny wynik `--keep-singletons`. Praca headword z CRAC 2024 wskazuje, że Polish-PCC ma bardzo dużo singletonów i proponuje osobną binarną głowicę mention/singleton zamiast mieszania ich z antecedent loss. Lokalny audyt UDAPI na PCC-dev 1.4 dał 18 847 wzmianek, z czego 10 255 (54,41%) należy do encji singletonowych. Starszy tokenowy cel CorefSeg-AE generuje dla nich dodatnie bloki, chociaż nie wpływają na główny wynik bez singletonów.

**Spodziewany wpływ.** Umiarkowany. Rozdzielenie sygnału może poprawić detekcję wzmianek bez zmuszania klasterera do optymalizacji niewidocznych w głównej metryce self-links.

**Koszt.** Niski: dwie maski strat i dwa raporty.

**Minimalny eksperyment.** Porównać (a) wszystkie singletony w tej samej stracie, (b) singletony wyłącznie w mention loss, (c) całkowite pominięcie singletonów. Raportować head-match bez singletonów, z singletonami oraz mention F1.

**Ryzyko.** Usunięcie singletonów z detekcji traci większość przykładów granic w PCC; dlatego wariant (b), a nie (c), jest rekomendowany.

## 7. P1 — 1024 subtokeny jako pierwszy cel kontekstu, nie 2560

**Dowód.** CorPipe 25 przeprowadza kontrolowaną ablacją: mT5-large zyskuje `+2,23` pkt średnio przy 512→1024 (`70,72→72,95`), lecz tylko `+0,31` przy 1024→2560 (`72,95→73,26`). Dla umT5-xl analogicznie `+1,85`, a potem `+0,45`. Autor podsumowuje, że największy przyrost następuje przed 1024. To doprecyzowuje samo stwierdzenie z notatki 06, że CorPipe używa 2560.

**Spodziewany wpływ.** Około kilku punktów jest możliwe, ale nie należy przenosić liczby wprost na PCC/HerBERT. Najważniejszy jest korzystny kompromis pamięć–kontekst.

**Koszt.** Średni. Pełna macierz tokenowa 1024² jest nierozsądna na RTX 3050, ale macierz wzmianek plus pamięć antecedentów jest wykonalna.

**Minimalny eksperyment.** Dla mention-level modelu porównać zasięg antecedentów odpowiadający 512 i 1024 subtokenom, bez zwiększania rozmiaru kwadratowej mapy; zmierzyć recall złotych antecedentów w candidate set oraz CoNLL F1.

**Ryzyko.** Dłuższy kontekst bez naprawy okien dokumentowych tylko zwiększy koszt. Najpierw trzeba usunąć sztuczne granice 48 wzmianek.

## 8. P1 — usunąć kwadratowe ważenie długością spanu i rozmiarem klastra

**Dowód.** Tokenowy target w starszym CorefSeg zaznacza wszystkie pary tokenów z całego klastra. W audycie dokładnie tego wejścia na PCC-dev otrzymano 660 888 dodatnich pól wobec 87 080 par na poziomie wzmianek; 1% klastrów generuje **30,90%** całej dodatniej masy. Największe pojedyncze spany singletonowe o długości 72, 69 i 67 słów tworzą odpowiednio 5184, 4761 i 4489 dodatnich pól. W aktualnym modelu mention-level problem jest mniejszy, ale nadal 1% lokalnych grup klastrowych tworzy 19,6% dodatnich par treningowych. CorPipe liczy decyzję antecedenta per bieżąca wzmianka, więc nie ma kwadratowego ważenia długością powierzchni.

**Spodziewany wpływ.** Umiarkowany do wysokiego dla stabilności i recall krótkich zaimków, szczególnie w prawie, gdzie bardzo długie nazwy aktów i organów nie powinny dominować gradientu.

**Koszt.** Niski dla ważenia, średni dla pełnego antecedent objective.

**Minimalny eksperyment.** Ważyć każdą encję odwrotnie do liczby jej dodatnich par albo losować jeden poprawny antecedent/set poprawnych antecedentów na wzmiankę. Porównać per-typ mention recall: PRON/PROPN/NOUN i kwartyle długości spanu.

**Ryzyko.** Zbyt silna normalizacja może osłabić uczenie dużych klastrów. Raportować wyniki według rozmiaru klastra.

## 9. P2 — naprawić przeciek paddingu w starszym U-Necie

**Dowód.** `TextEncoder` wypełnia embeddingi paddingu zerami, ale `CorefSegModel.proj` ma bias (`C:\Users\Kamil\Desktop\mg\kod\src\models\unet2d.py:81–89`), więc padding po projekcji przestaje być zerowy. `valid` maskuje dopiero loss, nie wejście ani warstwy U-Netu. BatchNorm liczy statystyki również na paddingu (`unet2d.py:17–27`), a konwolucje przenoszą ten sygnał do sąsiednich ważnych pól. Na PCC-dev przy L=256 aż 42,55% okien jest krótszych niż 256, a średnio 15,90% komórek macierzy jest zamaskowane.

**Spodziewany wpływ.** Raczej mały–umiarkowany, ale zmiana poprawia poprawność i stabilność względem długości dokumentu.

**Koszt.** Niski.

**Minimalny eksperyment.** Dodać jawny `valid` do forward, zerować projekcję po Linear, dołączyć maskę jako kanał i porównać BatchNorm z GroupNorm. Test inwariancji: predykcja tego samego prefiksu nie powinna zmieniać się po dodaniu wyłącznie paddingu.

**Ryzyko.** Część zachowania modelu może zależeć od „informacji o końcu” zakodowanej paddingiem; jawny kanał maski zachowuje tę informację bez zanieczyszczania cech.

## 10. P2 — zero mentions wdrażać jako oddzielną ablacją, nie blokować nimi rdzenia

**Dowód.** CorPipe 24 pokazuje polski F1 detekcji pustych węzłów 89,51. Dwuetapowa wersja, używająca osobnego encodera zer, daje około 0,9–1,1 pkt więcej od one-stage, ale jest około dwa razy większa i wolniejsza. Autorzy wskazują, że różnica predicted-vs-gold zeros w baseline to około 1,4 pkt. Head-match nie wymaga rekonstrukcji pełnego spanu zawierającego zero; pojedynczy pusty head wystarcza do głównej metryki. Reguły CRAC rozdzielają starting points właśnie po to, by tę składową mierzyć osobno.

**Spodziewany wpływ.** Realny, lecz prawdopodobnie mniejszy niż naprawa dokumentowego candidate set i ewaluacji.

**Koszt.** Średni dla one-stage, wysoki dla osobnego encodera.

**Minimalny eksperyment.** Najpierw clustering-only ze złotymi zerami kontra ten sam model bez zer; potem wejście z zerami baseline; dopiero na końcu własna głowica `NONE/deprel` do dwóch kandydatów na parent.

**Ryzyko.** Liczby CorPipe 24 dotyczą CorefUD 1.2, a PCC i konwersja zer zmieniły się w 1.4. Nie przenosić ich bezpośrednio jako oczekiwanego zysku.

## 11. P2 — dostrajanie encodera: najpierw mała kontrolowana LoRA, nie automatyczna wymiana HerBERT-a

**Dowód.** CorPipe 25 pokazuje, że przy kontekście ograniczonym do 512 XLM-R-large był najlepszy spośród porównanych encoderów, a przewaga mT5/umT5 wynikała w dużej części z obsługi dłuższego kontekstu. Paper headword pokazuje, że LoRA pozwala dostrajać duży model przy mniejszej liczbie parametrów, lecz pełne dostrajanie w ich joined-pretraining było lepsze od LoRA; dla Polish-PCC XLM-R heads osiągnął 74,88, a mT5-full 76,07. To nie uzasadnia tezy, że sama rodzina T5 rozwiązuje problem.

**Spodziewany wpływ.** Umiarkowany po naprawie celu i candidate set; może być zerowy, jeśli główny błąd nadal leży w oknach lub metryce.

**Koszt.** Średni na 4 GB VRAM przy LoRA ostatnich warstw; wysoki dla full fine-tune.

**Minimalny eksperyment.** Ta sama architektura i te same 3 seedy: frozen HerBERT kontra LoRA w ostatnich 2 i 4 blokach. Nie zmieniać równocześnie kontekstu ani dekodera.

**Ryzyko.** Adaptacja na srebrnym SAOS może nauczyć błędów CorPipe. Najpierw stroić na złotym PCC-train, a srebro dodać z niższą wagą i osobnym manifestem.

## Plan wykonawczy po tej rundzie

1. **Zamrozić kontrakt wyników.** Każdy raport ma pola `task_scope={end_to_end, gold_mentions_clustering}`, `zeros={gold, baseline, predicted, absent}`, `match={head, exact}`, `singletons={on, off}`.
2. **Naprawić warstwę danych i eksport.** Zachować oryginalne tokeny, składnię, head, puste węzły i granice dokumentów; pisać predykcję przez UDAPI/`MoveHead` do kopii wejścia.
3. **Usunąć niezależne okna 48.** Najpierw zmierzyć candidate recall, potem wprowadzić overlap + pamięć antecedentów albo przyrostową reprezentację klastrów inspirowaną Maverickiem.
4. **Utworzyć wspólny zestaw diagnostyczny.** Te same złote wzmianki PCC-dev dla obecnego pairwise, Matrix U-Net, CorPipe-linking (jeśli da się odseparować) i Maverick clustering-only.
5. **Sprawdzić DAE shortcut.** Bezuczeniowy row/column-copy jest bramką decyzyjną: jeśli dorównuje DAE, porzucić block-mask tensorów par.
6. **Dopiero potem ablacją modelu.** Reprezentacja head/span, loss antecedent vs pary, singleton mention loss, frozen vs LoRA i kontekst 512 vs 1024 — po jednej zmianie naraz, trzy seedy.
7. **Na końcu dodać legal silver.** Gold i silver rozdzielone; SAOS-dev bez dokumentów z gold/test; wagi pseudoetykiet i wyniki na ręcznie sprawdzonej próbce.

Najmniejszy następny krok to punkty 1–2: bez nich każdy dłuższy trening może dać precyzyjną liczbę dla źle zdefiniowanego zadania.

## Rejestr wykonanych audytów CPU

Wszystkie polecenia zakończyły się kodem 0.

| Audyt | Dane/wersja | Wynik |
|---|---|---|
| Głowy różne od pierwszego tokenu | CorefUD 1.4 PCC-dev, UDAPI | 14,29% wzmianek encji niesingletonowych ma head inny niż pierwszy token |
| Zgodność `_mention_head` | `pl_pcc-dev.jsonl`, ciągłe surface mentions | 65,59%, 5701 błędów / 16570 |
| Singletony | CorefUD 1.4 PCC-dev, UDAPI | 10255 / 18847 wzmianek = 54,41% |
| Straty między oknami | `herbert-real/*.metadata.jsonl`, max_mentions=48 | dev: 19062 / 33884 par = 56,26% |
| Nierównowaga tokenowego targetu | starszy reader CorefSeg, PCC-dev | top 1% klastrów = 30,90% dodatnich pól |
| Padding L=256 | HerBERT tokenizer rev. `50e33e...`, PCC-dev | 42,55% okien niepełnych; 15,90% pól masked średnio |

Hashe analizowanych plików: `corpipe26_onestage.py` `0E09E38...A637D`, `mg2/kod/src/data/tensorization.py` `348A2201...55B`, `mg2/kod/src/models/coreference.py` `45723524...978`, `mg2/kod/train.py` `DA03F8A4...BD6`.
