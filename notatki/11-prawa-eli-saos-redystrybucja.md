# Ponowne wykorzystanie ELI, SAOS i adnotacji stand-off

**Data kwerendy i dostępu do źródeł:** 2026-09-04

**Zakres:** teksty Dz.U./M.P. pobierane z ELI API Sejmu, dane i teksty orzeczeń z SAOS oraz utworzone na ich podstawie stand-off adnotacje koreferencji.

**Zastrzeżenie:** to jest audyt badawczy, nie porada prawna. Ostateczna decyzja o publicznej redystrybucji pełnego korpusu powinna opierać się na autorytatywnych warunkach podmiotów źródłowych i opinii prawnika znającego konkretny sposób pozyskania i publikacji.

## Wynik w skrócie

| Warstwa | Co można stwierdzić | Praktyczna decyzja |
|---|---|---|
| Urzędowa treść Dz.U./M.P. | Art. 4 pkt 1 ustawy o prawie autorskim wyłącza akty normatywne i ich urzędowe projekty spod prawa autorskiego; pkt 2 wyłącza urzędowe dokumenty, materiały, znaki i symbole. | Dla konkretnego wycinka trzeba dodatkowo zakwalifikować nietypowe załączniki i elementy nieurzędowe oraz sprawdzić prawa do bazy, warunki reuse i PII. Nie należy przypisywać pochodnemu plikowi urzędowego charakteru. |
| Metadane i masowy wyciąg ELI | Publiczne API jest przeznaczone do udostępniania aktów i metadanych. Oddzielnie mogą jednak istnieć prawa do doboru/układu bazy lub sui generis do bazy. Na stronie dokumentacji ELI nie znaleziono osobnej licencji danych ani warunków masowej redystrybucji. | Zachować provenance per akt; przed opublikowaniem pełnego lustra bazy potwierdzić warunki w Kancelarii Sejmu. Sam brak licencji na stronie API nie jest licencją. |
| Teksty orzeczeń w SAOS | Orzeczenia są co do zasady urzędowymi dokumentami z art. 4 pkt 2. SAOS jawnie deklaruje możliwość pobierania przez API metadanych i treści wszystkich zgromadzonych orzeczeń. | Treść pojedynczych orzeczeń ma mocniejszą podstawę niż redystrybucja kompletnego dumpu SAOS. Zawsze wskazać SAOS, jego ID i system źródłowy. |
| Baza SAOS i wzbogacenia | Aktualna dokumentacja nie podaje wyraźnej licencji publicznej redystrybucji korpusu. Raport ekspertów GRAI opublikowany na gov.pl zapisał przy SAOS „Licencja: Brak danych”, ale nie stanowi oficjalnego stanowiska Rady Ministrów. GPL-3.0 repozytorium SAOS dotyczy kodu, nie automatycznie danych. | Nie oznaczać dumpu SAOS jako CC-BY/CC0 bez ustalenia uprawnionego i warunków. Publiczny interfejs jawnie wspiera hurtowe pobieranie do własnej bazy, lecz nie rozstrzyga publicznej redystrybucji kopii. |
| Stand-off koreferencja | Same identyfikatory, offsety, relacje i etykiety nie muszą spełniać progu twórczości; cały dobór/układ adnotacji może być jednak chronionym utworem lub bazą. Uprawnienia zależą też od umów z anotatorami. | Publikować adnotacje oddzielnie od tekstów, z jawną licencją tylko na własną warstwę, np. CC BY 4.0, dopiero po potwierdzeniu praw wszystkich anotatorów i analizie danych osobowych. |
| Dane osobowe | Jawność orzeczenia ani jego obecność w API nie znosi RODO. Rola downstream zależy od tego, kto ustala cele i sposoby przetwarzania; możliwy jest administrator, współadministrator albo procesor. | Przed publikacją ustalić rolę, podstawę, PII/reidentyfikację i zabezpieczenia. Dla danych o wyrokach skazujących art. 10 wymaga dodatkowo nadzoru władz publicznych albo upoważnienia w prawie UE/krajowym. |

## 1. Teksty aktów z ELI API Sejmu

### 1.1. Prawo autorskie do treści

