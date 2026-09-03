# Jak komputer uczy się rozumieć, kto jest kim w tekście prawnym

Szczegółowe, lecz przystępne objaśnienie pracy magisterskiej z repozytorium
`mg-koreferencja-autokoder`, według stanu z commita `f02ed6bbecfa`.

Tekst nie jest mechanicznym odczytaniem pracy. Wyjaśnia jej tok rozumowania,
wyniki i ograniczenia prostym językiem. W miejscach, w których niezależna
weryfikacja wykazała problem, wyraźnie oddziela wynik raportowany od wyniku
potwierdzonego.

## 1. Po co w ogóle uczyć komputer koreferencji

Wyobraź sobie uzasadnienie wyroku. Na początku czytamy: „Jan Kowalski wniósł
pozew przeciwko spółce Alfa”. Kilka akapitów dalej pojawia się „powód”. Potem
„mężczyzna”, „on”, „J. K.” albo po prostu czasownik „twierdził”, w którym podmiot
nie został zapisany osobnym słowem. Człowiek zwykle rozumie, że wszystkie te
wyrażenia mogą wskazywać na Jana Kowalskiego. Komputer widzi jednak różne ciągi
znaków. Musi dopiero nauczyć się, że te fragmenty mogą mówić o tej samej osobie.

Takie zjawisko nazywa się koreferencją. „Ko” oznacza wspólność, a „referencja”
oznacza odnoszenie się do czegoś. Dwa wyrażenia są koreferencyjne, gdy odnoszą
się do tego samego obiektu w opisywanym świecie. Tym obiektem może być człowiek,
firma, sąd, umowa, nieruchomość, przepis, zdarzenie albo nawet cała wcześniejsza
sytuacja. Wszystkie wzmianki o jednym obiekcie tworzą łańcuch koreferencyjny.

Rozpoznanie takich łańcuchów jest ważne nie tylko dla wygody czytania. Bez nich
program analizujący dokument nie wie, że „pozwany”, „pracodawca” i „spółka” to w
danym miejscu ta sama strona postępowania. Nie potrafi zebrać wszystkich faktów
dotyczących jednej osoby. Może też przypisać czynność niewłaściwej stronie. Jeśli
chcemy budować grafy powiązań, wyszukiwać argumenty, streszczać akta, kontrolować
anonimizację albo odpowiadać na pytania o sprawę, koreferencja staje się jednym
z fundamentów całego systemu.

Praca, którą wyjaśniamy, pyta, czy do tego celu można wykorzystać pomysł znany z
przetwarzania obrazów: sieć U-Net oraz uczenie rekonstrukcyjne przypominające
autokoder. Główna intuicja brzmi następująco. Zamiast rozpatrywać każde słowo
oddzielnie, można utworzyć kwadratową mapę relacji między wszystkimi parami słów.
Taka mapa przypomina wielokanałowy obraz. Skoro U-Net potrafi znajdować obszary
na obrazie, być może potrafi też znajdować regularne obszary na mapie
koreferencji.

To podejście nazwano CorefSeg-AE. „Coref” oznacza koreferencję, „Seg” oznacza
segmentację, a „AE” odwołuje się do autokodera. Praca jest przede wszystkim
dowodem wykonalności: sprawdza, czy taki pomysł da się zbudować, wytrenować na
zwykłym laptopie i zastosować do polskich tekstów. Nie jest jeszcze gotowym
systemem dla sądów. W dalszych rozdziałach spokojnie rozłożymy go na części.

## 2. Wzmianki, klastry i najważniejsze pułapki

Zacznijmy od języka używanego w badaniach. Wzmianka to konkretny fragment tekstu,
który wskazuje na jakiś obiekt. W zdaniu „powód podpisał umowę” mamy co najmniej
dwie wzmianki: „powód” oraz „umowę”. Jeśli później pojawi się „ten dokument”, to
może być kolejna wzmianka o tej samej umowie. Zbiór wzmianek odnoszących się do
jednego obiektu nazywamy klastrem albo łańcuchem koreferencyjnym.

System musi rozwiązać dwa różne problemy. Najpierw musi wykryć granice wzmianek,
czyli zdecydować, czy wzmianką jest samo słowo „umowa”, czy całe wyrażenie
„przedmiotowa umowa sprzedaży nieruchomości”. Potem musi ustalić, które wykryte
wzmianki należą do jednego klastra. Można świetnie grupować wzmianki, ale
wcześniej przeoczyć połowę z nich. Można też znaleźć wszystkie wzmianki, a potem
połączyć powoda z pozwanym. Dlatego wyniki wykrywania i grupowania powinny być
raportowane osobno.

Nie każde podobne wyrażenie jest koreferencją. „Sąd Rejonowy” i „Sąd Okręgowy”
są sądami, ale nie są tym samym sądem. „Umowa z 2020 roku” i „umowa z 2021 roku”
mogą należeć do tego samego typu dokumentu, lecz opisywać dwa różne obiekty.
Z drugiej strony wyrażenia zupełnie niepodobne powierzchniowo, takie jak
„Jan Kowalski”, „powód” i „ubezpieczony”, mogą wskazywać na tę samą osobę.

Szczególnym przypadkiem jest singleton, czyli obiekt wspomniany tylko raz. Nie ma
drugiej wzmianki, z którą można byłoby go połączyć, ale nadal jest oznaczoną
encją. W polskich danych CorefUD singletonów jest bardzo dużo. To ważne, ponieważ
system może uzyskać pozornie lepszy wynik, jeśli dobrze znajduje pojedyncze
wzmianki, nawet gdy słabo rozwiązuje właściwe łańcuchy. Różne scorery mogą
singletony uwzględniać albo usuwać. Wyniki mają sens tylko wtedy, gdy dokładnie
wiemy, jakie ustawienie zastosowano.

