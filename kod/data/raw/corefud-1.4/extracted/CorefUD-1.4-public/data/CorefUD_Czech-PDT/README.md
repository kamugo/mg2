# Summary

Czech-PDT is based on the written (PDT) portion of Prague Dependency Treebank - Consolidated 2.0 (PDT-C),
created at the Charles University, Prague.

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
```

# Changelog

### 2026-02-18 v1.4
  * updated data to match UD Czech-PDTC in version 2.17
### 2025-04-17 v1.3
  * 2025-05-15 v2.16
    * Source data is now PDT-C 2.0 (previously it was 1.0).
    * Adjectives heading clauses are acl(:relcl) rather than amod.
    * Fixed attachment of bracketed punctuation.
    * Fixed multiword expressions need the ExtPos feature.
    * Fixed: demonstratives with clauses: det --> nmod.
    * Fixed: genitive postmodifiers should be nmod (not amod, nummod, det).
    * More generally, non-agreeing postponed determiners are now mostly nmod.
    * No longer distinguishing flat:foreign from flat.
  * 2024-11-15 v2.15
    * Nouns no longer distinguish Polarity. Negative nouns have negative lemmas.
    * Conditional auxiliary "by" does not have Person (besides 3, it could be also 2).
    * Short forms of adjectives now have Degree=Pos (instead of no Degree).
    * Disambiguated NumType=Mult,Sets.
    * Fixed conversion of "Cz" tags from PDT (not interrogative DET but cardinal NUM).
### 2024-03-28 v1.2
  * Improved distinction between adverbial predicates (with copula) and adverbial modifiers.
  * Coreference annotation: If a bracket is in mention span, the paired bracket is added too, if possible.
  * More restrictive use of orphans and empty nodes: Not in non-verbal coordinated sentences.
  * Fixed crossing coreference mentions.
  * Fixed treatment of "by" in aux/cop chains.
  * Improved form and position of abstract predicates in gapping.
  * Removed NumValue from all Czech UD treebanks.
  * Pseudo-existential "být" with oblique/adverbial modifiers changed to copula.
  * Source data switched from PDT 3.0 to PDT-C 1.0.
    * Underlying text data is the same.
    * Changed some aspects of lemmatization, including LId and other attributes in MISC.
    * Somewhat different XPOS tag set.
    * UD features: now all verbs have Aspect; minor changes at various other places.
    * Foreign words are now systematically tagged X (previously, many of them had descriptive UPOS tags).
  * The tectogrammatical (t-) layer of source annotation is now used for documents for which it is available.
    * Sentences converted with the help of t-layer have the comment "Tectogrammatical annotation available."
    * There are more enhanced dependency relations and empty nodes.
    * The MISC column contains tectogrammatical functors.
  * Temporary fix of double subjects (second subject converted to dep).
    In the long run, the cause should be found and fixed upstream.
  * Added the enhanced relation subtype nsubj:xsubj.
### 2023-02-24 v1.1
  * Added VerbForm=Part|Voice=Pass to long forms of passive participles.
  * Added VerbForm=Vnoun to verbal nouns.
  * The verb 'být' is now AUX in all contexts.
  * Merged PRON/DET 'sám', 'samý'.
  * Removed superfluous empty nodes #Rcp, #Cor, #QCor.
  * Removed empty nodes depending on the artificial 0:root.
  * "Bych/bys/by/bychom/byste" in MWTs no longer breaks mention spans.
  * Improved guessing of pronominal forms for empty nodes.
  * Functors added also to non-empty nodes.
  * Temporary fix of double subjects (second subject converted to dep).
    In the long run, the cause should be found and fixed upstream.
  * Added the enhanced relation subtype nsubj:xsubj.
### 2022-04-06 v1.0
  * new format of coreference and anaphora annotations
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
Genre: news reviews nonfiction
Lemmas: converted from manual
UPOS: converted from manual
XPOS: manual native
Features: converted from manual
Relations: converted from manual
CorefUD contributors: Zeman, Daniel (1); Mikulová, Marie (1); Štěpánková, Barbora (1); Štěpánek, Jan (1); Straka, Milan (1); Hajič, Jan (1)
Contributors' affiliations: (1) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Other contributors: Bémová, Alevtina; Buráňová, Eva; Hajičová, Eva; Havelka, Jiří; Hlaváčová, Jaroslava; Kárník, Jiří; Kolářová, Veronika; Kučová, Lucie; Lopatková, Markéta; Mírovský, Jiří; Nedoluzhko, Anna; Novák, Michal; Pajas, Petr; Panevová, Jarmila; Sgall, Petr; Ševčíková, Magda; Urešová, Zdeňka; Vidová Hladká, Barbora; Žabokrtský, Zdeněk
Contributing: elsewhere
Contact: zeman@ufal.mff.cuni.cz
===============================================================================
```
