# Plan treningu i transferu koreferencji

Data zamrożenia protokołu: 2026-09-03.

## Cel pilota

Wytrenować porównywalny model bazowy i odszumiający autokoder (DAE) na naturalnych,
ręcznie anotowanych danych Polish-PCC, zmierzyć jakość klastrowania na odłożonych
danych ogólnych oraz sprawdzić jakościowo transfer najlepszego wariantu na urzędowym
tekście prawnym ELI.

## Kroki i artefakty

1. Pobrać oficjalne CorefUD 1.4, zachować URL, licencję, rozmiar i SHA-256.
2. Skonwertować Polish-PCC do JSONL i zwalidować parser na konstrukcjach
   zagnieżdżonych oraz nieciągłych.
3. Podzielić część `train` dokumentowo na 85% treningu i 15% kalibracji. Oficjalnego
   `dev` nie używać do uczenia ani wyboru progu.
4. Zamrożonym `allegro/herbert-base-cased` wyznaczyć reprezentacje wzmianek. Zbudować
   niepokrywające się okna po maksymalnie 48 złotych wzmianek i osiem cech parowych.
5. Na identycznych tensorach wytrenować kontrolę bez autokodera oraz DAE. Zapisać
   konfiguracje, logi każdej iteracji, checkpointy i zużycie pamięci GPU.
6. Na kalibracji dobrać próg łączenia z poprzednikiem według parowego F1. Próg zamrozić.
7. Na CorefUD-dev policzyć parowe P/R/F1 oraz MUC, B³, CEAF_e, LEA, BLANC i CoNLL F1
   oficjalnym scorerem CorefUD. Ocena dotyczy klastrowania przy złotych granicach
   wzmianek i projekcji dokumentów na okna; nie jest wynikiem pełnego end-to-end.
8. W tekście ELI wykryć kandydatów nominalnych narzędziem Stanza, zakodować ich tym
   samym HerBERT-em i zapisać łańcuchy najlepszego modelu do ręcznego przeglądu.
9. Sporządzić raport z rozdzieleniem wyników ilościowych Polish-PCC od jakościowego
   transferu prawnego oraz z listą warunków pełnego eksperymentu domenowego.

## Kryteria uczciwości

- Żadna liczba nie jest raportowana przed realnym uruchomieniem.
- Kalibracja i test są rozłączne na poziomie dokumentu.
- Tekst ELI bez złotej anotacji nie służy do obliczania F1.
- Wniosek o wpływie autokodera wymaga porównania z kontrolą na identycznych danych.
- Pilot jednego seedu nie rozstrzyga jeszcze istotności statystycznej PB1.

## Aktualizacja po utworzeniu ELI-400

1. Głównymi etykietami srebrnymi są predykcje CorPipe 26 w
   `kod/data/processed/legal-silver-400/corpipe26/splits/`; Stanza służy do
   oznaczenia zgodności, a nie jako złoty klucz.
2. Najpierw należy przejrzeć `review_sample_100.csv` i doprecyzować instrukcję
   anotacji na podstawie rozbieżności modeli.
3. Następnie trzeba poprawić wszystkie dokumenty `dev` i `test`. Nie wolno
   stroić modelu na poprawionym `test`.
4. DAE można dostroić na srebrnym `train`, ważąc przykłady według
   `agreement_band`; wariant bez takiego ważenia pozostaje obowiązkową kontrolą.
5. Wynik domenowy wolno policzyć dopiero względem poprawionego ludzkiego testu.
   Wynik przeciw surowemu CorPipe mierzyłby imitację nauczyciela, nie prawdziwą
   jakość koreferencji prawnej.

Lokalny punkt odniesienia na złotym Polish-PCC dev: CorPipe 26 base osiągnął
CoNLL F1 0,7297 i LEA 0,6840 end-to-end; DAE osiągnął odpowiednio 0,5510 i
0,5007 przy złotych granicach wzmianek. Szczegóły są w
`wyniki/legal-silver-400/RAPORT.md`.
