# Summary

Dutch-OpenBoek is a conversion of the OpenBoek corpus, a coreference-annotated corpus of Dutch public-domain literary texts.
The corpus consists of long documents from various Dutch novels.

## References

```
@article{openboek,
    title = "OpenBoek: A Corpus of Literary Coreference and Entities with an Exploration of Historical Spelling Normalization",
    author = "{van Cranenburgh}, Andreas and {van Noord}, Gertjan",
    year = "2022",
    month = dec,
    day = "22",
    language = "English",
    volume = "12",
    pages = "235–251",
    journal = "Computational Linguistics in the Netherlands Journal",
    issn = "2211-4009",
    publisher = "Brill",
    url = "https://clinjournal.org/clinj/article/view/157",
}
```

# Changelog

### 2026-02-18 v1.4
  * initial conversion
  * converted from CoNLL-2012 format
  * fixes to provide a perfect alignment between the annotated data and the original texts
  * entity type annotations converted
  * morpho-syntactic attributes produced by UDPipe 2 using UD 2.17 models

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.4
License: CC BY 4.0
Includes text: yes
Genre: fiction literary
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: van Cranenburgh, Andreas (1); Novák, Michal (2)
Contributors' affiliations: (1) Center for Language and Cognition, University of Groningen, The Netherlands
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Other contributors: van Noord, Gertjan
Contributing: elsewhere
Contact: a.w.van.cranenburgh@rug.nl
===============================================================================
```