Są też przypadki trudniejsze od zwykłego rzeczownika lub zaimka. Wzmianki mogą
się zagnieżdżać. Wyrażenie „prezes spółki Alfa” zawiera wzmiankę o prezesie oraz
wzmiankę o spółce. Mogą występować elementy nieciągłe albo tak zwane zaimki
zerowe, niewidoczne jako osobne słowo. W zdaniu „Sąd zbadał dowody i uznał, że...”
wykonawca czynności „uznał” jest domyślny. Polski pozwala pomijać podmiot znacznie
częściej niż angielski.

Te przykłady prowadzą do istotnej zasady: reprezentacja wybrana przez model nie
jest neutralna. Jeśli system potrafi narysować tylko jeden ciągły odcinek dla
każdej wzmianki, część zjawisk z bogatego standardu CorefUD będzie dla niego
niemożliwa do zapisania. Wtedy nie wystarczy powiedzieć, że model popełnił błąd.
Trzeba sprawdzić, czy odpowiedź w ogóle mieściła się w języku jego wyjścia.

## 3. Dlaczego język prawny i prawniczy jest wyjątkowo trudny

W codziennej rozmowie często powtarzamy imiona albo używamy prostych zaimków.
Dokument prawny posługuje się rolami, definicjami i odesłaniami. Jedna osoba może
być opisana jako „powód”, „ubezpieczony”, „pracownik”, „skarżący”, „wnioskodawca”
albo inicjały. Każde określenie podkreśla inny aspekt tej samej osoby. Model musi
rozumieć nie tylko gramatykę, ale również strukturę sprawy.

Najbardziej niebezpieczny błąd polega na połączeniu dwóch różnych uczestników,
którzy pełnią podobne role. „Powód” i „pozwany” często występują blisko siebie,
mają podobną formę gramatyczną i dotyczą tego samego sporu, lecz zwykle wskazują
na różne osoby. Model może prawidłowo zauważyć, że oba słowa opisują uczestników
postępowania, a jednocześnie całkowicie pomylić ich tożsamość. W zastosowaniu
praktycznym taki błąd jest groźniejszy niż brak połączenia.

Kolejnym utrudnieniem są definicje. Umowa może wprowadzić formułę: „Jan Kowalski,
zwany dalej Wykonawcą”. Od tej chwili wyraz „Wykonawca” ma lokalne, precyzyjne
znaczenie. W innym dokumencie ten sam wyraz będzie wskazywał na kogoś zupełnie
innego. System nie może nauczyć się jednej stałej odpowiedzi ze słownika. Musi
odnaleźć definicję wewnątrz aktualnego dokumentu i pamiętać ją wiele akapitów
później.

Anonimizacja dodatkowo usuwa wskazówki. Nazwisko może zostać zastąpione przez
„J. K.”, nazwę przedsiębiorstwa przez „(...) spółkę akcyjną”, a adres przez
ogólny symbol. Dwie osoby mogą mieć te same inicjały. Czasami sposób anonimizacji
zmienia się w obrębie dokumentu. Model językowy, który normalnie korzysta z
informacji zawartej w nazwie własnej, otrzymuje bardzo mało danych.

Dokumenty są także długie. Wprowadzenie uczestnika może znajdować się na
pierwszej stronie, a kolejne odwołanie w końcowych wnioskach. Typowy model
transformerowy ma ograniczone okno kontekstu. CorefSeg-AE tnie tekst na mniejsze,
częściowo nakładające się okna. To oszczędza pamięć, ale tworzy nowy problem:
jak połączyć klaster z pierwszego okna z klastrem z dziesiątego okna?

Język prawniczy lubi też skróty myślowe: „Sąd zważył”, „organ wskazał”, „strona
podniosła”, „powyższe stanowisko”, „wspomniana okoliczność”, „niniejszy przepis”.
Odwołanie może dotyczyć nie rzeczownika, lecz całego wcześniejszego zdarzenia
albo argumentu. Granica między koreferencją, anaforą i szerszą relacją znaczeniową
nie zawsze jest oczywista nawet dla człowieka. Dlatego praca słusznie zakłada, że
do rzetelnego testu prawnego potrzebna jest instrukcja anotacji i ręcznie
sprawdzony zbiór, a nie wyłącznie automatyczne etykiety.

## 4. Jak wcześniej rozwiązywano koreferencję

Pierwsze systemy opierały się głównie na regułach. Program znajdował nazwy,
zaimki i grupy rzeczownikowe, a następnie łączył je na podstawie odległości,
rodzaju gramatycznego, liczby i podobieństwa słów. Taki model jest tani i łatwy
do wyjaśnienia. W prostym zdaniu „Anna weszła. Ona usiadła” reguła zgodności
rodzaju działa dobrze. W dokumencie prawnym szybko jednak napotyka wyjątki.
„Spółka” ma rodzaj żeński, ale można o niej dalej pisać jako o „pozwanym”, jeśli
gramatyka zdania lub konwencja prawna prowadzi do innej formy.

Później pojawiły się modele statystyczne, które oceniały pary wzmianek. Dla każdej
pary program wyliczał cechy: odległość, zgodność form, typ nazwy, pozycję w
zdaniu. Klasyfikator odpowiadał, czy dwie wzmianki należy połączyć. Następnie
trzeba było z par zbudować spójne klastry. Relacja koreferencji jest bowiem
przechodnia. Jeśli A oznacza to samo co B, a B to samo co C, to A, B i C powinny
znaleźć się w jednym łańcuchu.

