# Sformułowanie problemu i wybór architektury

## 1. Formalna definicja zadania

Niech dokument będzie sekwencją tokenów \(D=(t_1,\ldots,t_L)\). Złoty zbiór wzmianek oznacza się przez \(G=\{g_i=(s_i,e_i,h_i,\tau_i)\}_{i=1}^{N}\), gdzie \(s_i,e_i\) są granicami, \(h_i\) głową, a \(\tau_i\) typem wzmianki; dopuszcza się pusty węzeł dla podmiotu zerowego. System przewiduje zbiór \(M=\{m_j\}_{j=1}^{\hat N}\), a następnie partycję \(\Pi(M)=\{C_1,\ldots,C_K\}\), w której każda wzmianka należy dokładnie do jednego klastra encji. Relacja \(R(m_i,m_j)=1\) wtedy i tylko wtedy, gdy obie wzmianki należą do tego samego klastra; musi być zwrotna, symetryczna i przechodnia.

Model wyznacza ocenę wzmianki \(s_m(m_i)\), ocenę poprzednika \(s_a(m_i,m_j)\) dla \(j<i\) oraz ocenę pustego poprzednika \(\epsilon\). Rozkład ma postać
\[
p(y_i=j\mid D)=\frac{\exp s(i,j)}{\sum_{j'\in Y_i}\exp s(i,j')},
\qquad Y_i=\{\epsilon,1,\ldots,i-1\}.
\]
Przy niejednoznacznym złotym poprzedniku minimalizuje się ujemny logarytm sumy prawdopodobieństw wszystkich poprawnych poprzedników. Predykcyjne krawędzie są dekodowane do partycji przez kontrolowane łączenie zbiorów rozłącznych; nie wystarcza niezależna progowa klasyfikacja macierzy.

Funkcja oceny końcowej jest średnią \(F_1\) metryk MUC, B³ i CEAF_e, czyli CoNLL F1. Dodatkowo mierzy się LEA, jakość wykrywania wzmianek oraz wyniki dla podmiotów zerowych. Porównania wykonuje się na jednym dokumencie testowym jako jednostce bootstrapu, zawsze z tą samą wersją scorera, regułą singletonów i sposobem dopasowania granic.

## 2. Dlaczego tekst prawniczy jest trudny

Poniższe zdania są skonstruowanymi przykładami, a nie cytatami z korpusu.

- Encja może nie mieć nazwy własnej: „Pozwany odebrał przesyłkę. Następnie **tenże** odmówił zapłaty”. Model musi połączyć deskrypcję roli z archaizującym zaimkiem.
- Głowa leksykalna może się zmieniać: „Nieruchomość przy ul. Leśnej została obciążona. **Powyższa nieruchomość** stanowi przedmiot zabezpieczenia”.
- Referencję tworzy termin definiowany lokalnie: „ABC sp. z o.o., **zwana dalej Wykonawcą**, dostarczy system. **Wykonawca** udzieli gwarancji”. Wiedza słownikowa poza dokumentem nie wystarcza.
- Anonimizacja usuwa główny sygnał nazwy: „Świadek X.Y. zeznał, że [dane usunięte] przekazał mu dokument”. Ten sam znacznik może zastępować różne osoby, dlatego dopasowanie powierzchniowe bywa mylące.
- Odwołanie może dotyczyć jednostki tekstu, nie encji świata: „Obowiązek określono w § 4 ust. 2. **Powyższe postanowienie** stosuje się odpowiednio”. Detektor musi rozróżnić referencję tekstową od osoby lub przedmiotu.
- Zależność bywa długa: „Powód” wymieniony na początku wielostronicowego uzasadnienia może powrócić jako „skarżący” po cytacie z ustawy i opisie kilku innych uczestników.
- Szablonowość wprowadza fałszywe podobieństwo: powtarzane „Sąd zważył, co następuje” nie oznacza nowej encji, a role „powód” i „pozwany” są powtarzalne między dokumentami, lecz nie mogą tworzyć klastrów ponad granicami dokumentu.

