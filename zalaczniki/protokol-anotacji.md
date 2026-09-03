# Protokół anotacji koreferencji w polskich orzeczeniach

Wersja: 1.0, 2026-09-03. Planowana próbka obejmuje 24 orzeczenia. Wszystkie dokumenty anotuje niezależnie dwóch anotatorów; rozbieżności rozstrzyga się dopiero po obliczeniu zgodności.

## 1. Cel i jednostki

Celem jest oznaczenie wzmianek odnoszących się do tej samej encji w obrębie jednego dokumentu. Wzmianka to minimalny ciągły fragment tekstu pozwalający wskazać osobę, organizację, rzecz, dokument, miejsce albo lokalnie zdefiniowany obiekt. Klaster to zbiór co najmniej jednej wzmianki o identycznej referencji. Nie tworzy się klastrów między dokumentami.

Anotuje się pełną granicę syntaktycznej frazy i osobno jej głowę semantyczną. Determinatory i modyfikatory konieczne do rozróżnienia obiektu wchodzą do spanu; końcową interpunkcję pomija się. Podmiot zerowy zapisuje się jako pustą wzmiankę zakotwiczoną przy orzeczeniu czasownikowym. Każda wzmianka otrzymuje typ: PERSON, ORG, ROLE, OBJECT, PLACE, DOCUMENT, PROVISION albo OTHER.

## 2. Relacja identyczności

Dwie wzmianki łączy się, jeżeli w danym kontekście wskazują dokładnie ten sam obiekt. Przykłady dodatnie:

- „Anna Nowak” — „powódka” — „ona”;
- „ABC sp. z o.o.” — „Wykonawca”, jeżeli dokument jawnie wprowadza definicję;
- „umowa z 3 maja” — „przedmiotowa umowa”;
- „§ 4 ust. 2” — „powyższe postanowienie”, jeżeli nie ma konkurencyjnego przepisu;
- „pozwany złożył apelację i ∅ wniósł o zmianę wyroku”, gdzie ∅ jest podmiotem drugiego orzeczenia.

Nie łączy się: elementu i zbioru, klasy i egzemplarza, osoby i pełnionej funkcji w innym czasie, autora i cytowanego organu, dwóch różnych osób zastąpionych takim samym „X.Y.” ani dwóch wystąpień roli z różnych spraw. Relacja część--całość, mostkowanie i podobieństwo tematyczne nie są identycznością.

## 3. Przypadki szczególne

### Terminy definiowane

Fraza „zwany dalej X” tworzy alias tylko w zakresie obowiązywania definicji. Anotuje się pełną nazwę, wystąpienie definicyjne X oraz kolejne użycia X w jednym klastrze. Jeżeli X oznacza zbiór podmiotów, nie łączy się go z każdym członkiem osobno.

### Role procesowe

„Powód”, „skarżący”, „wnioskodawca” i inne role łączy się z nazwą osoby tylko przy jednoznacznym przypisaniu w dokumencie. Zmiana roli między instancjami nie zrywa tożsamości osoby, ale sama nazwa roli bez jednoznacznego referenta pozostaje osobną wzmianką.

### Anonimizacja

Znaczniki „X.Y.”, „(...)” i „[dane usunięte]” łączy się wyłącznie na podstawie kontekstu. Identyczna powierzchnia nie jest dowodem identyczności. Jeżeli nie można rozstrzygnąć, oznacza się flagę UNCERTAIN i nie łączy klastrów przed adjudykacją.

### Cytaty i mowa zależna

W cytacie anotuje się referencję zgodnie z perspektywą cytowanego fragmentu, ale identyfikator encji pozostaje dokumentowy. „Ja” w dwóch cytatach różnych świadków nie należy do jednego klastra. Fragment przytoczonej ustawy anotuje się tylko wtedy, gdy jego referencja jest potrzebna w bieżącym uzasadnieniu.

### Wzmianki zagnieżdżone i koordynacje