Współczesne systemy używają głębokich modeli językowych. Transformer, taki jak
BERT albo polski HerBERT, tworzy dla każdego tokenu wektor zależny od kontekstu.
Słowo „zamek” otrzyma inną reprezentację w zdaniu o drzwiach i inną w zdaniu o
budowli. System może dzięki temu nauczyć się subtelniejszych relacji niż prosty
słownik. Najmocniejsze dedykowane modele rozpatrują możliwe spany, wybierają
poprzedniki albo przewidują całe klastry.

Duże modele generatywne potrafią rozwiązywać koreferencję po opisaniu zadania w
poleceniu. Są elastyczne i dobrze wykorzystują wiedzę językową, ale mają również
ograniczenia. Wynik może być niestabilny, format odpowiedzi może się zmienić, a
wysłanie dokumentów do zewnętrznej usługi może być niedopuszczalne. Długie teksty
kosztują więcej, a dokładne wskazanie granic wszystkich wzmianek jest dla modelu
konwersacyjnego trudniejsze niż udzielenie ogólnej odpowiedzi.

Praca proponuje inną drogę: zachować zamrożony model HerBERT jako źródło wiedzy
o polszczyźnie, a nauczyć znacznie mniejszy moduł rozwiązujący właściwe zadanie.
Ma to ograniczyć koszt i pozwolić na lokalne przetwarzanie danych. Zaprojektowano
również wariant hybrydowy, w którym duży model pomaga tylko przy przypadkach
niepewnych. Ten wariant nie został jednak rzetelnie zmierzony, więc pozostaje
pomysłem na dalszy eksperyment, a nie potwierdzonym wynikiem pracy.

## 5. Czym jest autokoder i dlaczego U-Net pasuje do mapy relacji

Klasyczny autokoder otrzymuje dane, ściska je do mniejszej reprezentacji, a potem
próbuje odtworzyć wejście. Pierwsza część to enkoder, druga to dekoder. Jeżeli
sieć ma ograniczoną pojemność albo wejście zostanie częściowo zasłonięte, nie
może po prostu skopiować każdej liczby. Musi uchwycić regularności. Autokoder
odszumiający dostaje uszkodzoną wersję danych, lecz jako cel ma wersję pełną.

U-Net jest architekturą typu enkoder-dekoder stworzoną do segmentacji obrazów.
Enkoder stopniowo zmniejsza rozdzielczość i zbiera szerszy kontekst. Dekoder
ponownie zwiększa rozdzielczość i wskazuje klasę każdego piksela. Charakterystyczne
są połączenia skrótowe między odpowiadającymi sobie poziomami. Dzięki nim sieć
łączy ogólny obraz z dokładnym położeniem granic. W obrazie medycznym może
rozpoznać, gdzie znajduje się zmiana, a jednocześnie precyzyjnie narysować jej
kształt.

W tej pracy „pikselem” nie jest fragment zdjęcia. Wiersz mapy oznacza jeden token
tekstu, a kolumna drugi token tego samego tekstu. Pole o współrzędnych pięć i
dwieście opisuje relację tokenu piątego z tokenem dwusetnym. Jeżeli oba należą do
wzmianek wskazujących ten sam obiekt, odpowiedź docelowa w tym polu jest dodatnia.
Cała macierz ma więc regularne bloki. Wzmianka wielowyrazowa tworzy odcinek na
przekątnej, a dwie koreferencyjne wzmianki tworzą prostokąt poza przekątną.

To podobieństwo do obrazu jest atrakcyjne. U-Net może analizować lokalne wzory,
łączyć informacje z różnych skal i zwracać mapę tej samej wielkości. Trzeba jednak
pamiętać, że analogia ma granice. Kolejność tokenów jest ważna, macierz jest
symetryczna, a etykiety muszą ostatecznie tworzyć relację przechodnią. Zwykła
segmentacja obrazu nie gwarantuje żadnej z tych własności. System potrzebuje więc
dodatkowego dekodowania i reguł tworzenia klastrów.

Warto też odróżnić ten model od wariacyjnego autokodera, czyli VAE. VAE uczy
rozkładu w przestrzeni ukrytej i często wykorzystuje tak zwaną sztuczkę
reparametryzacji: losuje szum i przekształca go za pomocą średniej oraz odchylenia.
CorefSeg-AE nie jest takim VAE i nie potrzebuje sztuczki reparametryzacji. Nazwa
„AE” odnosi się tutaj głównie do rekonstrukcyjnego pretreningu i budowy
enkoder-dekoder U-Netu, a nie do probabilistycznego modelu generatywnego.

## 6. Jak dokładnie działa CorefSeg-AE

Wejściowy dokument jest dzielony na okna. W wykonanym eksperymencie długość okna
wynosi 256 tokenów, a kolejne okna częściowo się nakładają. Krótszy tekst jest
dopełniany, a dłuższy przechodzi przez model fragment po fragmencie. Takie
ograniczenie wynika zarówno z maksymalnego kontekstu encodera, jak i z pamięci
potrzebnej na kwadratową macierz.

Każde okno trafia do polskiego modelu HerBERT. HerBERT był wcześniej trenowany
na dużych zbiorach polskich tekstów. Zwraca dla tokenu wektor 768 liczb. W tej
pracy jego parametry pozostają zamrożone. To znaczy, że podczas treningu
koreferencji nie aktualizuje się całego HerBERT-a. Oszczędza to pamięć i czas,
ale ogranicza możliwość głębokiego dostosowania encodera do języka prawnego.

