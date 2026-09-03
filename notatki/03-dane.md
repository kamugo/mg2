# Dane i pipeline przygotowania

## 1. Role zbiorów

Korpus Polish-PCC z zamrożonego wydania CorefUD pełni rolę źródła złotych etykiet i danych ogólnojęzykowych. Nie należy mieszać plików z oryginalnego PCC 1.5 z wydaniem CorefUD, ponieważ różnią się formatem, licencją i procedurą ewaluacji. Manifest pobrania ma zawierać URL, wersję, SHA-256, datę oraz kopię informacji licencyjnej. Oficjalne splity train/dev/test zachowuje się bez zmian.

Korpus domenowy tworzy się z 24 polskich orzeczeń dobranych z jawnie licencjonowanej migawki JuDDGES-pl; jeżeli audyt licencji lub PII go wykluczy, używa się aktów ELI i ogranicza wniosek do języka legislacji. Wszystkie 24 dokumenty podlegają podwójnej anotacji według zalaczniki/protokol-anotacji.md. Podział 14/5/5 wykonuje się grupowo po identyfikatorze sprawy, po deduplikacji i przed oglądaniem etykiet. Mała liczba dokumentów oznacza studium wykonalności i szerokie przedziały ufności, nie reprezentatywny benchmark polskiego prawa.

Nieetykietowany tekst domenowy służy wyłącznie do pretrainingu DAE. Dokumenty domenowego dev/test, ich duplikaty i sprawy powiązane usuwa się z tego korpusu przed uczeniem. LexGLUE, LegalBench i CUAD nie dostarczają polskich etykiet koreferencji; nie są używane jako złoty test.

## 2. Pobieranie i pochodzenie

Skrypt kod/scripts/pobierz_dane.py ma trzy jawne tryby:

1. corefud pobiera wyłącznie podany przez badacza URL konkretnego wydania, opcjonalnie sprawdza oczekiwany SHA-256 i tworzy manifest. Brak URL kończy się kodem 2 z instrukcją.
2. eli --year ROK --limit N pobiera ograniczoną próbkę tekstów aktów z oficjalnego API Sejmu, zapisuje metadane i hashe.
3. juddges nie uruchamia automatycznie pobrania 43,1 GB; wypisuje komendę do ręcznego zamrożenia rewizji i kończy się kodem 2.

Surowe dane znajdują się poza kontrolą wersji w kod/data/raw/. Do repozytorium trafiają manifesty bez treści chronionej, kod, statystyki agregowane i małe przykłady syntetyczne. Każdy etap zapisuje identyfikator źródła, aby można było wycofać dokumenty po zmianie statusu prawnego.

## 3. Konwersja do wspólnego formatu

kod/src/data/konwersja.py czyta CoNLL-U/CorefUD i zapisuje jeden obiekt JSON na dokument. Pomija wiersze tokenów wielowyrazowych, zachowuje zwykłe tokeny i puste węzły, przetwarza nawiasową wartość Entity oraz zapisuje spany jako przedziały półotwarte [start,end). Schemat 1.0 zawiera:

- doc_id, source, text i schema_version;
- listę tokenów z conllu_id, formą, lematem, UPOS, cechami, numerem zdania i flagą pustego węzła;
- listę wzmianek z mention_id, entity_id, granicami, deskryptorem CorefUD i flagą wzmianki zerowej.

Konwerter przerywa pracę przy wierszu innym niż 10-kolumnowy, zamknięciu encji bez otwarcia albo niezamkniętej anotacji. Te błędy nie są naprawiane heurystycznie. Przed pełnym użyciem konwerter trzeba uruchomić na oficjalnym walidatorze i ręcznie porównać co najmniej 20 dokumentów, w szczególności wzmianki zagnieżdżone, nieciągłe i puste.

## 4. Tokenizacja i długie dokumenty

Najpierw zachowuje się indeksację słów CorefUD, a tokenizer HerBERT tworzy mapowanie słowo--subword przez word_ids. Reprezentacja granicy używa pierwszego i ostatniego subwordu, natomiast głowa pozostaje wskazana indeksem słowa. Nie dopuszcza się cichego obcięcia wzmianki; przykład bez pełnej mapy granic jest raportowany jako błąd.

Dokumenty dłuższe niż okno 512 subwordów dzieli się na okna długości 384 ze stride 256. Granice przesuwa się do końca zdania w zakresie ±32 subwordów, o ile nie powoduje to przekroczenia limitu. Wzmianka przecinająca granicę jest dołączana w całości do jednego z okien, a bardzo długa wzmianka otrzymuje osobny raport. Każde okno przechowuje globalne identyfikatory tokenów i wzmianek.

