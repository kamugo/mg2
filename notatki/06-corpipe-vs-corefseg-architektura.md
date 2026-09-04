# CorPipe 26 a CorefSeg-AE: skąd bierze się różnica jakości

Data analizy: 2026-09-04  
Zakres: architektura, reprezentacja, detekcja wzmianek, funkcja celu, kontekst i dekodowanie — bez przypisywania całej przewagi rozmiarowi modelu albo treningowi wielojęzycznemu.

## Wniosek główny

CorPipe i CorefSeg-AE nie są dwiema wersjami tego samego pomysłu. CorPipe rozkłada zadanie na trzy bezpośrednio nadzorowane części:

1. wykrycie granic wzmianek;
2. utworzenie reprezentacji każdej wzmianki;
3. wskazanie poprzednika albo decyzję „to początek nowej encji”.

CorefSeg-AE uczy jedną binarną macierz token–token, która ma równocześnie kodować granice wzmianek i przynależność do klastrów. Granice są następnie odtwarzane heurystycznie z przekątnej. To jest najważniejsza różnica konstrukcyjna. Nawet idealnie przewidziane komórki macierzy nie zachowują wszystkich informacji potrzebnych do jednoznacznego odzyskania zagnieżdżonych, nakładających się i sąsiadujących wzmianek.

