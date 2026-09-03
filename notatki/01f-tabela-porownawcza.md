# Zbiorcza tabela metod i wyników

Stan scalenia: 2026-09-03. Wartość „—” oznacza, że w odwiedzonym źródle nie przepisano bezpiecznie jednej wartości tabelarycznej. Oznaczenie **NIEPORÓWNYWALNE** wskazuje inny zbiór, podzbiór, definicję zadania, metrykę lub protokół; takich wierszy nie wolno używać do rankingu metod.

| metoda | dane | metryka | wynik | rok | klucz_bib |
|---|---|---|---:|---:|---|
| GAE grafu słów kluczowych | 20 Newsgroups, Reuters | miary klastrowania | poprawa względem cech bazowych; bez bezpiecznie przepisanej liczby | 2020 | chiu_2020_keyword |
| SDNE | 5 sieci rzeczywistych | klasyfikacja / predykcja krawędzi / wizualizacja | — | 2016 | wang_2016_sdne |
| mention-ranking, modele wyspecjalizowane | ACE Phase 2 | MUC/B³/CEAF F-score | wzrost >3% względem modeli bazowych | 2008 | denis_2008_specialized |
| LLM zero-shot | benchmarki angielskie | tradycyjne metryki koreferencji | — | 2024 | gan_2024_llm_coref |
| few-shot CoT | benchmarki angielskie | stabilność i metryki koreferencji | najlepszy wariant promptu; bez jednej liczby | 2024 | gan_2024_llm_coref |
| DAE | benchmarki klasyfikacyjne | rekonstrukcja / błąd klasyfikacji | **NIEPORÓWNYWALNE: zadanie ogólne**, — | 2008 | vincent_2008_dae |
| contractive AE | benchmarki klasyfikacyjne | rekonstrukcja + norma Jacobianu | **NIEPORÓWNYWALNE: zadanie ogólne**, — | 2011 | rifai_2011_contractive |
| AE | dane ogólne | błąd rekonstrukcji | **NIEPORÓWNYWALNE: brak zadania koreferencji**, — | 2016 | goodfellow_2016_deep |
| sparse AE | dane ogólne | rekonstrukcja + kara rzadkości | **NIEPORÓWNYWALNE: brak zadania koreferencji**, — | 2016 | goodfellow_2016_deep |
| fine-tuned Llama 3.1-8B | CorefUD 1.3, 22 zbiory / 17 języków | CoNLL F1 | — | 2025 | hejman_2025_llama |
| GLaRef pairwise | CRAC 2025 test | średni CoNLL F1 | 61,57; <10% kosztu wariantu LLM | 2025 | seminck_2025_glaref |
| GLaRef generatywny | CRAC 2025 test | średni CoNLL F1 | 62,96 | 2025 | seminck_2025_glaref |
| Gemini 2.5 Pro few-shot | CRAC 2025 mini-test, wiele języków | CoNLL F1 | **NIEPORÓWNYWALNE: mini-test**, 61,74 | 2025 | sajid_2025_fewshot |
| GPT-4 jako anotator | cross-document event coreference | zgodność / klasyfikacja par | **NIEPORÓWNYWALNE: koreferencja zdarzeń**, poziom porównywalny z przeszkolonymi anotatorami | 2023 | zhao_2023_gpt |
| LLM-rationales + student | ECB+, GVC, AIDA Phase 1 | B³ F1 | **NIEPORÓWNYWALNE: koreferencja zdarzeń**, SOTA według autorów bez przepisanej liczby | 2024 | nath_2024_rationale |
| VGAE | grafy cytowań | AUC/AP predykcji krawędzi | **NIEPORÓWNYWALNE: zadanie grafowe**, — | 2016 | kipf_2016_vgae |
| U-Net | ISBI, obrazy biomedyczne | segmentacja / czas | **NIEPORÓWNYWALNE: obrazy**, zwycięstwo w zadaniu bez przepisanej liczby | 2015 | ronneberger_2015_unet |
| DEC | MNIST, USPS, REUTERS-10K, STL-10 | ACC/NMI | **NIEPORÓWNYWALNE: klastrowanie obrazów/tekstu**, — | 2016 | xie_2016_dec |
| VAE | MNIST, Frey Face | ELBO / log-likelihood | **NIEPORÓWNYWALNE: model generatywny**, — | 2013 | kingma_2013_vae |
| mention-pair | MUC-6/MUC-7 | MUC | — | 2001 | soon_2001_machine |
| multi-pass sieve | ACE + OntoNotes | MUC/B³/CEAF | — | 2010 | raghunathan_2010_sieve |
| entity-based RNN | CoNLL-2012 / OntoNotes | CoNLL score | +0,8 pkt względem wcześniejszego SOTA | 2016 | wiseman_2016_global |
| e2e-coref | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | +1,5 pkt; ensemble +3,1 pkt względem wcześniejszego SOTA | 2017 | lee_2017_e2e |
| c2f-coref, ELMo | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 73,0; wartość z tabeli wtórnej Maverick | 2018 | lee_2018_higher |
| SpanBERT + c2f-coref | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 79,6 | 2020 | joshi_2020_spanbert |
| wl-coref, RoBERTa-large | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 81,0; wartość z tabeli wtórnej Maverick | 2021 | dobrovolskii_2021_word |
| s2e-coref | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 80,3; wartość z tabeli wtórnej Maverick | 2021 | kirstain_2021_s2e |
| LingMess | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 81,4; wartość z tabeli wtórnej Maverick | 2023 | otmazgin_2023_lingmess |
| ASP, FLAN-T5 XXL | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 82,5 | 2022 | liu_2022_asp |
| Link-Append, mT5-XXL | CoNLL-2012 English | CoNLL F1 | 83,3 | 2023 | bohnet_2023_linkappend |
| seq2seq tagged text, T0-XXL | OntoNotes 5.0 / CoNLL-2012 | CoNLL F1 | 83,2 | 2023 | zhang_2023_seq2seq |
| Maverick | OntoNotes 5.0 / CoNLL-2012 | efektywność + CoNLL F1 | SOTA w publikacji; do 0,006× pamięci treningowej, 170× szybsza inferencja | 2024 | martinelli_2024_maverick |
| F-coref | OntoNotes | czas 2,8 tys. dokumentów | 25 s; LingMess 6 min; AllenNLP 12 min | 2022 | otmazgin_2022_fcoref |
| LLM instrukcyjny | Polish Coreference Corpus | instruction--answer alignment | **NIEPORÓWNYWALNE: inna procedura oceny**, — | 2024 | saputa_2024_pcc_llm |
| IKAR | KPWr | B³ / MUC / BLANC F1 | **NIEPORÓWNYWALNE: węższa definicja anafory**, 93,89% / 83,67% / 83,61% | 2012 | broda_2012_ikar |
| U-Net 1D + transfer | syntetyczne krzywe, 1400 próbek | IoU | **NIEPORÓWNYWALNE: szeregi czasowe**, 50,96% od zera; 71,95% po transferze | 2019 | wen_2019_time |
| IDEC | zbiory obrazowe i tekstowe | ACC/NMI | **NIEPORÓWNYWALNE: klastrowanie ogólne**, — | 2017 | guo_2017_idec |

