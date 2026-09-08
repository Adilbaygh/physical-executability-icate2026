# Zenodo — manual upload, field by field

Use this when the GitHub integration will not mint a DOI. It produces the
same record: a version DOI and a concept DOI. Nothing here is invented — every
value is copied from `.zenodo.json` in the repository.

## 0. The file to upload

Download the archive of the tagged release:

    https://github.com/Adilbaygh/physical-executability-icate2026/archive/refs/tags/v1.0.0.zip

That zip is exactly the tagged commit `0a19c9b347`. Upload that one file.

## 1. Get the DOI before publishing

On the upload form, in the DOI box, choose the option that reserves a DOI
("No" to "Do you already have a DOI?", then the reserve/get-a-DOI button).
The reserved DOI appears immediately and is the one to send back.

## 2. Fields

**Resource type** — Software

**Title** — Reproducibility package for "The Price of Physical Executability in Fair Resource Allocation on Radial Supply Networks" (ICATE 2026)

**Version** — 1.0.0

**Language** — English

**License** — Creative Commons Attribution 4.0 International (CC BY 4.0)

**Access** — Open

**Publication date** — the day you publish

**Creators** (in this order, affiliation identical for all six):

- Kudaybergenov, Adilbay — Karakalpak State University named after Berdakh, Nukus, Uzbekistan
- Kazimbetova, Mukhabbad — Karakalpak State University named after Berdakh, Nukus, Uzbekistan
- Ametova, Gulsara — Karakalpak State University named after Berdakh, Nukus, Uzbekistan
- Ispanova, Jadira — Karakalpak State University named after Berdakh, Nukus, Uzbekistan
- Absametov, Bayram — Karakalpak State University named after Berdakh, Nukus, Uzbekistan
- Qudaynazarov, Mukhammed — Karakalpak State University named after Berdakh, Nukus, Uzbekistan

**Keywords** (one per entry):

- leximin allocation
- max-min fairness
- radial network
- load curtailment
- gradually varied flow
- IEEE 33-bus feeder
- irrigation canal
- certification
- reproducibility

**Related works** — add both, relation "References", type "Publication / Article":

- 10.1109/61.25627  (DOI)
- 10.3390/w10081017  (DOI)

**Description** — paste as plain text:

Deterministic benchmark accompanying the ICATE 2026 conference paper The Price of Physical Executability in Fair Resource Allocation on Radial Supply Networks (AIP Conference Proceedings).

The package contains the single script that produces every number, table entry and figure of the paper, its reference output, the three published figures, a complete list of the numerical parameters of the algorithms, and a map from each published number to its source in the result file.

Two physically unrelated radial media are solved: the IEEE 33-bus distribution feeder under a 0.95 p.u. bus-voltage floor, and a seven-offtake prismatic irrigation reach under gradually-varied-flow command head. For each medium a quantity-only leximin allocation is compared with a plan certified against the exact nonlinear network model, and the relative loss of the egalitarian floor is reported.

The script is deterministic and contains no randomness. The feeder instance uses a self-contained backward–forward sweep; MATPOWER and pandapower are cited only as the distribution source of the case33bw data table and are not runtime dependencies. The canal instance is a controlled synthetic benchmark informed by published Canale Emiliano Romagnolo parameters, not a calibrated model of that canal.

**Additional notes**:

The IEEE 33-bus line and load table is the case33bw benchmark of Baran and Wu (1989), doi:10.1109/61.25627. The canal section parameters follow Luppi et al., Water 10, 1017 (2018), doi:10.3390/w10081017 (CC BY 3.0); the bed slope, gate dimensions, offtake spacing, continuation flow, head-gate level limit and demand vector are declared design assumptions.

## 3. After publishing

The record page shows two DOIs. The one to put in the paper is the **concept**
DOI, shown beside "Cite all versions" — it resolves to the newest version. The
version DOI points at 1.0.0 only.

## 4. Optional, later

A manual deposit and the GitHub integration can coexist. If the integration
starts working, a future release would create a *separate* record rather than a
new version of this one, so leave the repository switched off in Zenodo unless
you deliberately want that.