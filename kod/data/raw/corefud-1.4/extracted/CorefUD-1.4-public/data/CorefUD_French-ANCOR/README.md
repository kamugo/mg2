# Summary

French-ANCOR is a French spoken corpus annotated with coreference.
The annotation was conducted on three different corpora of conversational speech (Accueil_UBS, OTG, ESLO).
The original corpus can be downloaded from [here](https://www.ortolang.fr/market/corpora/ortolang-000903).

## References

```
@inproceedings{muzerelle-etal-2014-ancor,
    title = "{ANCOR}{\_}{C}entre, a large free spoken {F}rench coreference corpus: description of the resource and reliability measures",
    author = {Muzerelle, Judith  and
      Lefeuvre, Ana{\"i}s  and
      Schang, Emmanuel  and
      Antoine, Jean-Yves  and
      Pelletier, Aurore  and
      Maurel, Denis  and
      Eshkol, Iris  and
      Villaneau, Jeanne},
    booktitle = "Proceedings of the Ninth International Conference on Language Resources and Evaluation ({LREC}`14)",
    month = may,
    year = "2014",
    address = "Reykjavik, Iceland",
    publisher = "European Language Resources Association (ELRA)",
    url = "https://aclanthology.org/L14-1169/",
    pages = "843--847",
}

@misc{11403/ortolang-000903/v3,
    title = {Corpus ANCOR Centre Version TEI},
    author = {LIFAT and LLL and Lattice},
    url = {https://hdl.handle.net/11403/ortolang-000903/v3},
    note = {{ORTOLANG} ({Open} {Resources} {and} {TOols} {for} {LANGuage}) \textendash www.ortolang.fr},
    copyright = {Licence Creative Commons Attribution - Pas d'Utilisation Commerciale - Partage dans les Mêmes Conditions 4.0 International},
    year = {2024}
}
```

# Changelog

### 2026-02-18 v1.4
  * morpho-syntactic attributes updated using UD 2.17 models
### 2025-04-17 v1.3
  * initial conversion from the TEI format by Kirill Milintsevich
  * Martin Popel helped to detect ill-nested mentions, Kirill fixed manually
  * Cross-sentence mentions are ignored in the conversion.

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.3
License: CC BY-NC-SA 4.0
Includes text: yes
Genre: spoken
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Muzerelle, Judith (1); Milintsevich, Kirill (2); Popel, Martin (3)
Other contributors: Grobol, Loïc
Contributors' affiliations: (1) Université d'Orléans, LLL UMR 7270, France
                            (2) Institut National de l'Audiovisuel, Bry-sur-Marne, France
                            (3) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: kmilintsevich@ina.fr
===============================================================================
```
