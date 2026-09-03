# Summary

Latin-CorefLat is a converted version of CorefLat, a coreference-annotated corpus of Latin.
It comprises four literary texts:
- two works of prose,
    1. Book I of De bello Gallico by Gaius Julius Caesar, and
    2. Book I of Confessiones by Augustine of Hippo
- and two theatrical plays
    3. Curculio by Titus Maccius Plautus, and 
    4. Medea by Lucius Annaeus Seneca.

## References

```
@inproceedings{delfino2024building,
  title={Building CorefLat. A Linguistic Resource for Coreference and Anaphora Resolution in Latin},
  author={Delfino, Eleonora and Leotta, Roberta and Passarotti, Marco and Moretti, Giovanni},
  booktitle={Proceedings of the 10th Italian Conference on Computational Linguistics (CLiC-it 2024)},
  pages={273--279},
  year={2024}
}

@article{delfino2025coreflat,
  title={CorefLat. Annotazione e modellizzazione per la risoluzione di coreferenze in latino},
  author={Delfino, Eleonora and Leotta, Roberta Grazia and Passarotti, Marco and Mambrini, Francesco},
  journal={Lingue antiche e moderne},
  volume={14},
  pages={61--91},
  year={2025}
}
```

# Changelog

### 2026-02-18 v1.4
  * initial conversion
  * morpho-syntactic attributes generated using UDPipe 2 with UD 2.17 models
  * the original annotation mostly contained single-word mention spans; during conversion, these spans were extended to longer phrases based on the parsed UD trees
  * each of the four annotated documents from the original resource was distributed across the CorefUD train/dev/test sections as follows: approximately the first 10% of the tokens were assigned to the test set, the next 10% to the development set, and the remaining 80% to the training set.
  * long-distance coreference relations (encoded via the external_reference XML attribute in the original resource) have not yet been converted.

```
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: CorefUD 1.4
License: CC BY-SA 4.0
Includes text: yes
Genre: fiction nonfiction historical literary
Lemmas: automatic
UPOS: automatic
XPOS: automatic
Features: automatic
Relations: automatic
CorefUD contributors: Leotta, Roberta Grazia (1);  Delfino, Eleonora (2); Passarotti, Marco (1);  Moretti, Giovanni (1);  Žabokrtský, Zdeněk (3)
Contributors' affiliations: (1) CIRCSE Research Centre, Università Cattolica del Sacro Cuore, Milano, Italy
                            (2) Università di Udine, Udine, Italy
                            (3) Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied Linguistics, Prague, Czechia
Other contributors:
Contributing: elsewhere
Contact: robertagrazia.leotta@unicatt.it
===============================================================================
```
