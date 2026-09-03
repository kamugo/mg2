# Summary

French-LitBankFr is a conversion of the French LitBank corpus, a coreference-annotated corpus of French literary texts.
The corpus consists of French novels from the 19th and beginning of 20th century.
The files are annotated following the LitBank guidelines.

## References

```
@article{MelanieBecquet2024BookNLPfr,
  author  = {M{\'e}lani{\'e}-Becquet, Fr{\'e}d{\'e}rique and Barr{\'e}, Jean and Seminck, Olga and Plancq, Cl{\'e}ment and Naguib, Marco and Pastor, Martial and Poibeau, Thierry},
  title   = {{BookNLP-fr, the French Versant of BookNLP: A Tailored Pipeline for 19th and 20th Century French Literature}},
  journal = {Journal of Computational Literary Studies},
  volume  = {3},
  number  = {1},
  pages   = {1--34},
  year    = {2024},
  doi     = {10.48694/jcls.3924}
}
```

# Changelog

### 2026-02-18 v1.4
  * initial conversion
  * the source already prepared in the CorefUD/CoNLL-U format
  * invalid morpho-syntactic annotation replaced by attributes produced by UDPipe 2 using UD 2.17 models
  * ensuring entity IDs are unique in each newdoc document
  * entity types converted to the standard inventory
  * new train/dev/test split -- differs from the one used in the original paper

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.4
License: CC BY-SA 4.0
Includes text: yes
Genre: fiction literary
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Mélanie-Becquet, Frédérique (1); Bourgois, Antoine (1); Poibeau, Thierry (1); Novák, Michal (2)
Other contributors: Barré, Jean; Seminck, Olga; Plancq, Clément; Naguib, Marco; Pastor, Martial
Contributors' affiliations: (1) Lattice (CNRS & ENS-PSL & Université Sorbonne Nouvelle), Montrouge, France
                            (2) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Contributing: elsewhere
Contact: frederique.melanie@ens.psl.eu
===============================================================================
```
