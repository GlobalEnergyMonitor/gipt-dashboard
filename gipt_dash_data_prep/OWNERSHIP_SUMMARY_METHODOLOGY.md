# Ownership summary methodology

The ownership summaries use each unit or phase's MWac-adjusted capacity. For
country results, binational hydropower is split using the two country-capacity
fields in GIPT.

## Entity source

- Use `Parent(s)` when it contains a named entity; otherwise use `Owner(s)`.
- Parent percentages are taken from `Parent(s) GEM Entity ID` when its entries
  align with the parent names. Owner names are never matched to owner IDs by
  position because that order is not reliable.
- Exact generic labels such as blank, unknown, other, not found, and
  undisclosed are combined as `Unknown`. A blank item within a semicolon list
  is ignored; it is not treated as an additional owner.
- Repeated names in one cell are consolidated. Repeated stated percentages are
  added, and repeated unstated names count once.

## Capacity allocation

The examples below assume a unit with 100 MW of capacity.

| Source ownership | Interpretation | Capacity allocation |
| --- | --- | --- |
| `A; B` | No percentages are stated. | Split equally: A 50 MW and B 50 MW. |
| `A [60%]; B [40%]` | Every entity has a share and the shares total 100%. | Retain the stated shares: A 60 MW and B 40 MW. |
| `A [60%]; B [20%]` | Every entity has a share, but the shares total less than 100%. | Retain the stated shares: A 60 MW and B 20 MW. Leave 20 MW unallocated. |
| `A [70%]; B [50%]` | Every entity has a share, but the shares total more than 100%. | Scale the shares down proportionally: A 58.3 MW and B 41.7 MW. |
| `A [60%]; B; C` | Some shares are unstated and the stated total is below 100%. | Retain A's 60 MW and split the remaining 40 MW equally: B 20 MW and C 20 MW. |
| `A [80%]; B [40%]; C` | An unstated entity is listed, but the stated shares total more than 100%. The percentages still provide relative weights. | Scale the stated shares down proportionally: A 66.7 MW and B 33.3 MW. Do not allocate capacity to C. |
| `A; B [100%]` | An unstated entity is listed alongside stated shares that total exactly 100%. | Treat the conflicting information as unusable and split equally: A 50 MW and B 50 MW. |
| `A [60%]; B [20%]; Unknown` | A generic placeholder is explicitly listed alongside named entities. | Apply the mixed-share rule: A 60 MW, B 20 MW, and `Unknown` 20 MW. |
| Blank, or only generic placeholders | No usable entity is provided. | Allocate all 100 MW to `Unknown`. |

Repeated entries are consolidated before applying this table. For example,
`A [75%]; A [25%]` becomes A 100%, while `A; A; B` becomes `A; B` and is
split equally.

Allocated plus unallocated capacity is checked against source capacity. No
synthetic joint-ownership or conflicting-ownership entity is created.

## Presentation

The dashboard shows the 20 largest named entities for each geography and
technology, with the remaining named entities combined as `Others`. This
roll-up is made for World, dashboard groups, and countries. `Others` therefore
means the generated ranking tail, while `Unknown` means missing or generic
source data. `Unknown` is omitted from the World hierarchy because it
overwhelms that visual, but is retained separately from `Others` in group and
country views. The standalone summary keeps the complete ranked entity lists,
including `Unknown` at World level, and does not create `Others`.
