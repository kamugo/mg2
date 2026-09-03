# Autokodery istotne dla analizy koreferencji

Stan weryfikacji: 2026-09-03. Przegląd obejmuje tylko mechanizmy, które można przełożyć na reprezentację wzmianek, segmentację macierzy relacji, uczenie domenowe albo klastrowanie encji.

## 1. Klasyczny autokoder (AE)

Autokoder (autoencoder, AE) składa się z kodera \(z=f_\theta(x)\) i dekodera \(\hat{x}=g_\phi(z)\), uczonych przez minimalizację błędu rekonstrukcji. Wąskie gardło wymusza kompresję, ale bez odpowiedniej regularyzacji model o dużej pojemności może nauczyć się niemal identyczności. Dla koreferencji wejściem może być wektor wzmianki albo wiersz macierzy zgodności, a kod latentny może zasilać klasyfikator par. Koszt pełnego połączenia rośnie jak iloczyn wymiarów kolejnych warstw; dla macierzy \(n\times n\) korzystniejsze są sploty. Klasyczne podstawy i ograniczenia opisano w rozdziale 14 podręcznika Goodfellowa i in. \cite{goodfellow_2016_deep}.

Wiersz porównawczy: AE | zbiory ogólne; zastosowanie projektowane dla PCC/prawniczych | błąd rekonstrukcji | — | goodfellow_2016_deep

## 2. Autokoder odszumiający (DAE)

Autokoder odszumiający (denoising autoencoder, DAE) otrzymuje zaburzone \(\tilde{x}\), lecz rekonstruuje czyste \(x\). Wymusza to cechy stabilne wobec brakujących lub zmienionych składowych, zamiast prostego kopiowania wejścia. W koreferencji zasadne są maskowanie cech morfosyntaktycznych, zakłócanie granic wzmianek i usuwanie wybranych krawędzi relacji. Wyjściem pozostaje rekonstrukcja wejścia, a kod latentny może zostać przeniesiony do zadania nadzorowanego. DAE wprowadza dodatkowy koszt generowania zakłóceń, lecz nie zmienia zasadniczego rzędu kosztu przejścia sieci \cite{vincent_2008_dae}.

Wiersz porównawczy: DAE | benchmarki klasyfikacyjne; transfer projektowany do domeny prawnej | błąd rekonstrukcji / błąd klasyfikacji | — | vincent_2008_dae

## 3. Autokoder wariacyjny (VAE)

Autokoder wariacyjny (variational autoencoder, VAE) koduje przykład jako parametry rozkładu przybliżonego, a próbkę latentną uzyskuje przez reparametryzację. Funkcja celu łączy oczekiwaną rekonstrukcję z dywergencją KL do prioru, czyli maksymalizuje dolne ograniczenie wiarygodności (evidence lower bound, ELBO). Gładka przestrzeń latentna ułatwia próbkowanie i może stabilizować reprezentacje rzadkich typów wzmianek. Dla deterministycznego rozstrzygania koreferencji losowość i zapadanie posterioru są jednak dodatkowym ryzykiem, dlatego VAE powinien być ablacją, nie wariantem głównym. Koszt jest zbliżony do AE, ale koder wyznacza co najmniej średnią i skalę \cite{kingma_2013_vae}.

Wiersz porównawczy: VAE | MNIST i Frey Face | ELBO / log-likelihood | — | kingma_2013_vae

## 4. Autokoder rzadki

Autokoder rzadki (sparse autoencoder) dodaje karę za aktywność kodu, na przykład normę \(L_1\) albo dywergencję od zadanej małej częstości aktywacji. Pozwala stosować kod szerszy niż wejście, o ile dla pojedynczego przykładu aktywna jest niewielka liczba cech. W koreferencji taki kod może rozdzielać sygnały rodzaju gramatycznego, liczby, roli prawnej i zgodności semantycznej. Zaletą jest potencjalna interpretowalność cech, wadą zaś wrażliwość na siłę kary i ryzyko martwych jednostek. Nie istnieje z tego automatyczny wniosek o poprawie metryk koreferencji; wymaga to osobnej ablacji \cite{goodfellow_2016_deep}.

