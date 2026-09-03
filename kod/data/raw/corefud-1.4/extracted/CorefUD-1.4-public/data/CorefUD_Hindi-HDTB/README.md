# Summary

Hindi-HDTB is derived from the HDTB data annotated with coreference and anaphoric relations, as created at IIIT Hyderabad, India.

The train/dev/test split follows the division proposed by UD_Hindi-HDTB. However, there is no direct sentence or document ID correspondence between the UD treebank and the original coreference corpus. To establish alignment, we matched sentences based on surface forms. While approximately 14% of sentences from the coreference corpus are not present in the UD treebank, at least one sentence from each coreference-annotated document is included.

For now, sentence IDs cannot be used to match sentences between the datasets, as Hindi-HDTB indexes them differently. Additionally, we do not currently incorporate the manually annotated morpho-syntactic information from the UD treebank; instead, we replace it with automatic parses produced by UDPipe 2.

The CorefUD conversion of coreference and anaphora annotations has been simplified. Coreferential mentions and entities are derived solely from the 2nd column (`cref`) of the original format. Since the 7th column (`crefType`), which annotates relation types, is not considered, some mentions may be incorrectly grouped into the same entity instead of being linked by bridging anaphora or split antecedent relations (`Coreference-PartOf` and `Coreference-RPartOf`).

Additionally, certain relation types, such as `Coreference-NounComplement` and `Coreference-Apposition`, should be handled differently in future versions. Specifically, we may consider merging mentions involved in these relations into a single mention.

## References

```
@inproceedings{mujadia-etal-2016-coreference,
    title = "Coreference Annotation Scheme and Relation Types for {H}indi",
    author = "Mujadia, Vandan  and
      Gupta, Palash  and
      Sharma, Dipti Misra",
    booktitle = "Proceedings of the Tenth International Conference on Language Resources and Evaluation ({LREC}`16)",
    month = may,
    year = "2016",
    address = "Portoro{\v{z}}, Slovenia",
    publisher = "European Language Resources Association (ELRA)",
    url = "https://aclanthology.org/L16-1025/",
    pages = "161--168",
}
```

# Changelog

### 2026-02-18 v1.4
  * morpho-syntactic attributes updated using UD 2.17 models
### 2025-04-17 v1.3
  * initial conversion
  * morpho-syntactic attributes produced by UDPipe 2 using UD 2.15 models
  * simplified conversion of coreference and anaphora annotations

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.3
License: CC BY-NC-SA 4.0
Includes text: yes
Genre: news
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Mujadia, Vandan (1); Novák, Michal (2)
Other contributors: Gupta, Palash; Sharma, Dipti Misra
Contributors' affiliations: (1) Kohli Center on Intelligent Systems, International Institute of Information Technology, Hyderabad, India
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: mnovak@ufal.mff.cuni.cz
===============================================================================
```
