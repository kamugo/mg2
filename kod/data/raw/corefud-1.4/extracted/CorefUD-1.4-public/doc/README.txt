Resource: CorefUD 1.4 - Coreferences in Universal Dependencies, version 1.4

Authors: Michal Novák¹, Martin Popel¹, Daniel Zeman¹, Zdeněk Žabokrtský¹, Anna Nedoluzhko¹, Kutay
         Acar², David Bamman³, Antoine Bourgois⁴, Peter Bourgonje⁵, Silvie Cinková¹, Eleonora
         Delfino⁶, Hanne Eckhoff⁷, Gülşen Eryiğit⁸, Jan Hajič¹, Sooyoun Han⁹, Christian Hardmeier¹⁰,
         Dag Haug¹¹, Tollef Jørgensen¹², Andre Kåsen¹³, Pauline Krielke¹⁴, Frédéric Landragin¹⁵,
         Ekaterina Lapshinova-Koltunski¹⁴, Roberta Grazia Leotta¹⁶, Petter Mæhlum¹⁷, M. Antònia
         Martí¹⁸, Frédérique Mélanie-Becquet⁴, Marie Mikulová¹, Kirill Milintsevich¹⁹, Giovanni
         Moretti¹⁶, Vandan Mujadia²⁰, Judith Muzerelle²¹, Sangha Nam²², Anders Nøklestad¹¹, Maciej
         Ogrodniczuk²³, Lilja Øvrelid¹⁷, Tuğba Pamay Arslan⁸, Marco Passarotti¹⁶, Thierry Poibeau⁴,
         Ian Porada²⁴, Marta Recasens¹⁸, Sumin Seo⁹, Per Erik Solberg¹³, Manfred Stede⁵, Jan
         Štěpánek¹, Barbora Štěpánková¹, Milan Straka¹, Daniel Swanson²⁵, Svetlana Toldova²⁶, Noémi
         Vadász²⁷, Andreas van Cranenburgh²⁸, Erik Velldal¹⁷, Veronika Vincze²⁹, Amir Zeldes³⁰,
         Voldemaras Žitkus³¹
         ¹ Charles University, Faculty of Mathematics and Physics, Institute of Formal and Applied
           Linguistics, Prague, Czechia
         ² Istanbul Technical University, Department of Computer Engineering, Istanbul, Turkey
         ³ University of California, Berkeley, School of Information, USA
         ⁴ Lattice (CNRS & ENS-PSL & Université Sorbonne Nouvelle), Montrouge, France
         ⁵ University of Potsdam, Applied Computational Linguistics, Potsdam, Germany
         ⁶ Università di Udine, Udine, Italy
         ⁷ University of Oxford, Faculty of Medieval and Modern Languages, Oxford, UK
         ⁸ Istanbul Technical University, Department of Artificial Intelligence and Data
           Engineering, Istanbul, Turkey
         ⁹ Yonsei University, Department of Digital Analytics, Seoul, South Korea
         ¹⁰ Uppsala University, Department of Linguistics and Philology, Uppsala, Sweden
         ¹¹ University of Oslo, Department of Linguistics and Scandinavian Studies, Oslo, Norway
         ¹² Norwegian University of Science and Technology, Department of Computer Science,
            Trondheim, Norway
         ¹³ The Norwegian Language Bank, National Library of Norway, Oslo, Norway
         ¹⁴ Saarland University, Department of Language Science and Technology, Saarbrücken, Germany
         ¹⁵ Lattice, CNRS & ENS Paris & Université Sorbonne Nouvelle & PSL Research University &
            USPC, Montrouge, France
         ¹⁶ CIRCSE Research Centre, Università Cattolica del Sacro Cuore, Milano, Italy
         ¹⁷ University of Oslo, Department of Informatics, Oslo, Norway
         ¹⁸ University of Barcelona, Department of Linguistics, Centre de Llenguatge i Computació,
            Barcelona, Spain
         ¹⁹ Institut National de l'Audiovisuel, Bry-sur-Marne, France
         ²⁰ Kohli Center on Intelligent Systems, International Institute of Information Technology,
            Hyderabad, India
         ²¹ Université d'Orléans, LLL UMR 7270, France
         ²² KAIST, School of Computing, Daejeon, South Korea
         ²³ Polish Academy of Sciences, Institute of Computer Science, Warsaw, Poland
         ²⁴ Mila, McGill University, Montreal, Canada
         ²⁵ Indiana University, Department of Linguistics, Bloomington, USA
         ²⁶ HSE University, Faculty of Humanities, Laboratory of Formal Models in Linguistics,
            Moscow, Russia
         ²⁷ Hungarian Research Centre for Linguistics, Research Group for Language Technology,
            Budapest, Hungary
         ²⁸ Center for Language and Cognition, University of Groningen, The Netherlands
         ²⁹ MTA-SZTE Research Group on Artificial Intelligence & University of Szeged, Department of
            General Linguistics, Szeged, Hungary
         ³⁰ Georgetown University, Department of Linguistics, Washington DC, USA
         ³¹ Kaunas University of Technologies, Department of Information Systems, Kaunas, Lithuania