Predykcje z nakładających się okien scala się po globalnym mention_id. Dla tej samej pary bierze się maksimum skalibrowanego prawdopodobieństwa, ale krawędź przyjmuje się dopiero po zastosowaniu progu dobranego na dev. Union-find buduje klastry w obrębie dokumentu; nigdy nie łączy encji między dokumentami. Dla par, które nie wystąpiły razem w żadnym oknie, przeprowadza się drugi, lekki przebieg nad centroidami klastrów albo pozostawia je rozdzielone w odpowiedniej ablacji.

## 5. Splity i ochrona przed przeciekiem

Oficjalny split CorefUD jest stały. Dla orzeczeń jednostką grupowania jest stabilny identyfikator sprawy; dokumenty o tym samym tekście po normalizacji, tej samej sygnaturze albo znacznym podobieństwie MinHash trafiają do jednej grupy. Losowanie z seedem 20260903 wykonuje się raz i zapisuje jako manifest. Na test nie wolno patrzeć podczas doboru progu, szerokości okna, wymiaru latentnego ani promptu LLM.

Pretraining domenowy może używać wyłącznie dokumentów niepowiązanych z dev/test. Demonstracje few-shot pochodzą z train. W przypadku publikowanego modelu należy ujawnić, czy enkoder bazowy mógł wcześniej widzieć tekst dokumentu w pretrainingu; tego ryzyka nie można całkowicie wykluczyć, więc porównanie opiera się na wspólnym enkoderze.

## 6. Transfer domeny

Główna różnica rozkładu dotyczy długości dokumentów, ról procesowych, terminów definiowanych, cytatów ustaw, powtórzeń szablonowych i anonimizacji. DAE uczy się na nieetykietowanym legalnym tekście, a głowica koreferencji na Polish-PCC; dopiero końcowe strojenie używa 14 domenowych dokumentów train. Warianty kontrolne to: brak pretrainingu, pretraining tylko na PCC oraz pretraining na korpusie prawniczym. Ocena osobno raportuje nazwy, deskrypcje ról, zaimki jawne, podmioty zerowe i odwołania do dokumentu.

## 7. Licencje, RODO i bezpieczeństwo

Do pipeline'u dopuszcza się tylko konkretną migawkę z jawną licencją albo ustawową podstawą ponownego wykorzystania. Licencja jest weryfikowana niezależnie dla danych, kodu i wag modelu. SAOS i CUAD pozostają wyłączone do czasu udokumentowania praw do danego artefaktu. JuDDGES-pl wymaga zachowania CC BY 4.0 i audytu prywatności, a ELI obejmuje dokumenty urzędowe wyłączone z ochrony prawnoautorskiej, co nie uchyla obowiązków dotyczących danych osobowych.

Przed anotacją skaner wykrywa PESEL, adresy, telefony, e-maile i daty urodzenia. Wynik jest ręcznie przeglądany; samo dopasowanie wyrażeń regularnych nie dowodzi anonimizacji. Surowe dane przechowuje się lokalnie z ograniczonym dostępem, a publiczny artefakt zawiera tylko identyfikatory do ponownego pobrania, kod i agregaty. Tekst z możliwym PII nie jest wysyłany do zewnętrznego LLM. Naruszenie tej reguły eliminuje dokument z eksperymentu i jest rejestrowane.

## 8. Statystyki korpusu

Poniższa tabela pozostaje niewypełniona do chwili zamrożenia pełnych danych. Polecenie reprodukcyjne: python kod/scripts/statystyki.py PLIK.jsonl --output wyniki/statystyki.json.

| część | dokumenty | tokeny | wzmianki | klastry | wzmianki zerowe |
|---|---:|---:|---:|---:|---:|
| CorefUD-PL train | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] |
| CorefUD-PL dev | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] |
| CorefUD-PL test | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] |
| prawniczy train/dev/test | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] | [DO UZUPEŁNIENIA: wynik uruchomienia kod/scripts/statystyki.py] |

## 9. Próba uruchomieniowa

Na syntetycznym pliku kod/tests/fixtures/sample.conllu konwerter i skrypt statystyk rzeczywiście uruchomiono 2026-09-03. Otrzymano 1 dokument, 9 tokenów, 3 wzmianki, 2 klastry i 1 wzmiankę zerową; surowy wynik zapisano w wyniki/s04-data-smoke.json. Liczb tych nie należy interpretować jako statystyk korpusu badawczego. Tryb CorefUD bez URL sprawdzono osobno i zakończył się oczekiwanym kodem 2.

Tryb ELI uruchomiono dla roku 2024 z limitem jednego aktu; zapisano tekst, metadane i manifest w kod/data/raw/eli-smoke. Tryb JuDDGES zakończył się oczekiwanym kodem 2 i instrukcją ręcznego zamrożenia dużej migawki.