Wiersz porównawczy: sparse AE | przykłady reprezentacyjne w literaturze ogólnej | rekonstrukcja + kara rzadkości | — | goodfellow_2016_deep

## 5. Autokoder kontraktywny

Autokoder kontraktywny (contractive autoencoder) dodaje normę Frobeniusa jakobianu kodera względem wejścia. Kara ogranicza zmianę reprezentacji przy małych perturbacjach wejścia, zachowując kierunki potrzebne do rekonstrukcji. W polskich tekstach prawnych może to zwiększyć odporność na fleksyjne warianty nazw i drobne różnice redakcyjne, jeżeli zakodowano je w ciągłych reprezentacjach. Jawne liczenie jakobianu jest kosztowniejsze pamięciowo i obliczeniowo niż zwykły AE. Metoda nie rozwiązuje sama wykrywania wzmianek ani tworzenia partycji encji \cite{rifai_2011_contractive}.

Wiersz porównawczy: contractive AE | benchmarki klasyfikacyjne | rekonstrukcja + norma Jacobianu | — | rifai_2011_contractive

## 6. U-Net i segmentacja macierzy 2D

U-Net łączy ścieżkę kompresującą ze ścieżką rozszerzającą i przekazuje cechy wysokiej rozdzielczości połączeniami skrótowymi (skip connections). Oryginalnie wyjściem jest maska segmentacji o rozdzielczości wejścia, a architekturę opracowano dla obrazów biomedycznych \cite{ronneberger_2015_unet}. W projekcie macierz \(M_{ij}\) może kodować cechy par wzmianek, a maska przewidywać krawędzie koreferencji. Sploty pozwalają wykorzystać lokalne wzorce bloków odpowiadające skupieniom, jednak arbitralna kolejność wzmianek i symetria macierzy muszą zostać jawnie obsłużone. Pełna macierz ma koszt pamięci \(O(n^2)\), więc potrzebne są okna, kafle albo rzadkie kandydaty.

Wiersz porównawczy: U-Net | ISBI: obrazy biomedyczne | segmentacja / czas | zwycięstwo w ISBI bez wartości przepisanej do tej tabeli | ronneberger_2015_unet

## 7. Segmentacja szeregów czasowych i transfer

Wen i Keyes przełożyli U-Net na jednowymiarową segmentację szeregów oraz pretraining na danych syntetycznych \cite{wen_2019_time}. Analogią dla koreferencji jest sekwencja potencjalnych poprzedników albo kolejne wiersze macierzy relacji, gdzie należy wykryć spójny odcinek lub wzorzec. Praca pokazuje, że architektura segmentacyjna może przenosić cechy między rozkładami przy niedoborze etykiet. Na syntetycznych krzywych autorzy podają IoU 50,96% przy treningu od zera i 71,95% po transferze; są to wyniki obcego zadania, a nie dowód jakości koreferencji. Różnica stanowi uzasadnienie testowania domenowego pretrainingu, nie wartość oczekiwaną dla pracy.

Wiersz porównawczy: U-Net 1D + transfer | syntetyczne krzywe, 1400 próbek | IoU | 50,96% od zera; 71,95% po transferze [nieporównywalne z koreferencją] | wen_2019_time

## 8. DEC i IDEC: klastrowanie w przestrzeni latentnej

Deep Embedded Clustering (DEC) najpierw uczy reprezentację, następnie wspólnie dostraja mapowanie i miękkie przypisania do centroidów przez dywergencję KL \cite{xie_2016_dec}. Wyjściem jest etykieta klastra dla każdego przykładu, co odpowiada partycjonowaniu wzmianek na encje. DEC zakłada jednak z góry liczbę klastrów, podczas gdy liczba encji zmienia się między dokumentami, a cel samowzmacniający może zniekształcić przestrzeń. Improved DEC (IDEC) zachowuje równolegle stratę rekonstrukcji, aby chronić lokalną strukturę \cite{guo_2017_idec}. Dla koreferencji użyteczniejszy jest zatem cel inspirowany IDEC, ale z dokumentowymi prototypami lub klastrowaniem progowym zamiast globalnej stałej liczby klas.

