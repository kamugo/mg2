# Summary

Ancient_Hebrew-PTNK contains portions of the Biblia Hebraic Stuttgartensia with morphological annotations from ETCBC and manual annotations of syntax and coreference.

## References

```
@inproceedings{swanson-tyers-2022-universal,
    title = {A {U}niversal {D}ependencies Treebank of {A}ncient {H}ebrew},
    author = {Swanson, Daniel and Tyers, Francis},
    booktitle = {Proceedings of the Thirteenth Language Resources and Evaluation Conference},
    month = jun,
    year = {2022},
    address = {Marseille, France},
    publisher = {European Language Resources Association},
    url = {https://aclanthology.org/2022.lrec-1.252},
    pages = {2353--2361},
}
```

# Changelog

### 2024-03-28 v1.2
  * initial conversion
  * The dev set contains Genesis 1-18, test set Genesis 19-30, train set Genesis 31-40.
    So the train set is now smaller than dev and test, but this should be improved
    in future releases, once the annotation of Genesis 41-50 and Ruth 1-4 is finished.
  * The original annotation contains some entities across several chapters.
    We have decided to make each chapter a document (newdoc), so we need to split such entities
    using `corefud.FixEntityAcrossNewdoc`
    (but there is an alternative option to make each file a single document).

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.2
License: CC BY-NC 4.0
Includes text: yes
Genre: bible
Lemmas: converted from manual
UPOS: converted from manual
XPOS: manual native
Features: converted from manual
Relations: manual native
CorefUD contributors: Swanson, Daniel (1); Popel, Martin (2)
Other contributors: Bryce Bussert
Contributors' affiliations: (1) Indiana University, Department of Linguistics, Bloomington, USA
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: dangswan@iu.edu
===============================================================================
```