Następnie liniowa projekcja zmniejsza wymiar 768 do 32. Dla każdej pary tokenów
budowane są cztery składniki: wektor pierwszego tokenu, wektor drugiego tokenu,
ich różnica oraz iloczyn element po elemencie. Cztery razy 32 daje 128 kanałów.
W ten sposób powstaje tensor o kształcie zbliżonym do 128 na 256 na 256. Można
myśleć o nim jak o obrazie 256 na 256, który zamiast kanałów czerwonego, zielonego
i niebieskiego ma 128 kanałów opisujących znaczenie pary słów.

Tensor przechodzi przez trójpoziomowy U-Net z bazową liczbą 32 kanałów. Sieć
zwraca jedną wartość dla każdego pola. Po funkcji sigmoid wartość staje się
prawdopodobieństwem. Domyślnie pole większe niż 0,5 uznaje się za dodatnie.

Dekoder najpierw bada przekątną. Kolejne dodatnie pola na przekątnej są łączone
w ciągłą wzmiankę. Potem dla każdej pary wykrytych wzmianek bierze odpowiadający
im prostokąt w macierzy. Jeśli średnie prawdopodobieństwo w prostokącie przekracza
próg, wzmianki zostają połączone. Algorytm union-find wymusza przechodniość:
jeżeli pierwsza wzmianka łączy się z drugą, a druga z trzecią, wszystkie lądują
w tym samym klastrze.

Po przetworzeniu okien trzeba scalić wyniki dla całego dokumentu. Obecna metoda
łączy klastry z dwóch okien, gdy zawierają wzmiankę o dokładnie takich samych
granicach w obszarze nakładania. Jest to proste i szybkie, lecz podatne na
rozcięcie łańcucha. Jeśli jedno okno wykryje „przedmiotowa umowa”, a drugie samo
„umowa”, granice nie są identyczne i połączenie może nie powstać.

Model jest trenowany za pomocą połączenia straty binarnej i straty Dice. Zwykła
strata binarna ocenia każde pole. Dice patrzy na nakładanie się całych obszarów
i pomaga przy ogromnej nierównowadze klas. Większość par tokenów nie jest
koreferencyjna. Gdyby sieć wszędzie przewidywała zero, miałaby wiele poprawnych
pól, lecz nie rozwiązywałaby zadania. Składnik Dice zwiększa znaczenie rzadkich
dodatnich obszarów.

## 7. Na czym polega prawny pretrening DAE

Najciekawsze pytanie pracy dotyczy adaptacji domenowej bez ręcznych etykiet. Dane
z koreferencją są drogie, ale nieoznaczonych orzeczeń sądowych jest dużo. Można
je pobrać z publicznej bazy SAOS. Czy model może oswoić się z ich strukturą,
słownictwem i typowymi zależnościami, zanim zobaczy złote klastry?

Wariant DAE, czyli denoising autoencoder, działa następująco. HerBERT tworzy
wektory, projekcja i konstruktor par tworzą tensor token-token. Losowe kwadratowe
bloki tensora zostają wyzerowane. U-Net otrzymuje uszkodzoną mapę i ma odtworzyć
wartości w zasłoniętych miejscach. Do tego nie potrzeba żadnej ręcznie oznaczonej
koreferencji. Wystarczy tekst prawny.

Intuicja jest rozsądna: aby uzupełnić brakujący obszar, sieć powinna rozpoznawać
regularności mapy i korzystać z otoczenia. Po takim pretreningu jej wagi są
punktem startowym do właściwego uczenia na PCC. Eksperyment użył 150 orzeczeń
SAOS i trwał około pięciu minut na karcie graficznej laptopa. Następnie model był
dostrajany z etykietami koreferencji.

Trzeba jednak bardzo dokładnie powiedzieć, co jest rekonstruowane. Cel nie jest
złotą mapą koreferencji ani oryginalnym tekstem. Jest nim wielokanałowy tensor
par utworzony przez projekcję 768 do 32. W aktualnej implementacji projekcja jest
świeżo, losowo zainicjalizowana i podczas pretreningu znajduje się za operacją
odcinającą gradient. U-Net uczy się zatem rekonstruować stabilny, ale arbitralny
losowy obraz cech. Może to nadal pełnić funkcję regularizacji, jednak nie jest
oczywiste, że przenosi najlepszą możliwą wiedzę o prawie.

Dlatego potrzebna jest ablacja. W jednym wariancie można rekonstruować
znormalizowane reprezentacje HerBERT. W drugim użyć PCA, czyli stałego rzutowania
zachowującego najważniejsze kierunki danych. W trzecim pozwolić projekcji się
uczyć, ale cel generować przez wolniej aktualizowaną gałąź nauczyciela. Dopiero
porównanie pokaże, czy poprawa pochodzi z prawnego tekstu, ogólnej regularizacji,
czy przypadkowego punktu startu.

To nadal nie jest VAE. Nie ma rozkładu normalnego, parametrów średniej i wariancji
ani losowania wektora ukrytego przez sztuczkę reparametryzacji. Jest to
odszumiające zadanie rekonstrukcyjne na cechach par tokenów. Taki wybór ma sens
dla tekstu, lecz powinien być nazwany i opisany precyzyjnie.

## 8. Jakich danych użyto i czego w nich brakuje