Polska fleksja zmienia formy tej samej nazwy, podmiot może pozostać niewyrażony, a swobodny szyk osłabia heurystykę najbliższego poprzednika. Jednocześnie role procesowe, terminy definiowane i odwołania paragrafowe są silnymi, lecz domenowymi cechami. Architektura powinna więc uczyć się reprezentacji na nieetykietowanym tekście prawniczym, ale końcową relację optymalizować na złotej koreferencji.

## 3. Wariant A — segmentacja macierzy wzmianek

Zamiast macierzy tokenów \(L\times L\) używa się macierzy kandydackich wzmianek \(M\times M\), ponieważ wariant tokenowy dla długiego dokumentu jest zbyt kosztowny i miesza detekcję granic z łączeniem. Po przycięciu przyjmuje się \(M\leq128\) w jednym oknie. Dla każdej pary tworzy się tensor \(X\in\mathbb{R}^{B\times C\times M\times M}\), gdzie \(C=8\): iloczyn skalarny embeddingów, zgodność rodzaju, liczby i osoby, odległość tokenowa, odległość zdaniowa, zgodność lematu/głowy oraz dwie oceny wzmianki. Maska rozróżnia padding i niedopuszczalne pary przyszłe.

Sieć typu U-Net ma kanały 32--64--128, trzy poziomy, jądra 3×3 i połączenia skrótowe. Wyjście \(Z\in\mathbb{R}^{B\times1\times M\times M}\) jest symetryzowane przez \((Z+Z^\top)/2\). Funkcja straty ma postać
\[
\mathcal L_A=\mathcal L_{\mathrm{BCE}}^{w}(Z,R)
+\lambda_{\mathrm{dice}}\mathcal L_{\mathrm{Dice}}
+\lambda_{\mathrm{tri}}\mathcal L_{\mathrm{trans}}.
\]
Ważona BCE przeciwdziała przewadze par negatywnych, Dice chroni rzadkie krawędzie, a ostatni składnik karze trójki naruszające przechodniość. Klasteryzator stosuje próg wybrany wyłącznie na dev i union-find.

Sam U-Net ma mniej niż 1 mln parametrów; wraz z projekcjami cech i detektorem zakłada się mniej niż 5 mln parametrów trenowanych przy zamrożonym HerBERT. Dla batcha 2, \(M=128\), mixed precision i akumulacji gradientu szacuje się 6--10 GB pamięci, a przy wspólnym strojeniu enkodera 14--20 GB. Są to szacunki projektowe do weryfikacji pomiarem szczytu CUDA, nie wyniki eksperymentalne. Ryzyka obejmują arbitralny porządek wzmianek, artefakty paddingu, koszt \(O(M^2)\), przeciek etykiety przez cechy regułowe i niezgodność lokalnych krawędzi z globalną partycją.

## 4. Wariant C — odszumiający autokoder domenowy

HerBERT generuje dla każdej wzmianki \(h_i\in\mathbb{R}^{768}\) przez konkatenację stanów granicznych i uwagową agregację wnętrza, po czym projekcja sprowadza wymiar z powrotem do 768. DAE ma warstwy 768→384→128→384→768, GELU, layer normalization i dropout. W pretrainingu 15% wymiarów jest maskowanych, dodaje się szum Gaussa o małej wariancji, a w 10% przykładów zeruje się cechy morfosyntaktyczne. Korpus domenowy nie wymaga etykiet koreferencji.

Po pretrainingu koder \(z_i\in\mathbb{R}^{128}\) zasila lekką głowicę par \(q_{ij}=[z_i;z_j;z_i\odot z_j;|z_i-z_j|;f_{ij}]\), gdzie \(f_{ij}\) zawiera cechy odległości i zgodności. Cel wspólny ma postać
\[
\mathcal L_C=\mathcal L_{\mathrm{antecedent}}
+\lambda_{\mathrm{rec}}\|x-\hat x\|_1
+\lambda_{\mathrm{cos}}(1-\cos(x,\hat x)).
\]
Najpierw uczy się samej rekonstrukcji, następnie głowicy na PCC/CorefUD-PL, a na końcu opcjonalnie dostraja koder z małym współczynnikiem uczenia.

