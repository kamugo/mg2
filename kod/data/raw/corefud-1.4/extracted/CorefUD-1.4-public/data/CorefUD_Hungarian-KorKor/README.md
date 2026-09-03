# Summary

Hungarian-KorKor is a conversion of KorKor, a coreference annotated corpus of Hungarian created at the Hungarian Research Centre for Linguistics.

## References

```
@inproceedings{korkor_mszny,
    author = {Vad{\'a}sz, No{\'e}mi},
    title = {{K}or{K}orpusz: k{\'e}zzel annot{\'a}lt, többr{\'e}teg\H{u} pilotkorpusz {\'e}p{\'i}t{\'e}se},
    booktitle = {{XVI}. {M}agyar {S}z{\'a}m{\'i}t{\'o}g{\'e}pes {N}yelv{\'e}szeti {K}onferencia ({MSZNY} 2020)},
    editor = {Berend, G{\'a}bor and Gosztolya, G{\'a}bor and Vincze, Veronika},
    publisher = {Szegedi Tudom{\'a}nyegyetem, TTIK, Informatikai Int{\'e}zet},
    address = {Szeged},
    year = {2020},
    pages = {141--154}
}

@inproceedings{korkor_coling,
    author = {Vad{\'a}sz, No{\'e}mi},
    title = {Building a Manually Annotated {H}ungarian Coreference Corpus: Workflow and Tools},
    booktitle = {Proceedings of the Fifth Workshop on Computational Models of Reference, Anaphora and Coreference},
    month = {oct},
    year = {2022},
    address = {Gyeongju, Republic of Korea},
    publisher = {Association for Computational Linguistics},
    url = {https://aclanthology.org/2022.crac-1.5},
    pages = {38--47}
}
```


# Changelog

### 2026-02-18 v1.4
  * morpho-syntactic attributes updated using UD 2.17 models
### 2025-04-17 v1.3
  * morpho-syntactic attributes updated using UD 2.15 models
  * conversion into CorefUD (from `xtsv` files to `conllu`)
    almost completely rewritten (hopefully simplified and improved, see below)
    by Martin Popel (using a single Udapi reader block `xtsv.py`,
    which is currently stored in the CorefUD private repo,
    but could be moved to the Udapi public repo if needed).
  * KOPULA nodes (empty copula verbs) are now deleted as required in UD
  * Original deprel values are used in the conversion (although they are
    still overwritten by UDPipe in the end when re-parsing).
    Most notably, DROP empty nodes are now distinguished (in enhanced dependencies)
    using the following mapping of deprels into UD values:
    SUBJ=nsubj, OBJ=obj, POSS=nmod:att.
    In the previous versions, all empty nodes had deprel=dep
    (so they could not be distinguished in the CRAC shared tasks,
    where forms of empty nodes are deleted).
  * Conversion of `ZÉRÓ_*` nodes into empty nodes has been improved as well.
  * The `coreftype=holo` annotation is now converted into CorefUD-style bridging (relation `part`).
    These were ignored/deleted in the previous versions.
  * Other `coreftype` values (prs, coref, rel,...) are stored in `mention.other["coreftype"]`.
  * `sent_id` uses the document name as prefix
    (e.g. `sent_id = huwiki_12-5` is the 5th sentence of `huwiki_12`).
### 2024-03-28 v1.2
  * morpho-syntactic attributes updated using UD 2.12 models
### 2023-02-24 v1.1
  * initial conversion

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.1
License: CC BY 4.0
Includes text: yes
Genre: news, Wikipedia
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Vadász, Noémi (1); Žabokrtský, Zdeněk (2); Popel, Martin (2)
Contributors' affiliations: (1) Hungarian Research Centre for Linguistics, Research Group for Language Technology, Budapest, Hungary
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: vadasz.noemi@nytud.hu
===============================================================================
```