CorefUD is a collection of previously existing datasets annotated with coreference,
which we converted into a common annotation scheme. In total, CorefUD in its current
version 1.4 consists of 33 datasets for 19 languages.

The datasets are enriched with automatic morphological and syntactic annotations
(except for a few datasets where these annotations are gold standard from corresponding
UD treebanks) that are fully compliant with the standards of the Universal Dependencies
project. All the datasets are stored in the CoNLL-U format, with coreference- and bridging-
specific information captured by attribute-value pairs located in the MISC column. To learn
more about the harmonized scheme, or about the diversity of the original resources, see
https://ufal.mff.cuni.cz/corefud.

The collection is divided into a public edition and a non-public (ÚFAL-internal) edition.
The publicly available edition is distributed via LINDAT-CLARIAH-CZ and contains 29
datasets for 19 languages (1 dataset for Ancient Greek, 1 for Ancient Hebrew, 1 for Catalan,
3 for Czech, 1 for Dutch, 4 for English, 3 for French, 2 for German, 1 for Hindi, 2 for Hungarian,
1 for Korean, 1 for Latin, 1 for Lithuanian, 2 for Norwegian, 1 for Old Church Slavonic, 1 for Polish,
1 for Russian, 1 for Spanish, and 1 for Turkish), excluding the test data.

The non-public edition is available internally to ÚFAL members and contains additional
4 datasets for 2 languages (1 dataset for Dutch, and 3 for English), which we are
not allowed to distribute due to their original license limitations. It also contains
the test data portions for all datasets.

When using any of the harmonized datasets, please get acquainted with its license
(placed in the same directory as the data) and cite the original data resource too.

References to original resources whose harmonized versions are contained
in the public edition of CorefUD 1.4:

- Ancient_Greek-PROIEL:
Haug, D. and Jøhndal, Marius L. (2008). Creating a Parallel Treebank of the Old Indo-European
Bible Translations. In Proceedings of the Language Technology for Cultural Heritage Data
Workshop, pages 27-34, Marrakech, Morocco. European Language Resources Association.

- Ancient_Hebrew-PTNK:
Swanson, D. and Tyers, F. (2022). A Universal Dependencies Treebank of Ancient Hebrew.
In Proceedings of the Thirteenth Language Resources and Evaluation Conference,
pages 2353-2361, Marseille, France. European Language Resources Association.

- Catalan-AnCora:
Recasens, M. and Martí, M. A. (2010). AnCora-CO: Coreferentially Annotated Corpora for
Spanish and Catalan. Language Resources and Evaluation, 44(4):315–345

- Dutch-OpenBoek:
van Cranenburgh, A. and van Noord, G. (2022). OpenBoek: A Corpus of Literary Coreference
and Entities with an Exploration of Historical Spelling Normalization. Computational
Linguistics in the Netherlands Journal, 12:235–251.

