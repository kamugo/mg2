# Koreferencja neuronowa — notatki do przeglądu

Wyniki liczbowe poniżej przepisano wyłącznie z odwiedzonych stron publikacji lub ich plików PDF. Nie należy porównywać ich bezpośrednio, jeśli różnią się korpus, podział danych, wersja scorera albo zasady uwzględniania singletonów.

## 1. Klasyfikacja par wzmianek (mention-pair)

Podejście Soon i in. tworzy przykłady dla par wcześniej wykrytych fraz nominalnych i uczy klasyfikator rozstrzygający, czy para jest koreferencyjna. Wejściem są ręcznie zaprojektowane cechy zgodności dwóch wzmianek, a wyjściem decyzja binarna, z której heurystycznie buduje się klastry. Konstrukcja rozpatruje kandydatów parami, dlatego nie modeluje bezpośrednio konkurencji między poprzednikami ani spójności całej encji. Złożoność liczby potencjalnych par jest kwadratowa względem liczby wzmianek, a jakość zależy od wcześniejszego potoku wykrywania fraz i cech językowych. Źródło: [Soon i in. 2001](https://aclanthology.org/J01-4004/), klucz `soon_2001_machine`.

`mention-pair | MUC-6/MUC-7 | MUC | — (nie przepisano wartości tabelarycznych) | soon_2001_machine`

## 2. Ranking poprzedników (mention-ranking)

Denis i Baldridge zastępują niezależną klasyfikację par rankingiem wszystkich kandydatów na poprzednika danej anafory. Wejściem pozostają cechy pary, lecz funkcja ucząca uwzględnia konkurencję między kandydatami; wyjściem jest najwyżej oceniony poprzednik albo decyzja o braku poprzednika. Autorzy dodatkowo uczą wyspecjalizowane modele dla zaimków, nazw własnych, deskrypcji określonych i innych fraz. Ranking upraszcza późniejsze dekodowanie, ale nadal wiąże lokalne decyzje w klastry za pomocą reguły przechodniości i zależy od jakości listy wzmianek. Na ACE obie modyfikacje dały wzrost F-score przekraczający 3% dla MUC, B³ i CEAF. Źródło: [Denis i Baldridge 2008](https://aclanthology.org/D08-1069/), klucz `denis_2008_specialized`.

`mention-ranking | ACE Phase 2 | MUC/B³/CEAF F-score | wzrost >3% względem modeli bazowych | denis_2008_specialized`

## 3. Modelowanie encji i cech globalnych (entity-based)

Wiseman i in. reprezentują każdy rozwijany klaster encji za pomocą rekurencyjnej sieci neuronowej nad jego wzmiankami. Reprezentacja klastra jest dołączana do systemu mention-ranking, dzięki czemu decyzja lokalna może zależeć od dotychczasowej historii całej encji. Wejściem są reprezentacje wzmianek i istniejących klastrów, a wyjściem wybór klastra lub nowej encji. Model jest uczony end-to-end bez ręcznie projektowanych cech klastrowych, lecz sekwencyjne tworzenie klastrów może propagować wcześniejsze błędy. Autorzy raportują poprawę CoNLL score o 0,8 punktu względem wcześniejszego stanu wiedzy, istotną dla wszystkich trzech metryk składowych. Źródło: [Wiseman i in. 2016](https://aclanthology.org/N16-1114/), klucz `wiseman_2016_global`.

`entity-based RNN | CoNLL-2012/OntoNotes | CoNLL score | +0,8 pkt względem wcześniejszego SOTA | wiseman_2016_global`

## 4. Stanford multi-pass sieve

System sitowy wykonuje uporządkowaną sekwencję reguł od najbardziej precyzyjnych do coraz bardziej liberalnych, łącząc klastry po każdym przebiegu. Wejściem są wzmianki wraz z informacją leksykalną, składniową i semantyczną, a wyjściem klastry aktualizowane deterministycznie. Wczesne decyzje dostarczają bogatszego kontekstu następnym sitom i czynią zachowanie systemu interpretowalnym. Koszt jest w przybliżeniu sumą kosztów poszczególnych przebiegów, lecz błędne połączenie jest nieodwracalne, a reguły wymagają adaptacji do języka i domeny. Źródło: [Raghunathan i in. 2010](https://aclanthology.org/D10-1048/), klucz `raghunathan_2010_sieve`.

`multi-pass sieve | ACE + OntoNotes | MUC/B³/CEAF | — (nie przepisano wartości tabelarycznych) | raghunathan_2010_sieve`

## 5. e2e-coref

Lee i in. traktują wszystkie ciągłe spany dokumentu do ustalonej długości jako potencjalne wzmianki, bez osobnego detektora. Reprezentacja spanu łączy stany tokenów brzegowych, uwagę nad jego wnętrzem i cechy szerokości, a scoring wybiera poprzednika lub symbol pusty. Agresywne przycinanie pozwala ograniczyć przestrzeń kandydatów, mimo że liczba spanów rośnie kwadratowo z długością dokumentu, a par spanów jeszcze szybciej. Uczenie maksymalizuje zmarginalizowane prawdopodobieństwo poprawnych poprzedników, lecz model jest pamięciochłonny i może tracić wzmianki podczas pruning. Autorzy podają poprawę 1,5 F1 na OntoNotes, a ensemble pięciu modeli 3,1 F1. Źródło: [Lee i in. 2017](https://aclanthology.org/D17-1018/), klucz `lee_2017_e2e`.

`e2e-coref | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | +1,5 pkt; ensemble +3,1 pkt względem wcześniejszego SOTA | lee_2017_e2e`

## 6. c2f-coref i wnioskowanie wyższego rzędu

Lee i in. wprowadzają tani biliniowy scoring coarse-to-fine, który odrzuca większość par przed kosztownym scoringiem dokładnym. Rozkład poprzedników działa następnie jako mechanizm uwagi do iteracyjnego uaktualniania reprezentacji spanów, co przybliża informację o całych klastrach. Wejściem są spanowe reprezentacje dokumentu, a wyjściem rozkłady poprzedników indukujące klastry. Przycinanie ogranicza koszt, ale pozostawia ryzyko nieodwracalnego usunięcia poprawnego poprzednika i zachowuje pamięciochłonne reprezentacje spanów. W tabeli porównawczej pracy Maverick wariant c2f-coref z ELMo ma 73,0 CoNLL F1, lecz warianty z późniejszymi enkoderami nie są z nim bezpośrednio porównywalne. Źródło: [Lee i in. 2018](https://aclanthology.org/N18-2108/), klucz `lee_2018_higher`.

`c2f-coref (ELMo) | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 73,0 (z tabeli porównawczej Maverick) | lee_2018_higher`

## 7. SpanBERT

SpanBERT zmienia pretraining BERT-a przez maskowanie całych ciągłych spanów i zadanie przewidywania ich zawartości z reprezentacji tokenów brzegowych. Taki cel lepiej odpowiada modelom koreferencji, które porównują wzmianki będące spanami, niż losowe maskowanie pojedynczych tokenów. Po zastosowaniu w architekturze c2f-coref wejściem pozostaje dokument, lecz enkoder dostarcza reprezentacje mocniej ukierunkowane na granice i zawartość spanów. Sam model nie usuwa kwadratowej przestrzeni spanów ani problemu długich dokumentów, a jego pretraining jest kosztowny. Autorzy raportują 79,6 CoNLL F1 na OntoNotes. Źródło: [Joshi i in. 2020](https://aclanthology.org/2020.tacl-1.5/), klucz `joshi_2020_spanbert`.

`SpanBERT + c2f-coref | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 79,6 | joshi_2020_spanbert`

## 8. wl-coref

Dobrovolskii przenosi podstawową decyzję z poziomu spanów na poziom pojedynczych słów, a pełne granice wzmianek rekonstruuje później. Wejściem są reprezentacje tokenów, z których model wyznacza potencjalne łącza słowo–słowo i granice; wyjściem są klastry spanów. Ogranicza to teoretyczną złożoność modułu koreferencji do O(n²) i usuwa konieczność pruning wszystkich par spanów o potencjalnej złożoności O(n⁴). Rekonstrukcja granic jest jednak dodatkowym źródłem błędów, szczególnie przy zagnieżdżonych lub wielowyrazowych wzmiankach. W tabeli porównawczej Maverick podano 81,0 CoNLL F1 na OntoNotes. Źródło: [Dobrovolskii 2021](https://aclanthology.org/2021.emnlp-main.605/), klucz `dobrovolskii_2021_word`.

`wl-coref (RoBERTa-large) | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 81,0 | dobrovolskii_2021_word`

## 9. s2e-coref

Kirstain i in. zachowują model end-to-end, ale rezygnują z jawnego tworzenia wektorów spanów i par spanów. Wynik dla wzmianki i poprzednika oblicza się lekkimi funkcjami biafinicznymi oraz biliniowymi nad reprezentacjami tokenów początkowych i końcowych. Wejściem są kontekstowe reprezentacje tokenów, a wyjściem scoring granic i poprzedników; przestrzenna złożoność dodatkowych reprezentacji spada z O(n²d) do poziomu zbliżonego do warstwy transformera. Model jest prostszy i oszczędniejszy, ale informacje z wnętrza długiej wzmianki są dostępne tylko pośrednio przez enkoder. W tabeli porównawczej Maverick podano 80,3 CoNLL F1. Źródło: [Kirstain i in. 2021](https://aclanthology.org/2021.acl-short.3/), klucz `kirstain_2021_s2e`.

`s2e-coref | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 80,3 | kirstain_2021_s2e`

## 10. LingMess

LingMess dzieli pary wzmianek na sześć lingwistycznie motywowanych kategorii i uczy osobnego scorera-eksperta dla każdej z nich. Wejściem są reprezentacje par oraz ich typ decyzji, a wyjściem suma scoringu ogólnego i właściwego eksperta. Rozdzielenie pozwala wykorzystywać inne sygnały dla zaimków, nazw i deskrypcji bez budowy osobnych pełnych modeli. Koszt rośnie przez wiele głowic scoringowych, a reguły kategoryzacji mogą wymagać dostosowania do polszczyzny i anotacji domenowej. Publikacja raportuje poprawę na OntoNotes i pięciu dodatkowych zbiorach; tabela porównawcza Maverick podaje 81,4 CoNLL F1 na OntoNotes. Źródło: [Otmazgin i in. 2023](https://aclanthology.org/2023.eacl-main.202/), klucz `otmazgin_2023_lingmess`.

`LingMess | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 81,4 | otmazgin_2023_lingmess`

## 11. Maverick

Maverick wraca do dyskryminacyjnego potoku encoder-only i rozdziela wykrywanie wzmianek od klasyfikacji wzmianka–poprzednik. Autorzy projektują warianty z ograniczonym zbiorem kandydatów oraz wariant inkrementalny, aby uzyskać dużą przepustowość bez wielkiego modelu generatywnego. Wejściem są dokumenty kodowane przez model rzędu 500 mln parametrów, a wyjściem klastry budowane z lokalnych decyzji. Rozwiązanie zachowuje ryzyko błędów potoku, lecz według publikacji trenuje się z użyciem do 0,006× pamięci i wykonuje inferencję 170× szybciej od wcześniejszych systemów generatywnych, osiągając stan wiedzy na CoNLL-2012. Źródło: [Martinelli i in. 2024](https://aclanthology.org/2024.acl-long.722/), klucz `martinelli_2024_maverick`.

`Maverick | OntoNotes 5.0 / CoNLL-2012 | efektywność + CoNLL F1 | do 0,006× pamięci treningowej i 170× szybsza inferencja; SOTA w publikacji | martinelli_2024_maverick`

## 12. Link-Append

Bohnet i in. formułują koreferencję jako przejścia tekst–tekst generowane przez mT5: `LINK` wskazuje ostatnią wzmiankę, `APPEND` dołącza do istniejącego klastra, a `SHIFT` przechodzi do następnego zdania. Wejście zawiera bieżące zdanie, kontekst i dotychczas zbudowane klastry, a wyjście jest sekwencją akcji. Model wspólnie wykrywa wzmianki i łącza bez osobnego span-search, ale wymaga bardzo dużego mT5 i autoregresyjnego dekodowania. Stan jest przekazywany zdanie po zdaniu, co pomaga przy długich dokumentach, lecz błędy tekstowego formatu lub wcześniejszych akcji mogą się propagować. Autorzy raportują 83,3 CoNLL F1 dla angielskiego, 68,5 dla arabskiego i 74,3 dla chińskiego CoNLL-2012. Źródło: [Bohnet i in. 2023](https://aclanthology.org/2023.tacl-1.13/), klucz `bohnet_2023_linkappend`.

`Link-Append (mT5-XXL) | CoNLL-2012 English | CoNLL F1 | 83,3 | bohnet_2023_linkappend`

## 13. ASP

Autoregressive Structured Prediction (ASP) generuje nie spłaszczony tekst anotacji, lecz sekwencję jawnych akcji strukturalnych. Dla koreferencji krok wskazuje granice wzmianki i poprzednika za pomocą mechanizmu pointer, warunkując decyzję na dokumencie i dotychczasowej strukturze. Wyjściem jest uporządkowany ciąg akcji, z którego bezstratnie odtwarza się spany i klastry. Model zachowuje zależności wewnątrz struktury, lecz autoregresja jest kosztowna i wynik silnie zależy od wielkości bazowego T5/FLAN-T5. Dla FLAN-T5 XXL raportowany wynik na OntoNotes wynosi 82,5 CoNLL F1. Źródło: [Liu i in. 2022](https://aclanthology.org/2022.findings-emnlp.70/), klucz `liu_2022_asp`.

`ASP (FLAN-T5 XXL) | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 82,5 | liu_2022_asp`

## 14. Seq2seq z anotacją w tekście

Zhang i in. uczą standardowy transformer seq2seq odwzorowujący dokument na tekst z dodatkowymi znacznikami granic i identyfikatorami klastrów. Wariant pełny generuje całą oznakowaną sekwencję, a uproszczony tylko oznakowane spany; oba unikają dedykowanego scorera spanów. Wejściem jest tekst dokumentu, a wyjściem liniowa reprezentacja anotacji możliwa do zdekodowania do klastrów. Architektura jest prosta, ale autoregresyjne generowanie może zmienić tekst, naruszyć format lub zgubić wzmiankę, a skuteczność rośnie wraz z rozmiarem modelu i ilością nadzoru. Publikacja podaje 83,2 CoNLL F1 dla OntoNotes. Źródło: [Zhang i in. 2023](https://aclanthology.org/2023.emnlp-main.704/), klucz `zhang_2023_seq2seq`.

`seq2seq tagged text (T0-XXL) | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 83,2 | zhang_2023_seq2seq`

## Wnioski dla projektu

Najważniejszy punkt odniesienia stanowią trzy rodziny: span-ranking (e2e/c2f/SpanBERT), oszczędniejsze modele tokenowe lub brzegowe (wl-coref, s2e-coref, Maverick) oraz modele generatywne (ASP, Link-Append, seq2seq). Dla dokumentów prawniczych szczególnie istotne są koszt O(n²) zamiast jawnych par spanów, obsługa długiego kontekstu, możliwość domenowego pretrainingu i osobna kontrola błędów wykrywania wzmianek. Liczb z różnych tabel nie należy traktować jako rankingu bez wspólnego kodu, podziału i oficjalnego scorera.