Podstawowym źródłem złotych etykiet jest polska część CorefUD, wywodząca się z
Polskiego Korpusu Koreferencyjnego. Zawiera teksty ogólne, między innymi prasę,
literaturę i rozmowy. W treningu pełnej wersji wykorzystano ponad tysiąc
dokumentów. Ewaluację wykonano na pierwszych 60 dokumentach części dev. To
wystarcza do eksperymentu wstępnego, ale nie do ostatecznego porównania systemów.

CorefUD zapisuje tokeny, zdania, informacje składniowe i adnotacje encji w
formacie CoNLL-U. Schemat pozwala opisywać złożone przypadki, w tym singletony i
pewne specjalne rodzaje wzmianek. Model macierzowy upraszcza część tego bogactwa.
Warto więc policzyć, ile złotych przypadków jest reprezentowalnych w jego formacie
wyjściowym, a ile zostaje utraconych jeszcze przed treningiem.

Drugim źródłem są nieanotowane orzeczenia SAOS. Część wykorzystano do pretreningu.
Z 400 różnorodnych orzeczeń powstał również zbiór srebrny. „Srebrny” oznacza, że
etykiety stworzył model, a nie człowiek. Zbiór ma około 987 tysięcy tokenów,
97 tysięcy encji i 112 tysięcy wzmianek według automatycznej anotacji. Dominują
singletony. Dokumenty są długie i dobrze reprezentują język orzecznictwa, więc
sam materiał tekstowy jest bardzo wartościowy.

Jakość etykiet jest jednak ograniczona jakością nauczyciela. Główną anotację 400
dokumentów wykonał własny model, którego mention F1 na ogólnym PCC wynosi około
0,51. To sugeruje, że wiele wzmianek może być pominiętych lub mieć niewłaściwe
granice. Przejście z języka ogólnego do prawnego może dodatkowo zwiększyć liczbę
błędów. Taki korpus nadaje się do eksperymentu ze słabym nadzorem, ale nie jest
złotym standardem.

CorPipe, silny system dedykowany koreferencji, uruchomiono dla 40 orzeczeń jako
punkt porównawczy. To dobry pilot, lecz zbyt mały zakres, aby oczyścić wszystkie
400 dokumentów. Najlepszym kolejnym krokiem jest zapisanie predykcji co najmniej
dwóch niezależnych nauczycieli dla całego zbioru. Miejsca zgodne można traktować
jako bardziej wiarygodne, a rozbieżności skierować do ręcznej kontroli.

Praca zawiera protokół ręcznej anotacji tekstów prawnych. To bardzo ważny element,
ponieważ wyjaśnia zasady dla ról procesowych, definicji, inicjałów i odesłań.
Sama anotacja nie została jednak jeszcze wykonana. Bez ręcznie sprawdzonego
zbioru prawnego można badać transfer i analizować przykłady, ale nie można
rzetelnie podać końcowej jakości systemu w docelowej domenie.

## 9. Jak mierzy się koreferencję i dlaczego jedna liczba nie wystarcza

W klasyfikacji obrazów często pytamy po prostu, jaki procent przykładów został
rozpoznany poprawnie. Koreferencja jest bardziej złożona, bo odpowiedzią jest
podział wzmianek na klastry. Jeden system może rozbić duży złoty klaster na wiele
małych. Inny może połączyć kilka poprawnych klastrów w jeden ogromny. Oba się
mylą, lecz w różny sposób.

Metryka MUC skupia się na połączeniach potrzebnych do utworzenia klastra. Jest
stosunkowo łagodna wobec pewnych błędów granic i słabo opisuje singletony.
B-sześcian, zapisywane B do trzeciej, liczy precyzję i pełność z perspektywy
każdej wzmianki. CEAF szuka najlepszego dopasowania między klastrami złotymi i
przewidzianymi. Standardowy CoNLL F1 jest średnią wyników F1 dla MUC, B-sześcian
i CEAF-e. LEA dodatkowo waży encje i ich połączenia.

Precyzja odpowiada na pytanie: jeśli model coś połączył, jak często miał rację?
Pełność pyta: ile z prawidłowych połączeń udało się odnaleźć? System ostrożny może
mieć wysoką precyzję, ale niską pełność. W prawie ostrożność bywa pożądana, lecz
nie wolno automatycznie uznać, że każdy brak jest bezpieczny. Jeśli narzędzie ma
kontrolować anonimizację, przeoczona wzmianka może ujawnić dane osobowe.

Osobno mierzy się mention precision, recall i F1. Jeżeli granice wzmianek są
podane ze złotego standardu, mention F1 wynosi z definicji jeden i wynik opisuje
głównie grupowanie. Jeżeli model sam wykrywa wzmianki, końcowy CoNLL F1 zawiera
oba rodzaje trudności. Dlatego porównanie systemu ze złotymi wzmiankami z systemem
end-to-end bez wyraźnego oznaczenia byłoby niesprawiedliwe.

Równie ważny jest oficjalny scorer. Własna implementacja metryk może służyć do
szybkiego treningu, ale wynik końcowy powinien zostać potwierdzony referencyjnym
narzędziem na plikach w standardowym formacie. Pozwala to wykryć różnice w
obsłudze singletonów, granic, pustych węzłów i identyfikatorów dokumentów.

Praca używa również bootstrapu dokumentowego. Losuje z powtórzeniami dokumenty
i obserwuje, jak zmienia się różnica między systemami. To rozsądny sposób oceny
niepewności wynikającej z doboru tekstów. Nie zastępuje jednak wielu treningów.
Jeśli model trenowano tylko raz, nie wiemy, jak bardzo wynik zależy od losowej
inicjalizacji, kolejności batchy i dropout. Potrzebne są oba poziomy analizy.

## 10. Co pokazały wykonane eksperymenty

