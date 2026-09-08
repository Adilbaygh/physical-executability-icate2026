# Text to paste into the revised manuscript

Insert as a first-level heading immediately **before** REFERENCES, using the
AIP template style *Heading 1* (it renders in all capitals automatically) and
*Paragraph* for the body.

---

## DATA AND CODE AVAILABILITY

> The complete benchmark that produces every number, table entry and figure in
> this paper is openly available at
> https://doi.org/10.5281/zenodo.XXXXXXX (version 1.0.0), and is developed at
> https://github.com/Adilbaygh/physical-executability-icate2026
> (commit REPLACE-WITH-COMMIT-HASH). The package contains one deterministic
> Python script with no random component, its reference output, the three
> figures, a table of every numerical parameter of the algorithms, and a map
> from each published number to its source in the output file. The feeder
> instance uses the IEEE 33-bus `case33bw` line and load table of Ref. 5 as
> distributed with Refs. 6 and 7; the load-flow solver is implemented in the
> script itself and the linear programs are solved with the HiGHS solver of
> SciPy. No proprietary software is required.

---

## What to fill in

| Placeholder | Where it comes from |
|---|---|
| `10.5281/zenodo.XXXXXXX` | the **concept DOI** reserved in Zenodo (resolves to the newest version) |
| `REPLACE-WITH-COMMIT-HASH` | the first 7–10 characters of the tagged commit |

The GitHub account is already filled in as `Adilbaygh`.

Use the **concept** DOI in the paper, not the per-version DOI, so the citation
keeps resolving if the package is updated after publication. State the version
number separately, as above.

## Related statements the conference may also require

> **Funding.** *(state the funding source, or: This research received no
> specific grant from any funding agency.)*

> **Conflict of interest.** The authors declare no conflict of interest.

## Order of operations

1. Create the GitHub repository and push this package.
2. In Zenodo, **reserve a DOI** for the deposition before publishing it.
3. Put the reserved concept DOI into the manuscript.
4. Tag the repository (`v1.0.0`), let Zenodo capture the release, publish.
5. Copy the resulting commit hash into the statement above.

## After the paper itself receives a DOI

AIP assigns the proceedings DOI only at publication, so the link from the
package to the paper cannot be made now. Once it exists, add it to the Zenodo
record and to `.zenodo.json` as

```json
{ "relation": "isSupplementTo",
  "identifier": "<the AIP DOI>",
  "scheme": "doi",
  "resource_type": "publication-conferencepaper" }
```

and add the same DOI to `CITATION.cff` under `preferred-citation:` as a `doi:`
field. The two entries already present are `references` relations to the two
sources the benchmark draws its input data from; they are not the paper.