W „prezes spółki ABC” można oznaczyć osobę oraz zagnieżdżoną organizację, jeżeli obie uczestniczą w późniejszych łańcuchach. Koordynacja „powód i pozwany” tworzy wzmiankę mnogą odrębną od klastrów członów; relację grupową zapisuje się w uwadze, nie jako identyczność z każdym członem.

### Singletony i wzmianki nieciągłe

Singletony są oznaczane, aby mierzyć wykrywanie wzmianek, lecz ustawienie scorera musi jawnie określać ich uwzględnienie. Wzmiankę nieciągłą zapisuje się jako listę segmentów i wskazuje jedną głowę; eksport uproszczony może użyć minimalnego spanu pokrywającego, ale musi zachować oryginalne segmenty.

## 4. Procedura anotatora

1. Zapoznać się z całym dokumentem bez oznaczania.
2. W drugim przejściu oznaczyć wszystkie wzmianki i ich głowy, nie tworząc jeszcze klastrów.
3. Przypisać typy i flagi ZERO, NESTED, DISCONTINUOUS lub UNCERTAIN.
4. Utworzyć klastry od nazw i terminów definiowanych, następnie dołączyć deskrypcje, zaimki i zera.
5. Dla każdej nowej krawędzi sprawdzić tożsamość, rodzaj/liczbę, rolę, zakres definicji i konkurencyjnych kandydatów.
6. Uruchomić walidator: jedna wzmianka w jednym klastrze, poprawne granice, brak klastrów między dokumentami, unikatowe identyfikatory.
7. Zapisać bez konsultacji z drugim anotatorem. Dyskusję rozpocząć dopiero po zamrożeniu obu wersji.

Anotator nie zgaduje. Przypadek niejednoznaczny otrzymuje UNCERTAIN oraz jednozdaniowe uzasadnienie i trafia do adjudykacji. Zabronione jest wysyłanie tekstu do publicznej usługi LLM.

## 5. Zgodność

Najpierw mierzy się zgodność wykrywania wzmianek: precision, recall i F1 dla exact-match oraz head-match między anotatorami. Następnie tworzy się wspólny zbiór jednostek parowych ze wzmianek dopasowanych głową. Dla każdej pary w jednym dokumencie anotator nadaje kategorię 1 (ta sama encja), 0 (różne encje) albo brak danych, gdy wzmianki nie da się dopasować.

Dla kategorii nominalnych oblicza się współczynnik Krippendorffa \(\alpha=1-D_o/D_e\), gdzie \(D_o\) jest obserwowaną niezgodnością, a \(D_e\) oczekiwaną niezgodnością przy rozkładzie marginalnym. Raport zawiera liczbę jednostek, braków, rozkład 0/1, \(\alpha\) i przedział ufności z bootstrapu dokumentów. Ze względu na przewagę par negatywnych raportuje się również dodatnie pairwise F1 i LEA między partycjami anotatorów.

Próg roboczy wynosi \(\alpha\geq0{,}80\). Wynik 0,67--0,80 wymaga doprecyzowania instrukcji i ponownej anotacji próbki pilotażowej; wynik poniżej 0,67 wstrzymuje tworzenie złota. Próg jest procedurą kontroli, nie gwarancją poprawności.

## 6. Pilotaż, adjudykacja i wersjonowanie

Najpierw niezależnie anotuje się 3 dokumenty pilotażowe spoza finalnego testu. Po obliczeniu metryk omawia się rozbieżności, aktualizuje instrukcję i anotuje pilotaż ponownie. Finalne 24 dokumenty pozostają niezależne do chwili obliczenia zgodności. Adjudykator widzi oba warianty i uzasadnienia, wybiera jeden, tworzy nową decyzję albo pozostawia przypadek wyłączony z głównego testu.

Każda wersja ma identyfikator dokumentu, hash tekstu, identyfikator anotatora, czas, wersję instrukcji i historię zmian. Złoty plik powstaje jako nowy artefakt; nie nadpisuje surowych anotacji. Publikacja zawiera agregaty i kod eksportu, a tekst tylko wtedy, gdy pozwala na to licencja i audyt PII.
