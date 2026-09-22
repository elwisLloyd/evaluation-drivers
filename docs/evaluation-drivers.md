# Evaluation drivers

Requirements for an IT implementation estimate often arrive at very different
levels of detail, ranging from a short brief or a call recording to a detailed
technical specification. A technical team still needs a consistent way to
reason about the implementation while clarification time is limited.

An **evaluation driver** is a parameter that describes an independent aspect of
the work and materially affects its composition, scale, or difficulty. A driver
is not an estimate by itself. Turning driver values into cost, duration,
staffing, or an aggregate score is a separate problem and is outside this
project.

The driver-discovery task is similar to feature engineering for a future
estimation model: identify a compact but sufficiently complete basis of
properties that explain meaningful variation between projects. The **work
space** is the complete set of work types that can occur in the target class of
projects. Every material area in that work space should be represented by at
least one driver.

## Categorical value model

Every driver is assessed using a finite set of categorical values so that an
assessment can express uncertainty as a probability distribution. The catalog
retains the physical source type:

- `numeric` for quantities such as the number of integration flows;
- `categorical` for properties such as delivery maturity;
- `binary` for yes/no properties.

A numeric driver is still evaluated through non-overlapping ranges. Range
boundaries must correspond to meaningfully different classes of implementation
work rather than arbitrary equal-width intervals. For example, an integration
count might use `0`, `1`, `2–3`, `4–10`, and `more than 10` if those boundaries
represent changes in architecture or operating effort.

The inference result for a relevant driver is a probability distribution over
all of its categories. Applicability and information quality are represented
separately: missing information must not be treated as the lowest-complexity
category.

## Example work areas

The universal ML/AI catalog may include both technical and organizational work:

| Work area | Example drivers |
|---|---|
| Business scope | Number and diversity of use cases and user groups |
| Data acquisition | Source count, access readiness, volume, update frequency |
| Data preparation | Data quality, cleaning, labeling, annotation agreement |
| ML/AI solution | Task diversity, model count, novelty, multimodality |
| Quality and validation | Ground-truth readiness, evaluation rigor, human review |
| Integration | Integration flows, consumers, interfaces, affected systems |
| Serving and scale | Batch/online mode, throughput, latency, availability |
| Security and compliance | Data sensitivity, access control, audit requirements |
| MLOps and operations | Automation, monitoring, retraining, rollback |
| Delivery organization | Stakeholder alignment, documentation, handover, training |

Technology names can be useful evidence but are normally not drivers by
themselves. A driver should be technology-neutral unless a specific technology
creates independent implementation work that cannot be represented otherwise.

## Catalog evolution

Training cases are processed incrementally against the current catalog. For
each case, the workflow records relevant existing drivers, insufficient
information, missing values, and missing drivers. New drivers and categories
are automatically applied in the MVP build mode, and the catalog version is
incremented whenever it changes.

Inference always uses an immutable catalog snapshot. If an incoming case
contains uncovered work, inference emits a request to add rather than changing
the basis. This keeps results comparable and allows proposed changes to be
reviewed before a new catalog version is used.