Eksperymenty uruchomiono na laptopie z kartą graficzną o czterech gigabajtach
pamięci. Z tego powodu zastosowano mniejszy U-Net, okna długości 256 i ograniczoną
liczbę przebiegów. Jest to ważny sukces praktyczny: pomysł da się rzeczywiście
uruchomić na dostępnym sprzęcie. Nie należy jednak mylić dowodu wykonalności z
ostatecznym wynikiem naukowym.

Model trenowany na 300 dokumentach uzyskał według własnych metryk około 0,218
CoNLL F1. Po zwiększeniu treningu do pełnego dostępnego zbioru wynik wzrósł do
około 0,375. To duża różnica i sensowny sygnał: model korzysta z większej ilości
danych, a krzywa nie wygląda na nasyconą. Prosty baseline regułowy osiągał wynik
wyraźnie niższy.

Po pretreningu DAE na 150 orzeczeniach SAOS i dalszym treningu nadzorowanym wynik
własny wzrósł z około 0,375 do około 0,385. Różnica jest niewielka, lecz spójna z
hipotezą, że rekonstrukcyjny punkt startu pomaga. W raporcie bootstrap dla 60
dokumentów dał przedział różnicy powyżej zera i wartość p równą 0,001.

Te liczby wymagają dwóch zastrzeżeń. Po pierwsze, funkcja opisana w kodzie jako
test dwustronny w rzeczywistości liczy jeden ogon. Proste podwojenie dałoby około
0,002, więc formalny wniosek prawdopodobnie by się nie zmienił, ale implementację
trzeba poprawić. Po drugie, oba modele wytrenowano jednym ziarnem. Bootstrap po
dokumentach nie pokazuje wariancji treningowej. Poprawę należy odtworzyć dla
kilku ziaren.

Profil błędów pokazuje stosunkowo wysoką precyzję i niższą pełność. Głównym
wąskim gardłem jest wykrywanie wzmianek; mention F1 wariantu DAE wynosi około
0,51. To oznacza, że model pomija znaczną część elementów, zanim zacznie je
grupować. Rozwój samego dekodera klastrów nie rozwiąże więc całego problemu.

CorPipe na tych samych pierwszych 60 dokumentach uzyskał we własnej ścieżce
pomiarowej około 0,740 CoNLL F1 z singletonami, a około 0,641 po ich usunięciu.
Pokazuje to, że silny system dedykowany nadal ma dużą przewagę. Jednocześnie
porównanie nie jest jeszcze w pełni referencyjne, ponieważ wszystkie systemy
powinny zostać przepuszczone przez identyczny oficjalny scorer i te same zasady
dotyczące wzmianek.

Najuczciwszy wniosek z obecnych eksperymentów brzmi zatem: macierzowy U-Net uczy
się sygnału koreferencji, większy trening wyraźnie pomaga, a domenowy DAE daje
obiecującą małą poprawę. Nie mamy jeszcze wystarczających podstaw, aby podać
ostateczną jakość na tekstach prawnych albo twierdzić, że różnica DAE jest
stabilna między treningami.

## 11. Co ujawniła próba użycia oficjalnego scorera

Niezależny przegląd uruchomił oficjalny scorer CorefUD na zapisanych predykcjach
pełnego U-Netu oraz wariantu DAE. Celem nie było zmienianie wyników, lecz
sprawdzenie, czy standardowy program potrafi odczytać eksport.

Pierwszy błąd dotyczył identyfikatorów zdań. Writer wkładał do sent id pełną
ścieżkę dokumentu zawierającą ukośniki. Biblioteka UDAPI potraktowała fragment po
ukośniku jako specjalną nazwę strefy i odrzuciła plik. W tymczasowej kopii
zastąpiono identyfikatory prostymi, bezpiecznymi numerami.

Drugi błąd wynikał z braku nagłówka global Entity, który opisuje pola anotacji
encji. Po dodaniu nagłówka tylko do kopii kontrolnej scorer rozpoczął dalsze
czytanie danych.

Trzeci problem okazał się poważniejszy. Program wykrył wzmiankę otwartą w jednym
zdaniu i zamkniętą w kolejnym. Zgłosił błąd „Cross-sentence mentions not supported”.
Przyczyną jest sposób działania writera: najpierw buduje znaczniki dla całego
dokumentu, a dopiero potem zapisuje zdania. Jeśli span przekracza granicę zdania,
powstaje konstrukcja nieakceptowana przez scorer. Ten sam problem wystąpił dla
predykcji zwykłego U-Netu i DAE.

Oznacza to, że wartości 0,375 i 0,385 są obecnie wynikami własnej implementacji,
a nie potwierdzonymi oficjalnymi wynikami CorefUD. Nie znaczy to automatycznie,
że są bezwartościowe albo fałszywe. Oznacza, że trzeba naprawić warstwę eksportu
i przeliczyć tabelę przed cytowaniem jej jako porównywalnej z literaturą.

Poprawny writer powinien zachować oryginalne tokeny, granice zdań i, jeśli to
możliwe, strukturę CoNLL-U zamiast budować sztuczne zależności root i dep. Musi
generować bezpieczne identyfikatory, dodawać schemat Entity i jasno obsługiwać
span przecinający zdanie. Najlepszym zabezpieczeniem będzie test integracyjny,
który po każdym eksporcie rzeczywiście uruchamia oficjalny scorer i oczekuje kodu
zakończenia zero.