DAE ma około 0,69 mln parametrów, a głowica mniej niż 1 mln; budżet całego nowego modułu wynosi mniej niż 2 mln trenowanych parametrów. Prekomputowane embeddingi pozwalają uczyć DAE w mniej niż 8 GB, zaś wspólne strojenie z HerBERT przy oknie 512, batchu 2 i akumulacji gradientu szacuje się na 12--18 GB. Główne ryzyka to rekonstrukcja cech nieistotnych dla koreferencji, utrata informacji w 128 wymiarach, przesunięcie między PCC i orzeczeniami oraz uczenie się artefaktów anonimizacji. Kontrolami są wariant bez DAE, losowo inicjalizowany koder tej samej wielkości i DAE pretrenowany wyłącznie na PCC.

## 5. Wariant D — selektywna hybryda z LLM

Wariant D nie jest osobnym detektorem, lecz warstwą decyzji nad wariantem C. Dla każdej anafory oblicza się margines między dwoma najlepszymi poprzednikami i błąd rekonstrukcji DAE. LLM otrzymuje tylko pary z marginesem poniżej \(\delta\) lub błędem powyżej percentyla \(p\), maksymalnie 16 kandydatów na dokument, wraz z dwoma zdaniami kontekstu i listą istniejących identyfikatorów. Odpowiedź ma zamknięty schemat JSON: identyfikator anafory, identyfikator poprzednika lub null, pewność i krótka etykieta powodu.

Nie trenuje się dodatkowych parametrów LLM. Lokalny model 8B w FP16 zajmowałby około 16 GB tylko na wagi i zostawiał zbyt mały margines na cache; dlatego domyślnym eksperymentem jest wersjonowane API albo osobny proces 4-bit, nigdy wspólne uczenie na tej samej karcie. Funkcja decyzyjna akceptuje LLM wyłącznie przy zgodnym schemacie i pewności powyżej progu z dev; w przeciwnym razie zachowuje predykcję specjalisty. Ryzyka to zmienność usługi, koszt, wyciek danych, halucynowane identyfikatory i brak deterministyczności. Do zewnętrznej usługi wolno wysłać tylko tekst po ponownym audycie PII albo syntetyczne przykłady; pełny LLM-only pozostaje baseline'em kosztowym.

## 6. Odrzucony wariant B — samodzielne klastrowanie latentne

Odrzucono model, w którym zwykły AE kompresuje wzmianki, a DEC/IDEC samodzielnie tworzy klastry. Liczba encji \(K\) zmienia się dla każdego dokumentu, małe klastry i singletony dominują, a geometryczna bliskość ról takich jak „powód” w różnych sprawach nie oznacza tożsamości. Stałe centroidy między dokumentami powodowałyby przeciek semantyki klas zamiast identyfikacji lokalnych encji, natomiast dobieranie \(K\) ze złota byłoby przeciekiem etykiety. Kompresję zachowano w wariancie C, ale decyzję o poprzedniku uczy się nadzorowanie i dopiero potem domyka przechodnio do partycji.

## 7. Uzasadnienie wyboru względem celu pracy

Cel z karty pracy akcentuje żmudną adaptację metod statystycznych i LLM do konkretnej dziedziny. Wariant C odpowiada temu bezpośrednio: około 0,69 mln parametrów DAE można pretrenować na jawnie licencjonowanych, nieanotowanych tekstach prawnych, pozostawiając kosztowny enkoder zamrożony. Wariant A bada analogię do segmentacji obrazów i szeregów wskazaną w karcie, ale przenosi ją na mniejszą macierz wzmianek. Wariant D sprawdza połączenie obu podejść, ograniczając LLM do przypadków niepewnych i mierząc oszczędność tokenów.

Najważniejszym kryterium nie jest maksymalny F1 bez ograniczeń, lecz przyrost jakości na jednostkę trenowanych parametrów, GPU-hour i tokenów inferencji. Każdy wariant ma architektonicznie porównywalną kontrolę bez AE, wspólne splity i ten sam scorer. Jeżeli DAE nie poprawi jakości lub hybryda nie zmniejszy kosztu, odpowiednie pytanie badawcze zostanie rozstrzygnięte negatywnie.