Rozmiar nadal pomaga, ale oficjalna ablacja CorPipe pokazuje, że nie tłumaczy całej różnicy. Średni CoNLL F1 pojedynczego modelu wzrasta od 69,19 dla `umT5-base` do 75,95 dla `umT5-xxl`, czyli o 6,76 punktu. Dla polskiego PCC wartości wynoszą odpowiednio około 75,0 i 81,4. Jest to wyraźny efekt, ale znacznie mniejszy od około 35–40 punktów oddzielających dotychczasowy CorefSeg-AE od lokalnego CorPipe base. Źródło: [Straka 2026, tabela 5](https://aclanthology.org/2026.codi-1.27.pdf), s. 210.

## Stan analizowanych źródeł

- Oficjalny kod CorPipe 26: `kod/vendor/corpipe26/corpipe26_onestage.py`, rewizja repozytorium `3ad2d913bd42f62f0422f0c5fdeb8002981298c8`, SHA-256 pliku `0E09E38B4951A95960343C9D5213663400A869DB3BA8F55DF3E7DEF289FA637D`.
- Karta lokalnego checkpointu: `kod/models/corpipe26-onestage-corefud1.4-base-260702/README.md` oraz `options.json`.
- Oficjalny artykuł: Milan Straka, [CorPipe at CRAC 2026: Empty Nodes and Cross-Lingual Transfer in Multilingual Coreference Resolution](https://aclanthology.org/2026.codi-1.27/), CODI-CRAC 2026.
- CorefSeg-AE: aktywny kod w `C:\Users\Kamil\Desktop\mg\kod`, HEAD `841177b95701292ce83d3562fcbdc68d8d2efaff`. `train.py` oraz konfiguracje długich przebiegów miały lokalne, niezatwierdzone zmiany; dlatego niżej podano także dokładne linie i hashe najważniejszych plików.

Analiza była statyczna. Nie uruchamiano inferencji ani obliczeń na GPU.

## Porównanie konstrukcji

| Obszar | CorPipe 26 one-stage | CorefSeg-AE | Konsekwencja |
|---|---|---|---|
| Reprezentacja wyjścia | Osobne tagi granic oraz wybór poprzednika | Jedna binarna macierz token–token | CorPipe zachowuje pojęcie wzmianki; macierz CorefSeg miesza dwa zadania |
| Detekcja wzmianek | Operacje stosowe `PUSH`/`POP:n`, dekodowane strukturalnie | Maksymalne ciągłe odcinki dodatniej przekątnej | CorefSeg nie może wiernie rozdzielić części sąsiadujących ani zagnieżdżonych |
| Linking | Jedna decyzja antecedenta na wzmiankę, z opcją `self` | Niezależne prawdopodobieństwa komórek i składowe spójne | CorPipe zawsze tworzy poprawną drzewiastą historię klastra; CorefSeg może scalać tranzytywnie przez pojedyncze błędy |
| Encoder | Dostrajany end-to-end razem z głowicami | HerBERT zamrożony i cache'owany | CorPipe może nauczyć encoder sygnałów granic i koreferencji |
| Kontekst | Zdanie docelowe + możliwie długi lewy kontekst + do 50 tokenów prawego; publikowana inferencja 2560 | Nakładające się okna 256, stride 128 | CorPipe widzi znacznie dalszych poprzedników i nie wymaga heurystycznego sklejania krótkich okien |
| Cel uczenia | Trzy straty CE bezpośrednio odpowiadające podzadaniom | BCE + Dice na gęstej macierzy | CorPipe nie jest zdominowany przez ogromną liczbę pustych par tokenów |
| Zera/elipsy | Do dwóch jawnych kandydatów pustej wzmianki na każdy token | Złoty pusty węzeł czytany jako zwykły token `_`; brak modułu tworzącego go z tekstu | CorefSeg nie realizuje porównywalnego zadania end-to-end dla polskiego pro-drop |
| Dobór modelu | Scoring dev po każdej epoce, wiele seedów w badaniu | Najniższy walidacyjny surrogate loss macierzy | W CorPipe selekcja jest bliższa końcowej metryce CorefUD |

## 1. CorPipe jawnie modeluje granice wzmianek

### Reprezentacja stosowa zamiast przekątnej

W danych CorPipe każda wzmianka jest zamieniana na sekwencję operacji `PUSH` i `POP:n`. Kod potrafi zapisać kilka otwarć i zamknięć na tym samym słowie (`corpipe26_onestage.py:122–157`). Lokalny `tags.txt` zawiera 55 kombinacji operacji rzeczywiście zaobserwowanych podczas treningu (`kod/models/corpipe26-onestage-corefud1.4-base-260702/tags.txt:1–55`). Dzięki stosowi model może reprezentować wzmian­ki zagnieżdżone i nakładające się, o ile mieszczą się w ograniczeniu głębokości.

Podczas inferencji CorPipe nie wybiera niezależnie najlepszego tagu dla każdego słowa. Dynamiczne programowanie uwzględnia dozwolone przejścia głębokości stosu i wymusza sekwencję z poprawnie zbilansowanymi operacjami (`corpipe26_onestage.py:185–197`, `477–499`). Domyślna głębokość wynosi 5 (`:36`). Artykuł opisuje tę metodę jako rozszerzone kodowanie BIO obsługujące nakładające się zakresy oraz strukturalne dekodowanie ([Straka 2026](https://aclanthology.org/2026.codi-1.27.pdf), s. 207, sekcja 3 i rysunek 2).

CorefSeg-AE nie ma osobnej głowicy granic. Macierz celu zaznacza wszystkie pary tokenów należących do dowolnych wzmianek tej samej encji (`C:\Users\Kamil\Desktop\mg\kod\src\data\windowing.py:39–53`). Na etapie predykcji wzmianką staje się maksymalny ciąg dodatnich elementów przekątnej (`...\src\models\decoding.py:24–53`). Powoduje to nieodwracalną utratę informacji:

- dwie sąsiadujące dodatnie wzmianki zostają jednym ciągiem;
- zakres wewnętrzny i zewnętrzny nie mogą być odtworzone jako dwie osobne wzmianki;
- macierz nie przechowuje granic dwóch wzmianek tej samej encji, jeśli ich tokeny tworzą jeden spójny odcinek;
- jeden próg `0.5` steruje jednocześnie wykrywaniem tokenów wzmianek i późniejszym linkingiem (`...\configs\base.yaml:16–18`).

To nie jest tylko słabszy dekoder tej samej informacji. Informacja o segmentacji wzmianek nie występuje jednoznacznie w celu macierzowym.

### Ograniczenie również po stronie CorPipe

CorPipe także upraszcza pełny CorefUD: wzmiankę nieciągłą redukuje do ciągłego fragmentu zawierającego jej head (`corpipe26_onestage.py:89–97`), a dwa przypadki sprowadzone do identycznego zakresu deduplikuje (`:100–105`). Nie należy więc przedstawiać go jako bezstratnej implementacji całego formatu. Mimo tego jego reprezentacja zachowuje znacznie więcej informacji o granicach niż przekątna CorefSeg.

## 2. CorPipe optymalizuje wybór poprzednika

Po wykryciu wzmianki CorPipe reprezentuje ją przez konkatenację embeddingów jej początku i końca. Osobne sieci `query` i `key` tworzą wynik będący skalowanym iloczynem wektorów (`corpipe26_onestage.py:398–405`, `436–456`).

Dla każdej bieżącej wzmianki kandydatami są wcześniejsze wzmianki obecne w kontekście oraz ona sama (`:227–241`, `572–592`). Wybór siebie oznacza utworzenie nowej encji. Podczas inferencji `argmax` daje dokładnie jednego poprzednika albo decyzję o nowym klastrze (`:580–592`). Nie ma progu, który niezależnie włącza wiele sprzecznych krawędzi.

Złoty cel również wykorzystuje strukturę klastrów:

- jeżeli istnieje kilka wcześniejszych wzmianek tej samej encji, masa prawdopodobieństwa jest rozdzielona równo między wszystkie poprawne antecedenty;
- jeżeli nie istnieje żaden poprzednik, celem jest sama bieżąca wzmianka;
- maska uniemożliwia wybór przyszłej wzmianki;
- stosowane jest wygładzanie etykiet 0,2.

Dowód: `corpipe26_onestage.py:227–241`, `458–475`; wartość `label_smoothing` w `kod/models/corpipe26-onestage-corefud1.4-base-260702/options.json`.

CorefSeg uczy każde pole macierzy poprzez BCE + soft Dice (`C:\Users\Kamil\Desktop\mg\kod\src\models\losses.py:9–29`). Następnie łączy dwie wykryte wzmianki, jeżeli średnia ich prostokątnego bloku przekroczy ten sam próg, a klastry buduje przez union-find (`...\src\models\decoding.py:55–68`). Pojedyncze błędne połączenie może więc tranzytywnie skleić dwa większe klastry. Co ważniejsze, koszt błędu granicy jest w treningu sumą błędów pojedynczych pikseli, chociaż w dekoderze zmiana jednego elementu przekątnej może połączyć lub rozdzielić cały span. Funkcja celu nie jest dobrze dopasowana do operacji dekodera ani końcowego CoNLL F1.

## 3. Encoder CorPipe jest dostrajany, HerBERT CorefSeg jest zamrożony

CorPipe przekazuje do optymalizatora `self.parameters()`, co obejmuje encoder i wszystkie głowice (`corpipe26_onestage.py:409–416`). Wyjścia wspólnego encodera zasilają wykrywanie granic, reprezentacje pustych wzmianek oraz linking (`:418–456`). Przy wczytywaniu checkpointu encoder jest najpierw tworzony z konfiguracji, a następnie cały stan jest odtwarzany z `model.pt` (`:385–388`, `675–677`).

CorefSeg jawnie ustawia HerBERT w tryb `eval`, wyłącza gradient dla wszystkich parametrów i koduje tekst wewnątrz `torch.no_grad()` (`C:\Users\Kamil\Desktop\mg\kod\src\models\encoder.py:1–6`, `45–51`, `84–92`). Trening obejmuje tylko projekcję do 32 wymiarów, tensor cech par i U-Net (`...\src\models\unet2d.py:78–93`; `...\train.py:104–120`). W długim przebiegu daje to 7,80 mln trenowanych parametrów (`C:\Users\Kamil\Desktop\mg\kod\runs\unet_long\train.log:5`).

Rozmiar checkpointu CorPipe około 1,16 GiB wynika przede wszystkim z zapisania około 269 mln dostrojonych parametrów `umT5-base`, a nie z niepotrzebnej, gigantycznej głowicy. Karta modelu identyfikuje bazę jako `google/umt5-base` (`kod/models/corpipe26-onestage-corefud1.4-base-260702/README.md:1–15`), a artykuł podaje 269 mln parametrów ([Straka 2026](https://aclanthology.org/2026.codi-1.27.pdf), tabela 2, s. 207). Lokalny `model.pt` ma 1 241 572 007 bajtów.

Wniosek: porównanie „30 MB kontra 1,16 GB” było mylące. Pierwsza liczba obejmuje wyłącznie trenowaną głowicę CorefSeg, ale w inferencji nadal potrzebny jest HerBERT. Rzeczywistą różnicą metodologiczną jest przede wszystkim zamrożenie kontra dostrojenie encodera.

## 4. Kontekst CorPipe jest dłuższy i ma strukturę dokumentu

CorPipe traktuje kolejne zdanie jako obszar, dla którego generuje predykcje, ale do wejścia dołącza możliwie dużo wcześniejszego tekstu oraz do 50 tokenów z prawej strony (`corpipe26_onestage.py:199–230`). Złote wcześniejsze wzmianki są kandydatami podczas uczenia, a przewidziane wcześniejsze wzmianki są przechowywane i używane podczas inferencji (`:227–241`, `501–576`).

Model był uczony z segmentem 512, lecz publikowane wyniki uzyskano z segmentem 2560, z wyjątkiem dwóch korpusów PROIEL. Autor uzasadnia to lepszym modelowaniem odległych powiązań; encoder z relatywnymi pozycjami pozwala wydłużyć segment podczas inferencji ([Straka 2026](https://aclanthology.org/2026.codi-1.27.pdf), s. 207, wiersze 234–238 ekstrakcji; karta modelu `README.md:33–41`).

CorefSeg używa okien 256 subtokenów ze stride 128 (`C:\Users\Kamil\Desktop\mg\kod\configs\unet_small.yaml:5–6`; dziedziczone przez `unet_long.yaml`). Każde okno jest dekodowane niezależnie, a dwa klastry z różnych okien łączą się wyłącznie wtedy, gdy zawierają wzmiankę o dokładnie tym samym spanie (`...\src\data\windowing.py:75–110`; `...\evaluate.py:234–260`). Jeżeli wspólna wzmianka zostanie pominięta albo jej granica przesunie się w jednym oknie, połączenie dokumentowe przepada. Nawet przy poprawnym sklejeniu bezpośredni kandydat relacji nie wykracza poza pojedyncze okno.

## 5. Puste węzły nie są detalem formatu

One-stage CorPipe tworzy do dwóch kandydatów pustej wzmianki dla każdego tokenu. Osobna głowica wybiera `NONE` albo relację zależności, a zaakceptowana pusta wzmianka trafia do tej samej procedury wyboru antecedenta co zwykłe wzmianki (`corpipe26_onestage.py:397–434`, `540–576`). Wartość `zeros_per_parent=2` jest częścią opublikowanej konfiguracji (`options.json`). Artykuł opisuje wspólne uczenie pustych wzmianek, granic i linków na s. 208.

CorefSeg wczytuje istniejący złoty pusty węzeł jako zwykły token o formie `_` (`C:\Users\Kamil\Desktop\mg\kod\src\data\corefud_reader.py:1–10`, `117–128`) i przepuszcza go przez zwykłą macierz. Nie ma jednak głowicy, która utworzyłaby taki węzeł z surowego tekstu. To znaczy, że na danych z gotowymi złotymi pustymi węzłami może nauczyć się ich klastrów, ale w zastosowaniu end-to-end nie potrafi ich najpierw wykryć. Jest to realna część zadania CorefUD, szczególnie w językach pro-drop.

Oficjalna ablacja pokazuje skalę problemu dla korpusów z zerami: usunięcie pustych węzłów obniża średni wynik mT5-large o 11,8 punktu, a dla polskiego o około 11 punktów ([Straka 2026](https://aclanthology.org/2026.codi-1.27.pdf), tabela 8, s. 212). Nie wolno bez dodatkowej kontroli przypisać całej różnicy CorefSeg–CorPipe właśnie zerom, ale nie wolno ich też ignorować przy porównaniu systemów.

## 6. Trening i dobór checkpointu

Opublikowany CorPipe base był uczony przez 15 epok po 10 000 batchy, z batch size 8, AdaFactorem, 10% warmupu i kosinusowym spadkiem learning rate. Daje to 150 000 aktualizacji oraz nominalnie 1,2 mln wylosowanych przykładów segmentowych. Źródła: `kod/models/corpipe26-onestage-corefud1.4-base-260702/options.json` oraz `corpipe26_onestage.py:409–416`.

Sampler jest deterministyczny względem seedu i waży korpusy potęgą liczności `0.5`, zamiast pozwolić największym zbiorom całkowicie zdominować epokę (`corpipe26_onestage.py:320–356`). Jest to wprawdzie element treningu wielokorpusowego, lecz sam mechanizm próbkowania i stała liczba kroków stanowią niezależne różnice w reżimie optymalizacji.

Autor trenował po 10 inicjalizacji dla każdego rozmiaru standardowego CorPipe i oceniał modele na minidev; w artykule wyniki ablacyjne są średnimi z co najmniej dwóch przebiegów, a wyniki zgłoszonego zespołu z siedmiu ([Straka 2026](https://aclanthology.org/2026.codi-1.27.pdf), s. 207 i tabela 6). Kod zapisuje checkpoint i uruchamia oficjalną ewaluację po każdej epoce (`corpipe26_onestage.py:681–699`).

CorefSeg zapisuje najlepszy model według walidacyjnego BCE+Dice, nie według mention F1 ani CoNLL F1 (`C:\Users\Kamil\Desktop\mg\kod\train.py:130–156`). To może wybrać checkpoint o lepszej kalibracji pikseli, ale gorszych granicach i klastrach po nieliniowym dekodowaniu.

## 7. Dlaczego „ten sam PCC” nie oznacza porównywalnego eksperymentu

Prawdą jest, że checkpoint CorPipe zawiera `pl_pcc` w liście zbiorów treningowych (`kod/models/corpipe26-onestage-corefud1.4-base-260702/options.json`). Nie oznacza to jednak, że oba modele dostały ten sam sygnał:

- CorPipe dostraja encoder, CorefSeg go zamraża;
- CorPipe nadzoruje osobno tagi wzmianek i antecedenty, CorefSeg nadzoruje komórki macierzy;
- CorPipe zachowuje nakładanie się ciągłych wzmianek, CorefSeg traci ich granice w macierzy;
- CorPipe jawnie generuje puste wzmianki, CorefSeg wymaga ich obecności na wejściu;
- CorPipe podczas publikowanej inferencji korzysta z kontekstu do 2560 tokenów, CorefSeg z 256 subtokenów;
- CorPipe używa oficjalnego parsera Udapi i zapisuje wynik z `MoveHead` (`corpipe26_onestage.py:277–302`), podczas gdy CorefSeg ma własny czytnik, przybliżający części nieciągłe jako osobne ciągłe wzmianki (`C:\Users\Kamil\Desktop\mg\kod\src\data\corefud_reader.py:33–45`);
- opublikowany CorPipe ma znacznie więcej aktualizacji i został sprawdzony na wielu inicjalizacjach.

Zatem uczciwa ablacja wpływu architektury wymagałaby wytrenowania CorPipe tylko na Polish-PCC albo zastosowania jego dekodera i celów z tym samym polskim encoderem i splitem. Bez tego można wskazać mechanizmy oraz ograniczenia reprezentacji, ale nie można liczbowo rozdzielić ich wkładu od dodatkowych danych i skali treningu.

## 8. Co warto przenieść, a czego nie kopiować

### Minimalna zmiana o największej wartości

Nie należy kopiować całego CorPipe ani porzucać tematu autokodera. Najbardziej obronny wariant CorefSeg-AE v2 to:

1. pozostawić DAE/U-Net jako eksperymentalny moduł tworzący lub odszumiający cechy relacyjne;
2. dodać osobną głowicę granic wzmianek, początkowo prostą BIO lub start/end;
3. reprezentować wykrytą wzmiankę przez embedding początku, końca i ewentualnie pooling wnętrza;
4. dodać klasyfikację antecedenta z kandydatem `self = nowy klaster`;
5. trenować linking rozkładem po wszystkich poprawnych wcześniejszych antecedentach;
6. odmrozić przynajmniej ostatnie 2–4 warstwy HerBERT-a;
7. dobierać checkpoint według CoNLL F1 lub mention F1 + CoNLL F1 na zamrożonym dev;
8. wydłużyć kontekst dopiero po usunięciu ograniczenia reprezentacji.

Pierwsza wersja nie musi implementować pełnych tagów stosowych. BIO/start-end nie obsłuży wszystkich zagnieżdżeń, ale pozwoli empirycznie sprawdzić, ile poprawy daje samo oddzielenie granic od relacji. Następnie stack tags CorPipe można dodać jako drugi wariant.

### Kolejność sprawdzalnych ablac­ji

Każdy wariant powinien używać tego samego splitu PCC i co najmniej trzech seedów:

1. obecny CorefSeg z tym samym encoderem i kontekstem;
2. osobna głowica wzmianek, bez zmiany encodera;
3. poprzedni wariant + antecedent/self zamiast union-find;
4. poprzedni wariant + częściowe dostrojenie HerBERT-a;
5. poprzedni wariant + dłuższy kontekst;
6. opcjonalnie DAE przed uczeniem nadzorowanym.

Raportować osobno mention precision/recall/F1, CoNLL F1, przypadki nakładające się, zera, odległość antecedenta oraz użycie VRAM. Dopiero taki eksperyment odpowie, która różnica daje największy zysk.

### Czego nie kopiować bez kontroli

- redukcji wzmianki nieciągłej do fragmentu wokół head (`corpipe26_onestage.py:89–105`);
- stałego limitu głębokości stosu 5 bez pomiaru pokrycia PCC (`:36`, `477–499`);
- obcinania bardzo długiego pojedynczego zdania (`:207–211`);
- wyboru najlepszego z wielu seedów bez raportowania średniej i wariancji;
- zachłannego chronologicznego linkowania jako rzekomej globalnej optymalizacji — kod wybiera lokalny `argmax` (`:580–592`);
- treningu antecedentów na złotych granicach bez osobnego raportu propagacji błędów z przewidzianych wzmianek. Głowice współdzielą encoder, ale dyskretny dekoder granic nie przekazuje gradientu z lossu antecedenta do decyzji tagów.

## Konkluzja

Najbardziej prawdopodobna kolejność przyczyn przewagi CorPipe jest następująca:

1. **jawna, strukturalna detekcja wzmianek**, która nie ma ograniczenia przekątnej CorefSeg;
2. **cel antecedent/self zgodny z klastrowaniem**, zamiast BCE na wszystkich parach tokenów;
3. **dostrajanie całego encodera** do koreferencji;
4. **znacznie dłuższy kontekst dokumentowy**;
5. **jawna obsługa pustych wzmianek**;
6. **mocniejszy reżim treningowy i selekcja na metryce zadania**;
7. dodatkowe dane wielojęzyczne i dopiero obok nich rozmiar modelu.

Punkty 1 i 2 są potwierdzone bezpośrednio przez kod i pokazują wadę reprezentacyjną CorefSeg, niezależnie od liczby parametrów. Nie da się jednak z istniejących wyników przypisać każdemu czynnikowi konkretnej liczby punktów F1. Wymaga to opisanych wyżej ablac­ji na identycznym PCC.

## Skrócony rejestr dowodów

| Twierdzenie | Źródło pierwotne |
|---|---|
| CorPipe używa PUSH/POP i strukturalnego DP | `corpipe26_onestage.py:122–197`, `477–499` |
| Wzmianka = początek + koniec; linking query/key | `corpipe26_onestage.py:398–405`, `436–456` |
| `self` rozpoczyna encję | `corpipe26_onestage.py:227–241`, `580–592` |
| Trzy bezpośrednie straty CE | `corpipe26_onestage.py:458–475` |
| Encoder CorPipe jest dostrajany | `corpipe26_onestage.py:385–416` |
| Kontekst lewy/prawy i segmenty 512/2560 | `corpipe26_onestage.py:199–230`; [artykuł, s. 207](https://aclanthology.org/2026.codi-1.27.pdf) |
| CorPipe generuje do dwóch pustych wzmianek na parent | `corpipe26_onestage.py:397–434`, `540–576`; `options.json` |
| CorefSeg traci granice w macierzy | `windowing.py:39–53`; `decoding.py:24–53` w `C:\Users\Kamil\Desktop\mg\kod` |
| CorefSeg zamraża HerBERT | `encoder.py:45–51`, `84–92` w `C:\Users\Kamil\Desktop\mg\kod` |
| CorefSeg skleja okna tylko przez identyczny span | `windowing.py:75–110` w `C:\Users\Kamil\Desktop\mg\kod` |
| Skala daje CorPipe base→XXL +6,76 pkt średnio | [artykuł, tabela 5](https://aclanthology.org/2026.codi-1.27.pdf) |

### Hashe kodu CorefSeg użytego w analizie

- `src/models/decoding.py`: `6BBAB1A10CAF8DEEE680F9E370D980F8677D77FCA98DD173A869B70EE42369F9`
- `src/models/unet2d.py`: `3951BB80B4D9F9B06A432D847A25E40E3CB59DC6C7723ED3539EB00460FDE574`
- `src/models/losses.py`: `4A7D114F4673E77F2836BF9A50E97234800D565055A7743627A93A2FC8746DB9`
- `src/data/windowing.py`: `F6898ACDA6876210C6AC9E8C53CCA213B2D0BA3FAE5AF40633006145CDFFC11E`
- `src/models/encoder.py`: `309B0308F93AFA2F6A07FD51AC1A9156824505BCD0DF5FABB72A35C20B3FB430`
- `train.py`: `4C90928D08A7CCCC7FACC19E591639FD378F8FC719DAC0D0A718762FA51CC731`
