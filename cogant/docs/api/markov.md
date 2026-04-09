# `cogant.markov`

The `cogant.markov` package partitions a program graph into internal (mu), sensory (s), active (a), and external (eta) nodes — the four disjoint sets of an Active Inference Markov blanket.

## Package

::: cogant.markov

## Blanket

The pure-function partitioner. `partition_by_seeds` is deterministic for a given graph and seed set.

::: cogant.markov.blanket

## Extractor

The seeded extractor with five strategies (`auto`, `module`, `class`, `cluster`, `explicit`).

::: cogant.markov.extractor

## Network

Network-level helpers for multi-blanket analysis.

::: cogant.markov.network