## Wnioski z porównania

Jedyną względnie spójną grupą liczbową są wyniki na OntoNotes 5.0 / CoNLL-2012, lecz nawet w niej część wartości pochodzi z tabeli wtórnej i różni się enkoderem, zasobami oraz implementacją scorera. Wyniki CRAC 2025 używają CorefUD 1.3 i osobnych tracków; mini-test Sajida i in. nie jest pełnym testem. Wyniki IKAR dotyczą KPWr i innej definicji zadania, a prace o zdarzeniach, grafach, obrazach, szeregach i klastrowaniu są wyłącznie uzasadnieniem mechanizmu. Tabela nie zawiera własnych wyników projektu.

## Audyt bibliografii

Automatyczny audyt wykazał 57 wpisów, 57 unikatowych kluczy, 57 pól z datą weryfikacji 2026-09-03 oraz brak wpisów pozbawionych URL lub DOI. Nie znaleziono niezdefiniowanych kluczy użytych przez polecenia cytowania w notatkach. Nie wykonano dodatkowych pobrań w limicie S-02f, ponieważ żadna pozycja nie wymagała uzupełnienia pola weryfikacji. Docelowy zakres 45--60 został osiągnięty; brak wynosi 0 pozycji. Najsłabiej pokrytym obszarem pozostają bezpośrednie zastosowania autokoderów do koreferencji, dla których nie znaleziono publikacji odnoszącej się równocześnie do polszczyzny i domeny prawnej.