Wiersz porównawczy: DEC | MNIST, USPS, REUTERS-10K, STL-10 | ACC/NMI | — | xie_2016_dec

Wiersz porównawczy: IDEC | obrazy i tekst | ACC/NMI | — | guo_2017_idec

## 9. Autokodery grafowe i macierz przyległości

Wariacyjny autokoder grafowy (variational graph autoencoder, VGAE) koduje węzły za pomocą splotu grafowego, a prosty dekoder iloczynu skalarnego rekonstruuje krawędzie macierzy przyległości \cite{kipf_2016_vgae}. W koreferencji węzłami są wzmianki, cechami ich embeddingi, a krawędziami relacja współreferencji. Taka reprezentacja naturalnie wymusza wspólną przestrzeń wzmianek, lecz rekonstrukcja niezależnych krawędzi nie gwarantuje przechodniości całych klastrów. Structural Deep Network Embedding zachowuje jednocześnie bliskość pierwszego i drugiego rzędu i waży błędy niezerowych elementów, co jest ważne dla bardzo rzadkiej macierzy relacji \cite{wang_2016_sdne}. Oba warianty mają co najmniej koszt zależny od liczby kandydackich krawędzi; pełny dekoder iloczynowy ponownie prowadzi do \(O(n^2)\).

Wiersz porównawczy: VGAE | grafy cytowań | AUC/AP w predykcji krawędzi | — | kipf_2016_vgae

Wiersz porównawczy: SDNE | 5 sieci rzeczywistych | klasyfikacja / link prediction / wizualizacja | — | wang_2016_sdne

## 10. Autokodery grafowe dla tekstu

Chiu i in. budują graf korelacji słów kluczowych z cechami lokalnymi i globalnymi, a autokoder grafowy rekonstruuje te zależności przed klastrowaniem dokumentów \cite{chiu_2020_keyword}. Jest to bezpośredni dowód, że grafowy AE może agregować strukturę wewnątrz- i międzyzdaniową tekstu, ale jednostką wyjściową pozostaje klasa dokumentu, nie encja. Adaptacja do koreferencji wymaga zmiany węzłów na wzmianki i uczenia na poziomie pojedynczego dokumentu. Model może służyć jako inspiracja dla kompresji grafu kandydatów, nie jako gotowy baseline. Koszt budowy gęstego grafu trzeba ograniczyć pruningiem poprzedników.

Wiersz porównawczy: GAE grafu słów kluczowych | 20 Newsgroups, Reuters | miary klastrowania | poprawa względem cech bazowych; brak bezpiecznie przepisanej liczby | chiu_2020_keyword

## Synteza dla projektu

Najmniejszym ryzykiem implementacyjnym jest deterministyczny DAE na embeddingach wzmianek: zachowuje liniowy koszt względem liczby wzmianek i umożliwia domenowy pretraining bez etykiet koreferencji. Najsilniej powiązany z tezą promotora jest konwolucyjny encoder--decoder segmentujący macierz kandydackich relacji, lecz wymaga ograniczenia kwadratowej pamięci oraz symetryzacji wyjścia. Trzeci uzasadniony wariant łączy rekonstrukcję IDEC z nadzorowaną stratą par, a końcowe klastry tworzy algorytm aglomeracyjny lub connected components z wymuszeniem spójności. VAE, sparse AE i contractive AE powinny pozostać ablacjami regularyzacji. VGAE jest wariantem rezerwowym, jeżeli macierz relacji zostanie przechowywana jako rzadki graf.

Nie znaleziono publikacji, która bezpośrednio wykazałaby skuteczność autokodera w polskiej koreferencji prawniczej. Przeniesienie z obrazów, szeregów i grafów jest hipotezą projektową, dlatego ocena musi używać identycznego enkodera, splitów i budżetu strojenia dla wariantu z AE i bez AE.
