# Summary

Czech-PCEDT is based on the PCEDT portion of Prague Dependency Treebank - Consolidated 2.0 (PDT-C),
created at the Charles University, Prague. The texts are manual translations of the texts from the
Wall Street Journal section of Penn Treebank.

## References

```
@inproceedings{udpdtc,
  author    = {Marie Mikulová and Barbora Štěpánková and Daniel Zeman and Jan Štěpánek and Milan Straka and Jan Hajič},
  title     = {Meet {UD_Czech-PDTC}: A Large and Genre-Rich Treebank in {Universal Dependencies}},
  booktitle = {Proceedings of the 15th International Conference on Language Resources and Evaluation (LREC 2026)},
  publisher = {European Language Resources Association},
  address   = {Palma, Spain},
  year      = 2026,
}

@inproceedings{pcedt2.0coref,
    author = {Nedoluzhko, Anna and Nov{\'a}k, Michal and Cinkov{\'a}, Silvie and Mikulov{\'a}, Marie and M{\'\i}rovsk{\'y}, Ji{\v{r}}{\'\i}},
    title = {Coreference in {P}rague {C}zech-{E}nglish {D}ependency {T}reebank},
    booktitle = {Proceedings of the Tenth International Conference on Language Resources and Evaluation ({LREC}'16)},
    publisher = {European Language Resources Association (ELRA)},
    address = {Portoro{\v{z}}, Slovenia},
    year = {2016},
    pages = {169--176},
}
```

# Changelog

### 2026-02-18 v1.4
  * updated data to match UD Czech-PDTC in version 2.17
  * the dataset is no longer parsed as it uses manual annotation from PDT-C 2.0
### 2025-04-17 v1.3
  * morpho-syntactic attributes updated using UD 2.15 models
### 2024-03-28 v1.2
  * the morpho-syntactic features are no longer converted from the PCEDT a-layer (which has been automatically parsed by an outdated method),
    but parsed by UDPipe 2 using the `czech-pdt-ud-2.12-230717` model
  * Coreference annotation: If a bracket is in mention span, the paired bracket is added too, if possible.
  * Added the enhanced relation subtype nsubj:xsubj.
  * More restrictive use of orphans and empty nodes: Not in non-verbal coordinated sentences.
### 2023-02-24 v1.1
  * Removed superfluous empty nodes #Rcp, #Cor, #QCor.
  * Removed empty nodes depending on the artificial 0:root.
  * "Bych/bys/by/bychom/byste" in MWTs no longer breaks mention spans.
  * Improved guessing of pronominal forms for empty nodes.
  * Functors added also to non-empty nodes.
### 2022-04-06 v1.0
  * new format of coreference and anaphora annotations
  * harmonization of train/dev/test split for corpora containing WSJ documents
  * Improved conversion from the Prague format, reduced number of discontinuous mentions.
  * Case-enhanced dependency relations made more consistent.
### 2021-12-10 v0.2
  * Fixed attachment of punctuation where required by the UD guidelines.
### 2021-03-11 v0.1
  * initial conversion

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 0.1
License: CC BY-NC-SA 4.0
Includes text: yes
Genre: news
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Zeman, Daniel (1); Mikulová, Marie (1); Štěpánková, Barbora (1); Štěpánek, Jan (1); Straka, Milan (1); Hajič, Jan (1); Nedoluzhko, Anna (1); Novák, Michal (1); Cinková, Silvie (1)
Contributors' affiliations: (1) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Other contributors: Bémová, Alevtina; Buráňová, Eva; Hajičová, Eva; Havelka, Jiří; Hlaváčová, Jaroslava; Kárník, Jiří; Kolářová, Veronika; Kučová, Lucie; Lopatková, Markéta; Mírovský, Jiří; Pajas, Petr; Panevová, Jarmila; Sgall, Petr; Ševčíková, Magda; Urešová, Zdeňka; Vidová Hladká, Barbora; Žabokrtský, Zdeněk
Contributing: elsewhere
Contact: nedoluzko@ufal.mff.cuni.cz
===============================================================================
```