- Czech-PCEDT:
Nedoluzhko, A., Novák, M., Cinková, S., Mikulová, M., and Mírovský, J. (2016). Coreference
in Prague Czech-English Dependency Treebank.  In Proceedings of the Tenth International
Conference on Language Resources and Evaluation (LREC'16), pages 169–176, Portorož,
Slovenia. European Language Resources Association.

- Czech-PDT:
Mikulová, M., Štěpánková, B., Zeman, D., Štěpánek, J., Straka, M., and Hajič, J. (2026).
Meet UD_Czech-PDTC: A Large and Genre-Rich Treebank in Universal Dependencies.
In Proceedings of the 15th International Conference on Language Resources and Evaluation
(LREC 2026), Palma, Spain. European Language Resources Association.

- Czech-PDTSC:
Mikulová, M., Mírovský, J., Nedoluzhko, A., Pajas, P., Štěpánek, J., and Hajič, J. (2017).
PDTSC 2.0 - Spoken Corpus with Rich Multi-layer Structural Annotation. In Text, Speech,
and Dialogue: 20th International Conference, TSD 2017, Prague, Czech Republic, August 27–31,
2017, Proceedings, pages 129–137. Springer International Publishing, Cham.

- English-GUM:
Zeldes, A. (2017). The GUM Corpus: Creating Multilayer Resources in the Classroom.
Language Resources and Evaluation, 51(3):581–612.

- English-LitBank:
Bamman, D., Lewke, O., and Mansoor, A. (2020). An Annotated Dataset of Coreference
in English Literature. In Proceedings of the Twelfth Language Resources and Evaluation
Conference, pages 44–54, Marseille, France. European Language Resources Association.

- English-ParCorFull:
Lapshinova-Koltunski, E., Hardmeier, C., and Krielke, P. (2018). ParCorFull: a
Parallel Corpus Annotated with Full Coreference. In Proceedings of the Eleventh
International Conference on Language Resources and Evaluation (LREC 2018), Miyazaki,
Japan. European Language Resources Association.

- English-FantasyCoref:
Han, S., Seo, S., Kang, M., Kim, J., Choi, N., Song, M., and Choi, J. D. (2021).
FantasyCoref: Coreference Resolution on Fantasy Literature Through Omniscient Writer's
Point of View. In Proceedings of the Fourth Workshop on Computational Models of Reference,
Anaphora and Coreference, pages 24–35, Punta Cana, Dominican Republic. Association for
Computational Linguistics.

- French-ANCOR:
Muzerelle, J., Lefeuvre, A., Schang, E., Antoine, J.-Y., Pelletier, A., Maurel, D.,
Eshkol, I., and Villaneau, J. (2014). ANCOR_Centre, a Large Free Spoken French 
Coreference Corpus: description of the Resource and Reliability Measures. In Proceedings
of the Ninth International Conference on Language Resources and Evaluation (LREC 2014),
pages 843–847, Reykjavik, Iceland. European Language Resources Association.

- French-Democrat:
Landragin, F. (2021). Le corpus Democrat et son exploitation. Présentation.
Langages, 224, 11–24.

- French-LitBankFr:
Mélanie-Becquet, F., Barré, J., Seminck, O., Plancq, C., Naguib, M., Pastor, M., and
Poibeau, T. (2024). BookNLP-fr, the French Versant of BookNLP: A Tailored Pipeline for
19th and 20th Century French Literature. Journal of Computational Literary Studies, 3(1):1–34.

- German-ParCorFull:
Lapshinova-Koltunski, E., Hardmeier, C., and Krielke, P. (2018). ParCorFull: a
Parallel Corpus Annotated with Full Coreference. In Proceedings of the Eleventh
International Conference on Language Resources and Evaluation (LREC 2018), Miyazaki,
Japan. European Language Resources Association

- German-PotsdamCC:
Bourgonje, P. and Stede, M. (2020). The Potsdam Commentary Corpus 2.2: Extending
annotations for shallow discourse parsing. In Proceedings of the 12th Language
Resources and Evaluation Conference, pages 1061–1066, Marseille, France. European
Language Resources Association.

- Hindi-HDTB:
Mujadia, V., Gupta, P., and Sharma, D. M. (2016). Coreference Annotation Scheme and
Relation Types for Hindi. In Proceedings of the Tenth International Conference on Language 
Resources and Evaluation (LREC 2016), pages 161–168, Portorož, Slovenia. European Language
Resources Association.

- Hungarian-KorKor:
Vadász, N. (2022). Building a Manually Annotated Hungarian Coreference Corpus: Workflow
and Tools. In Proceedings of the Fifth Workshop on Computational Models of Reference,
Anaphora and Coreference, pages 38–47, Gyeongju, Republic of Korea. Association for
Computational Linguistics.

- Hungarian-SzegedKoref:
Vincze, V., Hegedűs, K., Sliz-Nagy, A., and Farkas, R. (2018). SzegedKoref: A Hungarian
Coreference Corpus. In Proceedings of the Eleventh International Conference on
Language Resources and Evaluation (LREC 2018), Miyazaki, Japan. European Language
Resources Association.

- Korean-ECMT:
Nam, S., Lee, M., Kim, D., Han, K., Kim, K., Yoon, S., Kim, E., and Choi K.-S. (2020).
Effective Crowdsourcing of Multiple Tasks for Comprehensive Knowledge Extraction.
In Proceedings of the Twelfth Language Resources and Evaluation Conference (LREC 2020),
pages 212–219, Marseille, France. European Language Resources Association.

- Latin-CorefLat:
Delfino, E., Leotta, R., Passarotti, M., and Moretti, G. (2024). Building CorefLat.
A Linguistic Resource for Coreference and Anaphora Resolution in Latin. In Proceedings
of the 10th Italian Conference on Computational Linguistics (CLiC-it 2024), pages 273–279.

- Lithuanian-LCC:
Žitkus, V. and Butkienė, R. (2018). Coreference Annotation Scheme and Corpus for Lithuanian
Language. In Fifth International Conference on Social Networks Analysis, Management and
Security, SNAMS 2018, Valencia, Spain, October 15-18, 2018, pages 243–250. IEEE.

- Norwegian-BokmaalNARC:
Mæhlum, P., Haug, D., Jørgensen, T., Kåsen, A., Nøklestad, A., Rønningstad, E., Solberg,
P. E., Velldal, E., and Øvrelid, L. (2022). NARC–Norwegian Anaphora Resolution Corpus.
In Proceedings of the Fifth Workshop on Computational Models of Reference, Anaphora and
Coreference, pages 48–60, Gyeongju, Republic of Korea. Association for Computational
Linguistics.

- Norwegian-NynorskNARC:
Mæhlum, P., Haug, D., Jørgensen, T., Kåsen, A., Nøklestad, A., Rønningstad, E., Solberg,
P. E., Velldal, E., and Øvrelid, L. (2022). NARC–Norwegian Anaphora Resolution Corpus.
In Proceedings of the Fifth Workshop on Computational Models of Reference, Anaphora and
Coreference, pages 48–60, Gyeongju, Republic of Korea. Association for Computational
Linguistics.

- Old_Church_Slavonic-PROIEL:
Haug, D. and Jøhndal, Marius L. (2008). Creating a Parallel Treebank of the Old Indo-European
Bible Translations. In Proceedings of the Language Technology for Cultural Heritage Data
Workshop, pages 27-34, Marrakech, Morocco. European Language Resources Association.

- Polish-PCC:
Ogrodniczuk, M., Glowińska, K., Kopeć, M., Savary, A., and Zawisławska, M. (2013). Polish
coreference corpus. In Human Language Technology. Challenges for Computer Science
and Linguistics - 6th Language and Technology Conference, LTC 2013, Poznań, Poland,
December 7-9, 2013. Revised Selected Papers, volume 9561 of Lecture Notes in Computer
Science, pages 215–226. Springer.

- Russian-RuCor:
Toldova, S., Roytberg, A., Ladygina, A. A., Vasilyeva, M. D., Azerkovich,
I. L., Kurzukov,M., Sim, G., Gorshkov, D. V., Ivanova, A., Nedoluzhko, A., and Grishina, Y.
(2014). Evaluating Anaphora and Coreference Resolution for Russian. In Komp’juternaja
lingvistika i intellektual’nye tehnologii. Po materialam ezhegodnoj Mezhdunarodnoj konferencii
Dialog, pages 681–695.

- Spanish-AnCora:
Recasens, M. and Martí, M. A. (2010). AnCora-CO: Coreferentially Annotated Corpora for
Spanish and Catalan. Language Resources and Evaluation, 44(4):315–345

- Turkish-ITCC
Pamay, T., and Eryiğit, G. (2018). Turkish Coreference Resolution. 2018 Innovations in
Intelligent Systems and Applications (INISTA), pages 1–7, Thessaloniki, Greece. IEEE

References to original resources whose harmonized versions are contained in
the ÚFAL-internal edition of CorefUD 1.4:

- Dutch-COREA:
Hendrickx, I., Bouma, G., Coppens, F., Daelemans, W., Hoste, V., Kloosterman, G., Mineur, A.-M.,
Van Der Vloet, J., and Verschelde, J.-L. (2008). A coreference corpus and resolution system
for Dutch. In Proceedings of the Sixth International Conference on Language Resources and
Evaluation (LREC’08), Marrakech, Morocco. European Language Resources Association.

- English-ARRAU:
Uryupina, O., Artstein, R., Bristot, A., Cavicchio, F., Delogu, F., Rodriguez, K. J., and
Poesio, M. (2020). Annotating a broad range of anaphoric phenomena, in a variety of genres:
the ARRAU Corpus. Natural Language Engineering, 26(1):95–128.

- English-OntoNotes:
Weischedel, R., Hovy, E., Marcus, M., Palmer, M., Belvin, R., Pradhan, S., Ramshaw, L., and
Xue, N. (2011). Ontonotes: A large training corpus for enhanced processing. In Handbook
of Natural Language Processing and Machine Translation: DARPA Global Autonomous
Language Exploitation, pages 54–63, New York. Springer-Verlag.

- English-PCEDT:
Nedoluzhko, A., Novák, M., Cinková, S., Mikulová, M., and Mírovský, J. (2016). Coreference
in Prague Czech-English Dependency Treebank. In Proceedings of the Tenth International
Conference on Language Resources and Evaluation (LREC’16), pages 169–176, Portorož,
Slovenia. European Language Resources Association.
