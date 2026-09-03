# Summary

English-FantasyCoref is a conversion of the FantasyCoref corpus, a coreference-annotated corpus of English fairy tales and fantasy literature.
Although the current conversion includes texts from Grimms' Household Tales (GFT\_split1), the original corpus also contains Arabian Nights, and Alice in Wonderland, all sourced from Project Gutenberg.

## References

```
@inproceedings{han-etal-2021-fantasycoref,
    title = "{F}antasy{C}oref: Coreference Resolution on Fantasy Literature Through Omniscient Writer{'}s Point of View",
    author = "Han, Sooyoun  and
      Seo, Sumin  and
      Kang, Minji  and
      Kim, Jongin  and
      Choi, Nayoung  and
      Song, Min  and
      Choi, Jinho D.",
    booktitle = "Proceedings of the Fourth Workshop on Computational Models of Reference, Anaphora and Coreference",
    month = nov,
    year = "2021",
    address = "Punta Cana, Dominican Republic",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2021.crac-1.3/",
    doi = "10.18653/v1/2021.crac-1.3",
    pages = "24--35",
}
```

# Changelog

### 2026-02-18 v1.4
  * initial conversion
  * converted from CoNLL-2012 format
  * source data: GFT\_split1
  * fixes to provide a perfect alignment between the annotated data and the original texts
    * ad-hoc fixes in texts
    * quotation marks
  * fixed ill-nested mentions in the original annotations
  * morpho-syntactic attributes produced by UDPipe 2 using UD 2.17 models

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.4
License: CC BY-SA 4.0
Includes text: yes
Genre: fiction fairy-tales
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Han, Sooyoun (1); Seo, Sumin (1); Novák, Michal (2)
Contributors' affiliations: (1) Yonsei University, Department of Digital Analytics, Seoul, South Korea 
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Other contributors: Kang, Minji; Kim, Jongin; Choi, Nayoung; Song, Min; Choi, Jinho D.
Contributing: elsewhere
Contact: mnovak@ufal.mff.cuni.cz
===============================================================================
```
