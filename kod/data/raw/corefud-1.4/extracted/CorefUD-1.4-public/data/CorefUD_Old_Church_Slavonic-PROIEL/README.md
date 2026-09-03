# Summary

Old_Church_Slavonic-PROIEL is based on canonical Old Church Slavonic data from the PROIEL and TOROT treebanks.

## References
```
@incollection{HaugJohndal2008,
  author    = {Dag Haug and Marius L. Jøhndal},
  booktitle = {Proceedings of the Language Technology for Cultural Heritage Data Workshop (LaTeCH 2008), Marrakech, Morocco, 1 June 2008},
  editor    = {Caroline Sporleder and Kiril Ribarov and Antal van den Bosch and Milena P. Dobreva and Matthew James Driscoll and Claire Grover and Piroska Lendvai and Anke Luedeling and Marco Passarotti},
  location  = {Marrakech},
  pages     = {27--34},
  publisher = {ELRA},
  title     = {Creating a Parallel Treebank of the Old Indo-European Bible Translations},
  year      = {2008}
}

@article{Eckhoff-Hanne2015-287287,
	title        = {Linguistics vs. digital editions: The Tromsø Old Russian and OCS Treebank},
	journal      = {Scripta & e-Scripta},
	author       = {Eckhoff, Hanne and Berdicevskis, Aleksandrs},
	year         = {2015},
	number       = {14-15},
	pages        = {9--25},
}
```

# Changelog

### 2024-03-28 v1.2
  * initial conversion
  * Only the Codex Marianus and selected chapters (1, 2 and 14) of Suprasliensis were
    converted to CorefUD 1.2
    The UD_Old_Church_Slavonic-PROIEL treebank includes also documents
    (Kiev Missal, Psalms, Zographensis), but these lack coreference annotation.
  * UD document boundaries are marked (using the `newdoc` annotations).
  * Some coreference links were lost during the conversion because:
    - There were problems converting the original sentences to CoNLL-U.
    - The links were crossing train/dev/test files boundaries.
  * The original annotation marks only mention heads, so the span was guessed heuristically
    using the Udapi block `corefud.GuessSpan`.

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.2
License: CC BY-NC-SA 4.0
Includes text: yes
Genre: bible
Lemmas: converted from manual
UPOS: converted from manual
XPOS: manual native
Features: converted from manual
Relations: converted from manual
CorefUD contributors: Haug, Dag (1); Eckhoff, Hanne (2); Popel, Martin (3)
Other contributors:
Contributors' affiliations: (1) University of Oslo, Department of Linguistics and Scandinavian Studies, Oslo, Norway
                            (2) University of Oxford, Faculty of Medieval and Modern Languages, Oxford, UK
                            (3) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: hanne.eckhoff@mod-langs.ox.ac.uk
===============================================================================
```
