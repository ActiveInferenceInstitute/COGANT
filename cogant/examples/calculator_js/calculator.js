/**
 * Simple calculator with state machine (JavaScript port of
 * ``examples/control_positive/calculator/calculator.py``).
 *
 * Role contract (used by cross-language differential tests):
 *   - display, accumulator, operation, history, new_input: hidden state
 *   - input_digit, input_operation, equals, clear: actions
 *   - _execute_operation: hidden state transition
 *   - get_display, get_history: observations
 *   - assert_display, assert_history_length: preferences
 *
 * This file is intentionally kept free of external dependencies so the
 * tree-sitter JavaScript parser can walk it without a tool-chain.
 */

"use strict";

class Calculator {
  constructor() {
    // Hidden state
    this.display = "0";
    this.accumulator = 0;
    this.operation = null;
    this.history = [];
    this.new_input = true;
  }

  input_digit(digit) {
    // Action: input a digit (0-9).
    if (digit < 0 || digit > 9) {
      return this.display;
    }

    if (this.new_input) {
      this.display = String(digit);
      this.new_input = false;
    } else {
      this.display = this.display + String(digit);
    }

    this.history.push(`input_digit(${digit})`);
    return this.display;
  }

  input_operation(op) {
    // Action: input operation (+, -, *, /).
    const current_value = parseInt(this.display, 10);

    if (this.operation !== null) {
      // Execute pending operation.
      this.accumulator = this._execute_operation(
        this.accumulator,
        current_value,
        this.operation,
      );
      this.display = String(this.accumulator);
    } else {
      this.accumulator = current_value;
    }

    this.operation = op;
    this.new_input = true;
    this.history.push(`input_operation(${op})`);
    return this.display;
  }

  equals() {
    // Action: execute equals.
    if (this.operation === null) {
      return this.display;
    }

    const current_value = parseInt(this.display, 10);
    const result = this._execute_operation(
      this.accumulator,
      current_value,
      this.operation,
    );

    this.display = String(result);
    this.operation = null;
    this.accumulator = 0;
    this.new_input = true;
    this.history.push("equals()");
    return this.display;
  }

  clear() {
    // Action: clear the calculator.
    this.display = "0";
    this.accumulator = 0;
    this.operation = null;
    this.new_input = true;
    this.history.push("clear()");
    return this.display;
  }

  _execute_operation(left, right, op) {
    // Hidden state operation.
    if (op === "+") {
      return left + right;
    } else if (op === "-") {
      return left - right;
    } else if (op === "*") {
      return left * right;
    } else if (op === "/" && right !== 0) {
      return Math.trunc(left / right);
    }
    return left;
  }

  get_display() {
    // Observation: current display value.
    return this.display;
  }

  get_history() {
    // Observation: operation history.
    return this.history.slice();
  }

  assert_display(expected) {
    // Preference: assertion on display.
    return this.display === expected;
  }

  assert_history_length(max_length) {
    // Preference: constraint on history size.
    return this.history.length <= max_length;
  }
}

module.exports = { Calculator };
