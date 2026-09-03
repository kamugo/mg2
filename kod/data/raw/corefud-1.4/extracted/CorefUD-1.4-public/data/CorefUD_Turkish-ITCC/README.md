# Summary

Turkish-ITCC contains a conversion of coreference annotations of 24 Turkish documents [1, 2]. The annotations include overt and implicit mentions (e.g., dropped pronouns and null subjects) with their coreferential relations.

Update history of the dataset is as follows:

2023 - The annotations for dropped pronouns and null subjects were added and the data was also reannotated to eliminate missing annotations.
2022 - The data converted to CorefUD format and included in the CorefUD v1.1 release by [ITU NLP Group](http://www.nlp.itu.edu.tr/).
2018 - the data in CoNLL format. Only 24 documents from the previous version could have been continued to be used due to alignment issues between the annotations and the original text in [2].
2017 - first coreference annotations in XML format on 33 documents selected from METU Turkish Corpus (MC) [2].


## References
```
[1] @article{pamayTurkishCR,
  title={Enhancing {T}urkish Coreference Resolution: Insights from deep learning, dropped pronouns, and multilingual transfer learning},
  author={Pamay Arslan, Tu{\u{g}}ba and Eryi{\u{g}}it, G{\"u}l{\c{s}}en},
  journal={Computer Speech \& Language},
  year={2024},
  doi = {https://doi.org/10.1016/j.csl.2024.101681}
}

[2] @conference{odtuCorpus,
	title={Development of a corpus and a treebank for present-day written Turkish},
	author={Say, Bilge and Zeyrek, Deniz and Oflazer, Kemal and {\"O}zge, Umut},
	booktitle={Proceedings of the 11th International Conference of Turkish Linguistics},
	pages={183--192},
	address = {Northern Cyprus},
	year={2002}
}
```

# Changelog

### 2024-03-28 v1.2
  * issues and gaps in the coreference annotation fixed
  * coreference of zeros annotated
  * in the automatically parsed sentences, morpho-syntactic attributes updated using the `turkish-imst-ud-2.12-230717` model
### 2023-02-24 v1.1
  * initial conversion
  * some of the paragraphs completely lack the annotation of coreference
  * coreference in some of the paragraphs is annotated only partially
  * coreference of zeros is missing
  * there is an overlap between sentences from Turkish-ITCC and UD_Turkish-IMST. The gold-standard morpho-syntactic annotations of these sentences were directly taken from the UD_Turkish-IMST.
    For the rest, this annotation was automatically obtained by running UDPipe 2 with the `turkish-imst-ud-2.10-220711` model.
```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.1
License: CC BY-NC-SA 4.0
Includes text: yes
Genre: essay, news, article, story, novel
Lemmas: partially automatic
UPOS: partially automatic
XPOS: partially automatic
Features: partially automatic
Relations: partially automatic
CorefUD contributors: Pamay Arslan, Tuğba (1); Acar, Kutay (2); Eryiğit, Gülşen (1); Novák, Michal (3)
Contributors' affiliations: (1) Istanbul Technical University, Department of Artificial Intelligence and Data Engineering, Istanbul, Turkey
                            (2) Istanbul Technical University, Department of Computer Engineering, Istanbul, Turkey
                            (3) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: here
Contact: pamay@itu.edu.tr
===============================================================================
```