To dobry przykład różnicy między testem jednostkowym a integracyjnym. Wszystkie
cztery testy repozytorium przechodzą. Sprawdzają parser, windowing, dekodowanie,
metryki i uczenie na małych danych. Żaden nie pyta jednak zewnętrznego narzędzia,
czy końcowy plik jest zgodny ze standardem. Kod może więc działać poprawnie w
środku, a zawieść na granicy systemu.

## 12. Jak rozumieć zbiór srebrny i porównanie z CorPipe

Zbiór srebrny to praktyczny kompromis. Ręczne oznaczenie prawie miliona tokenów
byłoby ogromną pracą. Model może wykonać pierwszy przebieg w kilka godzin, a
człowiek poprawia tylko wynik. Takie podejście jest powszechne, lecz wymaga
zachowania różnicy między trzema pojęciami: predykcją, srebrną etykietą i złotą
etykietą.

Predykcja to zwykła odpowiedź modelu. Staje się srebrem, kiedy świadomie używamy
jej jako przybliżonej etykiety do treningu lub korekty. Złotem jest dopiero wynik
sprawdzony według ustalonej instrukcji przez człowieka, najlepiej z kontrolą
zgodności co najmniej dwóch anotatorów. Srebro może pomóc modelowi, ale nie może
samo oceniać modelu, który je wytworzył.

W repozytorium własny model oznaczył wszystkie 400 orzeczeń. CorPipe oznaczył 40
z nich. Duży udział singletonów i różnice w wykrywaniu wzmianek sprawiają, że
prosta liczba zgodności jest trudna do interpretacji. Dwa systemy mogą być zgodne,
bo oba przeoczyły to samo. Mogą też nie zgadzać się, choć jeden z nich ma rację.
Zgodność nie jest więc dokładnością.

Lepszy proces wykorzystuje kilka sygnałów. CorPipe, własny U-Net i ewentualnie
Stanza zapisują niezależne warstwy. Dla identycznych spanów można porównać pary i
klastry. Przykłady o wysokiej zgodności otrzymują większą wagę treningową.
Rozbieżności trafiają do plików review, uporządkowanych według niepewności,
długości łańcucha, typu roli prawnej i źródła dokumentu.

Do końcowej ewaluacji warto wybrać 40 do 80 dokumentów w sposób warstwowy. Próba
powinna obejmować różne sądy, lata, długości i typy spraw. Przynajmniej część
powinna zostać oznaczona niezależnie przez dwie osoby. Nie chodzi o ręczne
oznaczenie wszystkiego, lecz o mały, wiarygodny termometr, którym można mierzyć
duży srebrny zbiór.

Połączenie danych z obu projektów daje ciekawą możliwość. `mg2` ma 400 aktów
Dz.U. i M.P., natomiast drugi projekt ma 400 orzeczeń SAOS. To dwa różne gatunki.
Akt normatywny opisuje reguły, organy, obowiązki i definicje. Orzeczenie opisuje
uczestników, materiał dowodowy, tok sprawy i argumentację. Nie powinno się ich
wrzucać do jednego wyniku bez rozróżnienia. Można natomiast trenować na obu i
raportować transfer osobno dla legislacji oraz orzecznictwa.

## 13. Najważniejsze ograniczenia architektury i kodu

Pierwszym ograniczeniem jest koszt kwadratowy. Dla 256 tokenów mamy ponad 65
tysięcy pól. Dla 512 tokenów już ponad 262 tysiące. Podwojenie długości powoduje
czterokrotnie większą mapę. Wielokanałowy tensor zużywa dużo pamięci, dlatego
długie dokumenty muszą być dzielone.

Drugim ograniczeniem jest binarna reprezentacja. Ciąg dodatnich pól na przekątnej
jest interpretowany jako jedna wzmianka. Jeśli dwie przylegające wzmianki należą
do tego samego klastra, mogą się zlać. Zagnieżdżone i nieciągłe wzmianki nie mają
jednoznacznego obrazu. Empty nodes używane dla wzmianek zerowych również wymagają
specjalnego traktowania, a nie zamiany na zwykłe tokeny.

Trzecim problemem jest cache embeddingów. Nazwa pliku zależy od identyfikatora
dokumentu, offsetu i długości okna, ale nie od tekstu, rewizji HerBERT-a ani
tokenizatora. Po zmianie danych program może bez ostrzeżenia wczytać stare
wektory. Klucz powinien zawierać skrót treści, nazwę i wersję modelu, parametry
tokenizacji oraz wersję potoku.

Czwarty problem dotyczy gradient accumulation. Optymalizator wykonuje krok po
określonej liczbie mini-batchy. Jeżeli na końcu epoki pozostanie niepełna grupa,
obecny kod nie wykonuje dla niej kroku. Część obliczonych gradientów przepada.
Naprawa jest niewielka, ale potrzebny jest test z liczbą batchy niepodzielną przez
wartość akumulacji.

Piątym ograniczeniem jest brak kompletnych checkpointów w repozytorium. Pliki
modeli są ignorowane, a zapis nie obejmuje pełnego stanu optymalizatora,
schedulera i skalera. Osoba klonująca projekt może uruchomić kod, lecz nie odtworzy
natychmiast głównych predykcji. Potrzebne są checkpointy w Git LFS albo wydaniu,
sumy kontrolne, rewizje danych i mechanizm wznowienia treningu.

Szóstym problemem jest stały próg 0,5. Prawdopodobieństwo sieci nie musi być
skalibrowane. Próg należy wybrać na wydzielonej części treningowej, zamrozić i
dopiero wtedy użyć na dev oraz teście. Strojenie progu bezpośrednio na zbiorze,
z którego raportujemy wynik, prowadziłoby do przecieku informacji.