**FAKT.** Aktualny tekst jednolity ustawy o prawie autorskim stanowi, że nie są przedmiotem prawa autorskiego: (1) akty normatywne i ich urzędowe projekty oraz (2) urzędowe dokumenty, materiały, znaki i symbole. Nie jest to licencja, lecz ustawowe wyłączenie ochrony. Obejmuje urzędową treść mieszczącą się w tych kategoriach, ale nie wolno automatycznie rozciągać go na każdy plik ELI, nietypowy załącznik lub element nieurzędowy bez osobnej kwalifikacji. [Ustawa o prawie autorskim i prawach pokrewnych, tekst jedn. Dz.U. 2025 poz. 24, art. 4](https://api.sejm.gov.pl/eli/acts/DU/2025/24/text.pdf)

**DOPRECYZOWANIE.** To wyłączenie nie przenosi automatycznie na użytkownika praw do nieurzędowych elementów serwisu: kodu aplikacji, dokumentacji napisanej twórczo, grafiki lub ewentualnej twórczej organizacji całej kolekcji. Ta sama ustawa chroni twórczy dobór, układ lub zestawienie bazy nawet wtedy, gdy jej elementy nie są chronione (art. 3).

### 1.2. Ponowne wykorzystywanie informacji sektora publicznego

**FAKT.** Ustawa o otwartych danych przyznaje każdemu prawo do ponownego wykorzystywania informacji sektora publicznego udostępnianych m.in. w innym systemie teleinformatycznym podmiotu zobowiązanego (art. 5). Zasadą jest udostępnianie bezwarunkowe i bezpłatne, z ustawowymi wyjątkami (art. 14 i 17). Podmiot może nałożyć m.in. warunek wskazania źródła, czasu wytworzenia i pozyskania oraz informacji o przetworzeniu (art. 15). [Ustawa o otwartych danych i ponownym wykorzystywaniu informacji sektora publicznego, tekst jedn. Dz.U. 2023 poz. 1524](https://api.sejm.gov.pl/eli/acts/DU/2023/1524/text.html)

**WAŻNE OGRANICZENIE.** Reguła, zgodnie z którą brak informacji o warunkach oznacza udostępnienie bezwarunkowe, jest w art. 11 ust. 5 sformułowana dla BIP i portalu danych. Dla informacji udostępnianych w inny sposób art. 11 ust. 4 nakazuje podmiotowi poinformować o braku warunków/opłat albo je określić. Nie należy więc automatycznie rozszerzać fikcji „bezwarunkowości” na każde samodzielne API.

### 1.3. Co rzeczywiście komunikuje ELI

**FAKT.** Dokumentacja ELI opisuje API jako sposób udostępnienia informacji o aktach prawnych w ustandaryzowanym formacie. Podaje stabilny schemat URI i endpointy zwracające listy, metadane oraz teksty PDF/HTML. [Oficjalna dokumentacja ELI API](https://api.sejm.gov.pl/eli_pl.html)

**NIEZWERYFIKOWANE.** Na przejrzanej stronie dokumentacji (oznaczonej aktualizacją 2026-01-12) nie znaleziono:

- osobnej licencji danych;
- limitu zapytań ani regulaminu masowego pobierania;
- oświadczenia, że można publicznie redystrybuować kompletne lustro metadanych API.

Brak takiego tekstu nie dowodzi zakazu, ale też nie zastępuje warunków wymaganych przez art. 11 ustawy. Ustawa o ochronie baz danych przyznaje producentowi, który poniósł istotny nakład, prawo pobierania i wtórnego wykorzystywania całości lub istotnej części bazy (art. 6); samego istnienia tego prawa nie wolno zakładać bez ustalenia producenta i nakładu. Jeżeli prawa do bazy przysługują podmiotowi zobowiązanemu, art. 14 ust. 2 ustawy o otwartych danych nakazuje mu określić warunki ponownego wykorzystania; prawa osoby trzeciej mogą uruchomić ograniczenie z art. 6 ust. 4 pkt 4. Przed publikacją lustra trzeba ustalić producenta, uprawnionego i autorytatywne warunki, a nie automatycznie zakładać zakaz albo konieczność nabycia praw. [Ustawa o ochronie baz danych, tekst jedn. Dz.U. 2024 poz. 1769](https://api.sejm.gov.pl/eli/acts/DU/2024/1769/text.pdf)

Art. 8 ust. 1 pkt 2 ustawy o ochronie baz danych pozwala korzystać z istotnej części rozpowszechnionej bazy w charakterze ilustracji do celów dydaktycznych lub badawczych, ze wskazaniem źródła, jeżeli takie korzystanie jest uzasadnione niekomercyjnym celem. Nie jest to ogólna podstawa publicznej redystrybucji benchmarku, a mała liczba dokumentów nie przesądza sama o nieistotności części bazy — istotność może być ilościowa lub jakościowa.

### 1.4. Minimalny bezpieczny manifest ELI

Dla każdego aktu należy zachować:

- pełny identyfikator ELI, np. `DU/2025/24`, oraz kanoniczny URL;
- wydawnictwo (`DU` albo `MP`), rok, pozycję i rodzaj tekstu (`ogl`, `tj`, `uj`);
- czas pobrania, nagłówki `ETag`/`Last-Modified`, jeżeli serwer je zwraca, oraz SHA-256 pobranego pliku;
- informację, czy opublikowany tekst został oczyszczony, podzielony na dokumenty albo znormalizowany;
- wyraźne zastrzeżenie, że pochodny plik nie jest urzędowym źródłem prawa.

## 2. SAOS: tekst orzeczenia, baza i wzbogacenia to trzy różne warstwy

### 2.1. Treść orzeczeń

**WNIOSEK Z PRZEPISU.** Orzeczenie sądowe jest urzędowym dokumentem, więc jego urzędowa treść co do zasady mieści się w art. 4 pkt 2 ustawy o prawie autorskim. Nadal należy odróżnić sam tekst orzeczenia od nieurzędowej redakcji, glosy, abstraktu, opracowania lub warstwy portalu.

**FAKT.** SAOS informuje, że gromadzi dane orzeczeń polskich sądów i umożliwia pobranie metadanych oraz treści wszystkich zgromadzonych orzeczeń przez programowe API. Dokumentacja opisuje API pobierania danych jako narzędzie do hurtowego ściągania całej bazy, zbudowania własnej bazy i synchronizacji. [Strona główna SAOS](https://www.saos.org.pl/), [dokumentacja API pobierania danych](https://www.saos.org.pl/help/index.php/dokumentacja-api/api-pobierania-danych)

Jest to wyraźna deklaracja dozwolonego sposobu pobierania i kopiowania do własnej bazy, ale nie jednoznaczne zezwolenie na publiczną redystrybucję kopii.

### 2.2. Brak jawnej licencji dumpu

**FAKT.** W przejrzanych aktualnych stronach SAOS (serwis w wersji 0.9.13, dokumentacja i strony pomocy) nie znaleziono licencji danych ani warunków ich redystrybucji. Pomocniczym, zgodnym sygnałem jest raport grupy ekspertów GRAI opublikowany na gov.pl, który przy SAOS podaje `Licencja: Brak danych` (str. 50), a przy ISAP analogiczny brak danych (str. 64). Raport zastrzega jednak, że nie stanowi oficjalnego stanowiska Rady Ministrów; wpis nie dowodzi braku licencji ani nie rozstrzyga praw do redystrybucji. [Raport „Przegląd polskich zasobów językowych w otwartym dostępie o znaczącym potencjale dla AI w biznesie”](https://www.gov.pl/attachment/66a49243-bb16-4388-b38a-0c908f2edcb0)

**FAKT.** Oficjalne repozytorium oprogramowania SAOS prowadzone przez CeON ma licencję GPL-3.0. Nie ma podstaw, aby tę licencję kodu automatycznie stosować do treści bazy. Stan sprawdzony na commicie `b6b64ddaf3140c98ddd1b59ff8cda9b5a92c32f8`. [Plik `LICENSE` repozytorium CeON/saos](https://github.com/CeON/saos/blob/b6b64ddaf3140c98ddd1b59ff8cda9b5a92c32f8/LICENSE)

### 2.3. Dane źródłowe i dane generowane

**FAKT.** SAOS podaje, że automatycznie importuje dane z Portalu Orzeczeń Sądów Powszechnych, serwisów Sądu Najwyższego, Trybunału Konstytucyjnego i Krajowej Izby Odwoławczej. Odpowiedzialność za treść oraz upublicznienie danych osobowych przypisuje systemom źródłowym. [SAOS — O projekcie, sekcja „Dane osobowe”](https://www.saos.org.pl/help/index.php)

**FAKT.** SAOS wzbogaca importowane dane automatycznymi tagami. Dokumentacja ostrzega, że tagów nie zweryfikował człowiek i mogą zawierać błędy; API oznacza je polem `generated=true`. Ta warstwa nie jest tożsama z urzędową treścią orzeczenia i nie należy przypisywać jej statusu urzędowego. [SAOS — Wzbogacanie danych](https://www.saos.org.pl/help/index.php/wzbogacanie-danych)

**WNIOSEK.** Publiczny korpus powinien rozdzielać co najmniej:

1. niezmienioną treść i metadane pochodzące z systemu źródłowego;
2. generowane pola SAOS;
3. własne transformacje i adnotacje projektu.

## 3. Prywatność, PII i orzeczenia

**FAKT.** Ustawa o otwartych danych ogranicza prawo ponownego wykorzystywania ze względu na prywatność osoby fizycznej, w tym ochronę danych osobowych (art. 6 ust. 2), i wprost stwierdza, że nie narusza przepisów o ochronie danych osobowych (art. 7 ust. 2). Publiczna dostępność nie jest zatem samodzielną podstawą dowolnego dalszego przetwarzania.

**FAKT.** RODO definiuje dane osobowe szeroko: identyfikacja może być pośrednia. Pobieranie, organizowanie, przechowywanie, wykorzystywanie i publiczne udostępnianie są „przetwarzaniem”. Jeżeli odbiorca samodzielnie lub wspólnie ustala cele i sposoby przetwarzania, jest odpowiednio administratorem albo współadministratorem i musi ustalić podstawę z art. 6; podmiot działający wyłącznie na udokumentowane polecenie może być procesorem. Zastosowanie mają też zasady ograniczenia celu, minimalizacji, prawidłowości, retencji, bezpieczeństwa i rozliczalności z art. 5. [RODO, art. 4–6](https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=celex:32016R0679)

**FAKT.** Dane dotyczące wyroków skazujących i naruszeń prawa podlegają szczególnej regule art. 10 RODO. Sama podstawa z art. 6 ani badawczy charakter celu nie wystarczają: trzeba również wykazać nadzór władz publicznych albo upoważnienie w prawie UE lub krajowym przewidującym odpowiednie zabezpieczenia. Art. 89 opisuje zabezpieczenia badań, w tym minimalizację, ale nie zastępuje tego upoważnienia. [RODO, art. 10 i 89](https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=celex:32016R0679)

**RYZYKO PRAKTYCZNE.** Automatyczna anonimizacja może nie usunąć identyfikatorów pośrednich. Stand-off offsety bez tekstu również mogą wskazywać konkretne osoby po połączeniu z publicznym dokumentem. Pseudonimizacja nie jest anonimizacją: jeżeli istnieje realna możliwość ponownej identyfikacji, RODO nadal ma zastosowanie.

Minimalna kontrola przed publikacją:

- skan nazwisk, adresów, PESEL, danych kontaktowych, sygnatur umożliwiających łatwe połączenie oraz szczególnych kategorii danych;
- ręczna kontrola losowej próby i wszystkich trafień skanera;
- osobna analiza spraw karnych i danych dzieci;
- brak niepotrzebnych fragmentów tekstu w pliku adnotacji;
- procedura zgłoszenia, poprawy i usunięcia wadliwie zanonimizowanego rekordu;
- zapis podstawy prawnej, celu, retencji i kontroli dostępu.

## 4. Status stand-off adnotacji koreferencji

### 4.1. Prawa do wejścia a prawa do nowej warstwy

**FAKT.** Prawo autorskie chroni tylko przejaw działalności twórczej o indywidualnym charakterze, nie idee, procedury, metody ani zasady działania (art. 1). Twórczy dobór i układ bazy może być chroniony nawet wtedy, gdy elementy nie są (art. 3). Opracowanie cudzego chronionego utworu może tworzyć prawa zależne (art. 2). [Ustawa o prawie autorskim, art. 1–3](https://api.sejm.gov.pl/eli/acts/DU/2025/24/text.pdf)

**WNIOSEK OSTROŻNY.** Pojedyncze decyzje typu `span=[start,end]`, `cluster_id=7` lub relacja antecedentowa mają głównie charakter faktograficzny/metodyczny i mogą nie osiągać progu twórczości. Nie ma jednak podstaw, by bez analizy uznać cały korpus za niechroniony: twórczy schemat, wybór przykładów, komentarze anotatorów albo baza wymagająca istotnego nakładu mogą tworzyć odrębne prawa.

Ponieważ urzędowe teksty aktów i orzeczeń co do zasady nie są przedmiotem prawa autorskiego, sama stand-off adnotacja do takiego tekstu nie wymaga zezwolenia „twórcy tekstu urzędowego” na zasadzie art. 2. Nie rozwiązuje to jednak:

- praw do masowo wyekstrahowanej bazy ELI/SAOS;
- praw do nieurzędowych opracowań, tez i automatycznych wzbogaceń;
- praw anotatorów i producenta nowej bazy;
- prywatności i ochrony danych osobowych.

### 4.2. Kto może udzielić licencji

**FAKT.** Ochrona powstaje bez formalności. Jeżeli warstwa ma cechy utworu, pierwotnym uprawnionym jest co do zasady twórca. Przy utworze pracowniczym pracodawca nabywa prawa majątkowe dopiero w granicach art. 12 i konkretnego stosunku pracy; status studenta, zleceniobiorcy lub wolontariusza trzeba ustalić z umowy, a nie zakładać. [Ustawa o prawie autorskim, art. 8 i 12](https://api.sejm.gov.pl/eli/acts/DU/2025/24/text.pdf)

Przed nadaniem licencji korpusowi trzeba mieć:

- listę autorów/anotatorów i podstawę nabycia praw;
- dla celów dowodowych i bezpiecznej publikacji — pisemnie udokumentowaną podstawę obejmującą publiczną redystrybucję, modyfikacje i użycie komercyjne;
- ustalone prawa producenta bazy;
- zgodę na publikację komentarzy swobodnych, jeżeli są zachowane;
- osobne oznaczenie materiałów, do których licencjodawca nie ma praw.

### 4.3. Zalecany model publikacji

**PROPOZYCJA, NIE USTALENIE PRAWNE.** Publikować dwa oddzielne artefakty:

1. `annotations.jsonl` — dokument ID/źródłowy URL, wersja tekstu i hash, offsety/segmenty, klastry, status adjudykacji, provenance i wersja schematu; bez pełnego tekstu;
2. skrypt odtwarzający tekst z urzędowego API, z cache'em lokalnym i manifestem integralności.

Własną warstwę adnotacji można udostępnić np. na **CC BY 4.0**, jeżeli projekt rzeczywiście posiada prawa wszystkich autorów i producenta bazy. CC BY 4.0 obejmuje wprost prawa sui generis do baz danych, ale daje tylko te uprawnienia, którymi licencjodawca może rozporządzać; nie obejmuje automatycznie prywatności ani praw osób trzecich. [Oficjalny tekst prawny CC BY 4.0, § 1, 2 i 4](https://creativecommons.org/licenses/by/4.0/legalcode.pl)

Plik `LICENSE-DATA.md` powinien wyraźnie stwierdzać:

> W zakresie, w jakim oryginalna warstwa adnotacji jest chroniona prawem autorskim lub prawami sui generis do bazy danych i prawa te przysługują licencjodawcy, warstwa ta jest udostępniana na CC BY 4.0. Licencja nie obejmuje tekstów źródłowych, cudzych metadanych, kodu, znaków ani innych materiałów osób trzecich i nie stanowi podstawy ani zezwolenia na przetwarzanie danych osobowych. Licencjodawca nie twierdzi, że prawa wyłączne istnieją do każdego pojedynczego identyfikatora, offsetu lub faktu.

## 5. Decyzja dla projektu `mg2`

### Można zrobić teraz lokalnie lub w repozytorium z kontrolą dostępu

- przechowywać manifesty, identyfikatory ELI/SAOS, URL-e, hashe, skrypty pobierające i robocze stand-off adnotacje;
- przygotować prywatny, mały test z pełnym provenance i oznaczeniem transformacji;
- prowadzić zamkniętą anotację badawczą na legalnie pobranych danych;
- określić licencję własnego kodu niezależnie od licencji danych.

### Wstrzymać przed publicznym pushem

- pełny lub istotny dump SAOS;
- kompletne lustro metadanych ELI;
- automatyczne wzbogacenia SAOS oznaczone jako `generated=true`;
- pliki z nieweryfikowanym PII albo umożliwiające prostą reidentyfikację;
- stand-off adnotacje przed ustaleniem praw anotatorów/producenta nowej bazy i analizą, czy ID, hashe lub offsety umożliwiają identyfikację po połączeniu ze źródłem;
- nadanie CC0/CC-BY całemu pakietowi, jeżeli zawiera warstwy cudze.

### Najmniejszy następny sprawdzalny krok

Wysłać do Kancelarii Sejmu i opiekuna SAOS dwa krótkie pytania z dokładnym opisem planowanego artefaktu:

1. czy wolno publicznie redystrybuować zamrożony, nieaktualizowany wycinek pełnych tekstów i metadanych oraz na jakich warunkach atrybucji;
2. czy publiczne odwołania przez ELI/SAOS ID, hash i offset naruszają warunki dotyczące danych źródłowych lub ich bazy.

Prawa do własnej warstwy ustalić osobno z anotatorami, uczelnią/pracodawcą i producentem nowej bazy. Odpowiedzi zachować jako provenance. Do czasu tych ustaleń oraz analizy PII publiczny artefakt powinien domyślnie zawierać wyłącznie kod i zagregowane wyniki; manifesty i adnotacje pozostają w repozytorium z kontrolą dostępu. Dla danych objętych art. 10 trzeba dodatkowo wykazać właściwe upoważnienie prawne albo użyć danych rzeczywiście anonimowych.

## Źródła pierwotne i materiały pomocnicze

- [ELI API — oficjalna dokumentacja](https://api.sejm.gov.pl/eli_pl.html), dostęp 2026-09-04.
- [Ustawa o prawie autorskim i prawach pokrewnych, tekst jedn. Dz.U. 2025 poz. 24](https://api.sejm.gov.pl/eli/acts/DU/2025/24/text.pdf), dostęp 2026-09-04.
- [Ustawa o otwartych danych i ponownym wykorzystywaniu informacji sektora publicznego, tekst jedn. Dz.U. 2023 poz. 1524](https://api.sejm.gov.pl/eli/acts/DU/2023/1524/text.html), dostęp 2026-09-04.
- [Ustawa o ochronie baz danych, tekst jedn. Dz.U. 2024 poz. 1769](https://api.sejm.gov.pl/eli/acts/DU/2024/1769/text.pdf), dostęp 2026-09-04.
- [SAOS — strona główna](https://www.saos.org.pl/) i [dokumentacja API](https://www.saos.org.pl/help/index.php/dokumentacja-api), dostęp 2026-09-04.
- [SAOS — O projekcie i dane osobowe](https://www.saos.org.pl/help/index.php), dostęp 2026-09-04.
- [SAOS — Wzbogacanie danych](https://www.saos.org.pl/help/index.php/wzbogacanie-danych), dostęp 2026-09-04.
- [CeON/saos, `LICENSE`, commit `b6b64dd`](https://github.com/CeON/saos/blob/b6b64ddaf3140c98ddd1b59ff8cda9b5a92c32f8/LICENSE), dostęp 2026-09-04.
- [RODO, rozporządzenie (UE) 2016/679](https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=celex:32016R0679), dostęp 2026-09-04.
- [Creative Commons Attribution 4.0 — tekst prawny](https://creativecommons.org/licenses/by/4.0/legalcode.pl), dostęp 2026-09-04.
- [Raport grupy ekspertów GRAI o polskich zasobach językowych](https://www.gov.pl/attachment/66a49243-bb16-4388-b38a-0c908f2edcb0), pomocniczy sygnał `Licencja: Brak danych`; raport nie stanowi oficjalnego stanowiska Rady Ministrów; dostęp 2026-09-04.
