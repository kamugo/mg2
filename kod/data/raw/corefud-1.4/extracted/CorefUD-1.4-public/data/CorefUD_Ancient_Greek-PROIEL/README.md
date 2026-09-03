# Summary

Ancient_Greek-PROIEL is converted from the Ancient Greek data in the PROIEL treebank and consists of the New Testament gospels,
which were annotated for information structure in the PROIEL project (2008-2012).

## References

```
@incollection{HaugJohndal2008,
  author    = {Dag Haug and Marius L. Jøhndal},
  booktitle = {Proceedings of the Language Technology for Cultural Heritage Data Workshop (LaTeCH 2008), Marrakech, Morocco, 1 June 2008},
  editor    = {Caroline Sporleder and Kiril Ribarov and Antal van den Bosch and Milena P. Dobreva and Matthew James Driscoll and Claire Grover and Piroska Lendvai and Anke Luedeling and Marco Passarotti},
  location  = {Marrakech},
  pages     = {27--34},
  publisher = {European Language Resources Association},
  title     = {Creating a Parallel Treebank of the Old Indo-European Bible Translations},
  year      = {2008}
}
```

# Changelog

### 2024-03-28 v1.2
  * initial conversion
  * Only Greek_(MARK|JOHN|MATT|LUKE) gospels were converted to CorefUD 1.2
    The UD_Ancient_Greek-PROIEL treebank includes also selections from Herodotus,
    but these lack coreference annotation.
  * UD document boundaries are marked (using the `newdoc` annotations),
    so that the maximal continuous sequence of chapters from each book is kept in one document.
    E.g. the dev set contains chapter 5 of MATT in a document `newdoc id = Greek_MATT5`.
    The train set includes chapters 1-4 and 7-28 of MATT, which are separated into two documents
    `newdoc id = Greek_MATT1-4` and `newdoc id = Greek_MATT7-28`).
    An alternative would be to separate each chapter into one document, but that would mean
    loosing coreference links crossing chapter boundaries (e.g. between MATT 1 and MATT 2).
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
Genre: bible nonfiction
Lemmas: converted from manual
UPOS: converted from manual
XPOS: manual native
Features: converted from manual
Relations: converted from manual
CorefUD contributors: Haug, Dag (1); Popel, Martin (2)
Other contributors: Eckhoff, Hanne; Fortscher, Miachel; Majer, Marek; Müth, Angelika; Welo, Eirik
Contributors' affiliations: (1) University of Oslo, Department of Linguistics and Scandinavian Studies, Oslo, Norway
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: daghaug@ifikk.uio.no
===============================================================================
```
