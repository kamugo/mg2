---
license: cc-by-nc-sa-4.0
language: [ca, cs, cu, de, en, es, fr, grc, hbo, hi, hu, ko, la, lt, nl, no, pl, ru, tr]
tags: [ CorPipe, CorPipe 26, CRAC Shared Task, CRAC 2026, CorefUD, CorefUD 1.4, Coreference Resolution, Minnt]
base_model: google/umt5-base
---

# The `corpipe26-onestage-corefud1.4-base-260702` Model

The `corpipe26-onestage-corefud1.4-base-260702` is a `umT5-base`-based multilingual model for
coreference resolution usable in CorPipe 26 <https://github.com/ufal/crac2026-corpipe>.
It is released on [LINDAT/CLARIAH-CZ](https://hdl.handle.net/11234/1-6205) and on
[HuggingFace](https://huggingface.co/ufal/corpipe26-onestage-corefud1.4-base-260702) under the CC BY-NC-SA 4.0 license.
The model is downloaded automatically from HuggingFace when running prediction with
the `--load ufal/corpipe26-onestage-corefud1.4-base-260702` argument.

The model is language agnostic, so it can be in theory used to predict
coreference in any `umT5` language; for zero-shot cross-lingual evaluation,
please refer to the CRAC 2026 paper.

The model predicts also the empty nodes and therefore ignores all empty nodes
present on input during prediction.

The model was trained using the following command (see the CorPipe 26 repository
for more information):
```sh
tbs="ca_ancora cs_pcedt cs_pdt cs_pdtsc cu_proiel de_potsdamcc en_fantasycoref en_gum en_litbank es_ancora fr_ancor fr_democrat fr_litbankfr grc_proiel hbo_ptnk hi_hdtb hu_korkor hu_szegedkoref ko_ecmt la_coreflat lt_lcc nl_openboek no_bokmaalnarc no_nynorsknarc pl_pcc ru_rucor tr_itcc"

python3 corpipe26_onestage.py --train --dev --treebanks $(for c in $tbs; do echo data-onestage/$c/$c-corefud-train.conllu; done) --batch_size=8 --learning_rate=6e-4 --learning_rate_decay --adafactor --encoder=google/umt5-base --exp=corpipe26-onestage-corefud1.4-base --compile
```


## CorefUD 1.4 Test Sets Results

The model achieves the following CorefUD 1.4 test set results (as reported in
the paper); segment size 2560 was used, with the exception for `cu_proiel` and
`grc_proiel` where it was 512:

| avg   | ca   | cs_pce| cs_pdt| cs_pdts| cu   | de   | en_fan| en_gum| en_lit| es   | fr_anc| fr_dem| fr_lit| grc  | hbo  | hi   | hu_kor| hu_sze| ko   | la   | lt_lcc| nl   | no_bok| no_nyn| pl   | ru   | tr   |
|-------|------|-------|-------|--------|------|------|-------|-------|-------|------|-------|-------|-------|------|------|------|-------|-------|------|------|-------|------|-------|-------|------|------|------|
| 69.09 | 76.4 | 73.7  | 74.3  | 70.5   | 53.5 | 68.1 | 71.3  | 70.5  | 74.2  | 78.1 | 69.1  | 69.4  | 73.5  | 63.1 | 58.1 | 72.9 | 62.0  | 62.9  | 67.7 | 52.2 | 73.8  | 68.8 | 73.7  | 71.5  | 75.5 | 77.2 | 63.5 |


## Running the Model on Plain Text

To run the model on plain text, first the plain text needs to be tokenized and
converted to CoNLL-U (and optionally parsed if you also want mention heads),
by using for example UDPipe 2:

```sh
curl -F data="Susan came home and Martin greeted her there. Then Martin and Paul left for a trip and Susan waved them off." \
  -F model=english -F tokenizer= -F tagger= -F parser=  https://lindat.mff.cuni.cz/services/udpipe/api/process \
  | python -X utf8 -c "import sys,json; sys.stdout.write(json.load(sys.stdin)['result'])" >input.conllu
```

Then the CoNLL-U file can be processed by CorPipe 26, by using for example
```sh
python3 corpipe26_onestage.py --load ufal/corpipe26-onestage-corefud1.4-base-260702 --exp . --epoch 0 --test input.conllu
```
which would generate the following predictions in `input.00.conllu`:
```
# generator = UDPipe 2, https://lindat.mff.cuni.cz/services/udpipe
# udpipe_model = english-ewt-ud-2.17-251125
# udpipe_model_licence = CC BY-NC-SA
# newdoc
# global.Entity = eid-etype-head-other
# newpar
# sent_id = 1
# text = Susan came home and Martin greeted her there.
1	Susan	Susan	PROPN	NNP	Number=Sing	2	nsubj	_	Entity=(c1--1)
2	came	come	VERB	VBD	Mood=Ind|Number=Sing|Person=3|Tense=Past|VerbForm=Fin	0	root	_	_
3	home	home	ADV	RB	_	2	advmod	_	_
4	and	and	CCONJ	CC	_	6	cc	_	_
5	Martin	Martin	PROPN	NNP	Number=Sing	6	nsubj	_	Entity=(c2--1)
6	greeted	greet	VERB	VBD	Mood=Ind|Number=Sing|Person=3|Tense=Past|VerbForm=Fin	2	conj	_	_
7	her	she	PRON	PRP	Case=Acc|Gender=Fem|Number=Sing|Person=3|PronType=Prs	6	obj	_	Entity=(c1--1)
8	there	there	ADV	RB	PronType=Dem	6	advmod	_	SpaceAfter=No
9	.	.	PUNCT	.	_	2	punct	_	_

# sent_id = 2
# text = Then Martin and Paul left for a trip and Susan waved them off.
1	Then	then	ADV	RB	PronType=Dem	5	advmod	_	_
2	Martin	Martin	PROPN	NNP	Number=Sing	5	nsubj	_	Entity=(c3--1(c2--1)
3	and	and	CCONJ	CC	_	4	cc	_	_
4	Paul	Paul	PROPN	NNP	Number=Sing	2	conj	_	Entity=(c4--1)c3)
5	left	leave	VERB	VBD	Mood=Ind|Number=Sing|Person=3|Tense=Past|VerbForm=Fin	0	root	_	_
6	for	for	ADP	IN	_	8	case	_	_
7	a	a	DET	DT	Definite=Ind|PronType=Art	8	det	_	_
8	trip	trip	NOUN	NN	Number=Sing	5	obl	_	_
9	and	and	CCONJ	CC	_	11	cc	_	_
10	Susan	Susan	PROPN	NNP	Number=Sing	11	nsubj	_	Entity=(c1--1)
11	waved	wave	VERB	VBD	Mood=Ind|Number=Sing|Person=3|Tense=Past|VerbForm=Fin	5	conj	_	_
12	them	they	PRON	PRP	Case=Acc|Number=Plur|Person=3|PronType=Prs	11	obj	_	Entity=(c3--1)
13	off	off	ADP	RP	_	11	compound:prt	_	SpaceAfter=No
14	.	.	PUNCT	.	_	5	punct	_	SpaceAfter=No

```

## How to Cite

```
@inproceedings{straka-2026-corpipe,
  title = "{C}or{P}ipe at {CRAC} 2026: Empty Nodes and Cross-Lingual Transfer in Multilingual Coreference Resolution",
  author = "Straka, Milan",
  editor = "Braud, Chlo{\'e}  and Hardmeier, Christian  and Ogrodniczuk, Maciej  and Loaiciga, Sharid  and
    Zeldes, Amir  and Nov{\'a}k, Michal  and Li, Chuyuan  and Strube, Michael  and Li, Junyi Jessy",
  booktitle = "Proceedings of the 2nd Joint Workshop on Computational Approaches to Discourse, Context and
    Document-Level Inferences and Computational Models of Reference, Anaphora and Coreference ({CODI}-{CRAC} 2026)",
  month = jul,
  year = "2026",
  address = "San Diego, California, USA",
  publisher = "Association for Computational Linguistics",
  url = "https://aclanthology.org/2026.codi-1.27/",
  doi = "10.18653/v1/2026.codi-1.27",
  pages = "205--216",
  ISBN = "979-8-89176-400-2"
}
```
