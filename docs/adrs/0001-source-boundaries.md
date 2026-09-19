# ADR 0001: Use generated fixtures at the portfolio boundary

Status: accepted for the sample.

The portfolio uses only invented fixtures generated inside this repository.
It illustrates a separation between operational records and reporting summaries
without importing real source records. Synthetic labels and local keys make the
boundary visible. See [provenance](../synthetic-data-provenance.md).

Synthetic data reduces disclosure risk; it does not by itself settle software
rights or make future real summary rows public. No actual production metrics
or adoption claims follow from this design.