Żaden z tych punktów nie przekreśla głównej idei. Pokazują raczej różnicę między
prototypem badawczym a eksperymentem gotowym do ostatecznej publikacji. Prototyp
odpowiada: „czy sygnał istnieje?”. Dojrzały eksperyment odpowiada: „jak duży jest
efekt, z jaką niepewnością i czy ktoś inny potrafi go odtworzyć?”.

## 14. Jak doprowadzić badanie do mocnego finału

Pierwszy krok to naprawa eksportu. Dopóki oficjalny scorer odrzuca pliki, nie ma
sensu rozszerzać głównej tabeli. Writer powinien przejść automatyczny test na
małym dokumencie zawierającym singleton, wzmiankę wielowyrazową, kilka zdań i
kilka klastrów. Następnie trzeba przeliczyć U-Net, DAE oraz CorPipe identycznym
narzędziem.

Drugi krok to wspólny protokół. Należy zamrozić listy dokumentów treningowych,
kalibracyjnych, dev i testowych. Wyniki trzeba podzielić na tor ze złotymi
wzmiankami oraz tor end-to-end. W obu przypadkach zachować te same ustawienia
singletonów. Próg wybierać tylko na kalibracji.

Trzeci krok to wiele ziaren. Pięć pełnych treningów bazowego U-Netu i pięć DAE
pozwoli policzyć średnią, odchylenie standardowe i sparowaną różnicę. Dokumentowy
bootstrap można następnie zastosować do predykcji każdego przebiegu albo użyć
hierarchicznej analizy uwzględniającej oba źródła losowości.

Czwarty krok to ablacja pretreningu. Trzeba porównać brak DAE, DAE na tekstach
ogólnych, DAE na SAOS oraz DAE na aktach prawnych. Do tego kilka celów
rekonstrukcyjnych: losowa projekcja, PCA, reprezentacje HerBERT i teacher EMA.
Wtedy będzie można odpowiedzieć, czy pomaga sama rekonstrukcja, ilość tekstu czy
rzeczywiście domena prawna.

Piąty krok to ręczny mini-złoty standard prawny. Nie musi obejmować 400 tekstów.
Starannie wybrane 40 do 80 dokumentów wystarczy, by odróżnić realny transfer od
ładnie wyglądającego przykładu. Warto raportować osobno orzeczenia oraz akty
normatywne, ponieważ wymagają innej wiedzy.

Szósty krok to analiza błędów według zjawisk prawnych. Zamiast podawać tylko
CoNLL F1, można policzyć jakość dla ról procesowych, definicji „zwany dalej”,
anonimizowanych inicjałów, odesłań do przepisów, długich odległości i wzmianek
zerowych. Taka analiza odpowie nie tylko, który model ma większą liczbę, ale też
dlaczego i w jakim zastosowaniu jest bezpieczniejszy.

Najlepszą strategią organizacyjną jest pozostawienie `mg2` jako głównego,
reprodukowalnego potoku oraz przeniesienie CorefSeg-AE jako dodatkowego wariantu.
Nie trzeba wybierać między projektami. Scorer par wzmianek może być mocnym
baseline'em, U-Net odważną architekturą eksperymentalną, CorPipe nauczycielem i
punktem odniesienia, a DAE metodą adaptacji. Wspólne dane i wspólny scorer
zamienią różne prototypy w jeden czytelny eksperyment.

## 15. Podsumowanie bez technicznego żargonu

Praca próbuje nauczyć komputer śledzenia bohaterów dokumentu prawnego. Komputer
ma zrozumieć, że nazwisko, rola procesowa, inicjały i zaimek mogą oznaczać tę samą
osobę. Zamiast rozwiązywać problem wyłącznie jako serię decyzji językowych,
zamienia relacje między słowami w mapę podobną do obrazu i przekazuje ją sieci
U-Net.

Pomysł jest twórczy i działa na tyle, aby model uczył się na rzeczywistych
polskich danych. Więcej danych wyraźnie poprawia wynik. Krótki pretrening na
nieoznaczonych orzeczeniach daje mały dodatkowy wzrost według metryk własnych.
Całość można uruchomić na laptopie, co wspiera tezę, że adaptacja nie zawsze musi
wymagać ogromnego modelu i kosztownej infrastruktury.

Jednocześnie nie mamy jeszcze gotowego narzędzia prawniczego. System odnajduje
tylko około połowy wzmianek w danych ogólnych, nie został oceniony na ręcznym
złotym zbiorze orzeczeń, a eksport wyników nie przechodzi obecnie przez oficjalny
scorer. Mały wzrost po DAE pochodzi z jednego treningu, a sam cel rekonstrukcji
korzysta z losowej, zamrożonej projekcji.

Najuczciwsza ocena jest więc pozytywna, ale ostrożna. Architektura zasługuje na
dalszy eksperyment. Korpus SAOS jest wartościowy. Pretrening domenowy jest
obiecujący. Liczby trzeba jednak ponownie potwierdzić po naprawie ewaluacji,
uruchomić kilka ziaren i sprawdzić jakość na ręcznie oznaczonych tekstach
prawnych.

Jeżeli te kroki zostaną wykonane, praca może dostarczyć nie tylko ciekawego
prototypu, lecz także rzetelnej odpowiedzi na ważne pytanie: czy mały model,
uczący się struktury na nieoznaczonych dokumentach, potrafi tanio i lokalnie
dostosować koreferencję do języka prawa. To pytanie ma znaczenie naukowe i
praktyczne, a obecny projekt zbudował już znaczną część potrzebnej drogi.

