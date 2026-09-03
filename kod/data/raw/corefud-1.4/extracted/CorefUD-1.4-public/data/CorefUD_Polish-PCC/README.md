# Summary

Polish-PCC is a conversion of Polish Coreference Corpus, a coreference-annotated
corpus of Polish built upon the National Corpus of Polish (Przepiórkowski et al., 2012).

## References

```
@inproceedings{PCC2013,
    author    = {Maciej Ogrodniczuk and Katarzyna Glowińska and Mateusz Kopeć and Agata Savary and Magdalena Zawisławska},
    title     = {Polish Coreference Corpus},
    booktitle = {Human Language Technology. Challenges for Computer Science and Linguistics - 6th Language and Technology Conference, {LTC} 2013, Pozna{\'{n}}, Poland, December 7-9, 2013. Revised Selected Papers},
    series    = {Lecture Notes in Computer Science},
    volume    = {9561},
    pages     = {215--226},
    publisher = {Springer},
    year      = {2013},
}

@book{PCC-book,
    author = {Ogrodniczuk, Maciej and Głowińska, Katarzyna and Kopeć, Mateusz and Savary, Agata and Zawisławska, Magdalena},
    title = {Coreference in {P}olish: Annotation, Resolution and Evaluation},
    publisher = {Walter De Gruyter},
    isbn = {978-1-61451-835-8},
    year = {2015},
}
```

# Changelog

### 2026-02-18 v1.4
  * morpho-syntactic attributes updated using UD 2.17 models
### 2025-04-17 v1.3
  * morpho-syntactic attributes updated using UD 2.15 models
### 2024-03-28 v1.2
  * morpho-syntactic attributes updated using UD 2.12 models
  * improved conversion of empty nodes (zeros), distinguishing three types:
    - EmptyType=NullSubjAglt, e.g. in "dowiedział em" the clitic "em" is an auxiliary verb,
      but the nsubj coreference (if present on the clitic) is moved to a newly created empty node
      in CorefUD. This node is positioned before the verb ("dowiedział"), which forms
      a multiword token together with the clitic ("dowiedziałem").
    - EmptyType=NullSubjVerbal, empty nodes created for single-word verbal mentions
      (again before the verb).
    - EmptyType=Ellipsis, the original annotation contains special Ø words,
      which are converted to empty nodes in CorefUD
### 2023-02-24 v1.1
  * morpho-syntactic attributes updated using UD 2.10 models
### 2022-04-06 v1.0
  * new format of coreference and anaphora annotations
### 2021-12-10 v0.2
  * morpho-syntactic attributes updated using UDPipe 2 with UD 2.6 models
### 2021-03-11 v0.1
  * initial conversion

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 0.1
License: CC BY 3.0
Includes text: yes
Genre: literature news journals conversations web
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Ogrodniczuk, Maciej (1); Žabokrtský, Zdeněk (2); Popel, Martin (2)
Other contributors: Kopeć, Mateusz; Savary, Agata
Contributors' affiliations: (1) Polish Academy of Sciences, Institute of Computer Science, Warsaw, Poland
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: maciej.ogrodniczuk@ipipan.waw.pl
===============================================================================
```
