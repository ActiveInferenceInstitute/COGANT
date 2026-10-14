"""Rust and Go structural parsers keep generic items and grouped imports.

The regex front ends are the only registered parsers for ``rust`` and
``go``, so idiomatic modern syntax must not be dropped silently: Rust
generic functions (``fn largest<T: PartialOrd>(...)``), generic impls
(``impl<T> Stack<T>``) and rustfmt-style grouped ``use a::{B, C};``, and Go
generic functions (``func Map[T any, U any](...)``).
"""

from __future__ import annotations

import pytest

from cogant.parsers import get_parser

_RUST = """\
use std::fmt;
use std::collections::{HashMap, HashSet};
use std::io::{self, Write as W};
use std::{
    sync::{Arc, Mutex},
    thread,
};

// we use a hashmap; it is fast
pub struct Stack<T> {
    items: Vec<T>,
}

impl<T> Stack<T> {
    pub fn push(&mut self, item: T) {
        self.items.push(item);
    }
}

impl<T: fmt::Display> fmt::Display for Stack<T> {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        Ok(())
    }
}

impl Stack<u8> {
    fn bytes(&self) -> usize {
        0
    }
}

fn largest<T: PartialOrd>(list: &[T]) -> &T {
    &list[0]
}

fn into_all<T: Into<Vec<u8>>>(x: T) -> Vec<u8> {
    x.into()
}

fn plain() {}
"""

_GO = """\
package main

func Map[T any, U any](xs []T, f func(T) U) []U {
    return nil
}

func Keys[M ~map[K]V, K comparable, V any](m M) []K {
    return nil
}

func Plain(x int) int {
    return x
}
"""


@pytest.mark.unit
def test_rust_grouped_use_statements_are_kept() -> None:
    uses = [u["path"] for u in get_parser("rust").parse(_RUST)["uses"]]

    assert uses == [
        "std::fmt",
        "std::collections::{HashMap, HashSet}",
        "std::io::{self, Write as W}",
        "std::{ sync::{Arc, Mutex}, thread, }",
    ]


@pytest.mark.unit
def test_rust_generic_functions_and_impls_are_kept() -> None:
    result = get_parser("rust").parse(_RUST)

    assert [f["name"] for f in result["functions"]] == [
        "push",
        "fmt",
        "bytes",
        "largest",
        "into_all",
        "plain",
    ]
    assert [(i["trait"], i["type"]) for i in result["impls"]] == [
        (None, "Stack"),
        ("fmt::Display", "Stack"),
        (None, "Stack"),
    ]


@pytest.mark.unit
def test_go_generic_functions_are_kept() -> None:
    functions = get_parser("go").parse(_GO)["functions"]

    assert [f["name"] for f in functions] == ["Map", "Keys", "Plain"]
