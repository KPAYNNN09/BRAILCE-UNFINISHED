"""
Brailce Safe Arithmetic Engine
===============================

Deterministic arithmetic solver and pedagogical explanation generator
specifically designed for the Grade 1 DepEd curriculum (Method 1).

Pedagogical Principles (Grade 1 DepEd Mathematics):
    - Concrete, auditory step-by-step counting methods for blind learners.
    - Addition: "Counting on" (e.g. 5 + 3 -> start at 5, count up 6, 7, 8).
    - Subtraction: "Counting back" (e.g. 9 - 4 -> start at 9, count back 8, 7, 6, 5).
    - Zero Property: Adding or taking away 0 leaves the quantity unchanged.
    - Whole Numbers: Enforces whole-number constraints (no negative results in Grade 1).
    - Repeated Addition: Multiplications are explained as repeated groups.
    - Equal Sharing: Division explained as sharing equally among groups.
    - Deterministic & Safe: Absolutely no eval() or exec().
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List, Union

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MathSolution:
    """
    Structured outcome of an arithmetic calculation and pedagogical explanation.

    Attributes:
        expression:    Original cleaned math expression (e.g. "5 + 3").
        result:        Numeric result, or None if invalid/unsupported.
        result_str:    Display/speech representation of the result (e.g. "8").
        explanation:   Spoken step-by-step counting explanation for TTS.
        short_step:    Concise visual summary for compact display (e.g. "5 -> 6, 7, 8").
        is_valid:      Whether the expression was valid and solved.
        error_message: Optional friendly error explanation for the learner.
    """
    expression: str
    result: Optional[Union[int, float]]
    result_str: str
    explanation: str
    short_step: str
    is_valid: bool
    error_message: Optional[str] = None


class SafeArithmetic:
    """
    Deterministic solver for Grade 1 DepEd arithmetic problems.
    Generates step-by-step counting explanations without LLM dependencies.
    """

    @classmethod
    def solve(cls, raw_expr: str) -> MathSolution:
        """
        Parse and evaluate a math expression, generating a Grade 1 explanation.

        Args:
            raw_expr: A string such as "5 + 3", "9 - 4", "5+3=", or "12 + 5".

        Returns:
            MathSolution dataclass.
        """
        cleaned = raw_expr.strip()
        # Remove trailing equals if typed
        if cleaned.endswith("="):
            cleaned = cleaned[:-1].strip()

        # Replace visual math symbols
        cleaned = cleaned.replace("×", "*").replace("÷", "/")

        if not cleaned:
            return MathSolution(
                expression="",
                result=None,
                result_str="",
                explanation="Math buffer is empty. Please enter a math problem, such as 5 plus 3.",
                short_step="Empty",
                is_valid=False,
                error_message="Math buffer is empty."
            )

        # Check for invalid characters (letters, illegal symbols)
        invalid_chars = [ch for ch in cleaned if ch not in "0123456789+-*/. "]
        if invalid_chars:
            return MathSolution(
                expression=cleaned,
                result=None,
                result_str="",
                explanation=(
                    f"I found letters or unsupported symbols. "
                    f"Please enter numbers with plus or minus."
                ),
                short_step="Invalid characters",
                is_valid=False,
                error_message=f"Unsupported symbols: {', '.join(set(invalid_chars))}"
            )

        # Tokenize numbers and operators
        tokens = re.findall(r'(\d+(?:\.\d+)?|[+\-*/])', cleaned)
        if not tokens:
            return MathSolution(
                expression=cleaned,
                result=None,
                result_str="",
                explanation="Please enter a math problem, such as 5 plus 3.",
                short_step="Invalid input",
                is_valid=False,
                error_message="No valid math tokens found."
            )

        # Case 1: Single number entered (e.g. "5")
        if len(tokens) == 1:
            try:
                val = float(tokens[0])
                num = int(val) if val.is_integer() else val
                num_str = str(num)
                return MathSolution(
                    expression=cleaned,
                    result=num,
                    result_str=num_str,
                    explanation=f"{num_str} equals {num_str}.",
                    short_step=f"= {num_str}",
                    is_valid=True
                )
            except ValueError:
                pass

        # Check if first token is operator
        if tokens[0] in "+-*/":
            return MathSolution(
                expression=cleaned,
                result=None,
                result_str="",
                explanation="Please enter the first number before the operator.",
                short_step="Leading operator",
                is_valid=False,
                error_message="Expression cannot start with an operator."
            )

        # Validate token pattern: should alternate number, op, number, op, number...
        # E.g. [num, op, num]
        if len(tokens) % 2 == 0:
            last_token = tokens[-1]
            if last_token in "+-*/":
                op_word = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}.get(last_token, "operator")
                return MathSolution(
                    expression=cleaned,
                    result=None,
                    result_str="",
                    explanation=f"Incomplete math problem. Please enter a second number after the {op_word}.",
                    short_step="Incomplete",
                    is_valid=False,
                    error_message=f"Missing number after {last_token}"
                )
            return MathSolution(
                expression=cleaned,
                result=None,
                result_str="",
                explanation="Please enter a math problem like 5 plus 3.",
                short_step="Malformed",
                is_valid=False,
                error_message="Malformed expression."
            )

        # If exactly 3 tokens: Binary operation (most common Grade 1 scenario)
        if len(tokens) == 3:
            return cls._solve_binary(tokens[0], tokens[1], tokens[2], cleaned)

        # If more than 3 tokens: Chained operations (e.g. 2 + 3 + 4)
        return cls._solve_chained(tokens, cleaned)

    @classmethod
    def _solve_binary(cls, token_a: str, op: str, token_b: str, original_expr: str) -> MathSolution:
        """Evaluate a binary expression: A op B."""
        try:
            val_a = float(token_a)
            val_b = float(token_b)
        except ValueError:
            return MathSolution(
                expression=original_expr,
                result=None,
                result_str="",
                explanation="Could not read the numbers in your problem.",
                short_step="Error",
                is_valid=False,
                error_message="Invalid numeric tokens."
            )

        is_int = val_a.is_integer() and val_b.is_integer()
        a = int(val_a) if is_int else val_a
        b = int(val_b) if is_int else val_b

        canonical_expr = f"{a} {op} {b}"

        if op == "+":
            ans = a + b
            ans_str = str(ans)
            explanation, short_step = cls._explain_addition(a, b, ans)
            return MathSolution(
                expression=canonical_expr,
                result=ans,
                result_str=ans_str,
                explanation=explanation,
                short_step=short_step,
                is_valid=True
            )

        elif op == "-":
            # Grade 1 DepEd check: whole numbers only, no negative answers
            if a < b:
                return MathSolution(
                    expression=canonical_expr,
                    result=None,
                    result_str="",
                    explanation=(
                        f"In Grade 1 math, we cannot take away {b} from {a} "
                        f"because {b} is bigger than {a}."
                    ),
                    short_step=f"{a} < {b} (Not enough)",
                    is_valid=False,
                    error_message=f"Cannot subtract {b} from {a} in Grade 1."
                )

            ans = a - b
            ans_str = str(ans)
            explanation, short_step = cls._explain_subtraction(a, b, ans)
            return MathSolution(
                expression=canonical_expr,
                result=ans,
                result_str=ans_str,
                explanation=explanation,
                short_step=short_step,
                is_valid=True
            )

        elif op == "*":
            ans = a * b
            ans_str = str(ans)
            explanation, short_step = cls._explain_multiplication(a, b, ans)
            return MathSolution(
                expression=canonical_expr,
                result=ans,
                result_str=ans_str,
                explanation=explanation,
                short_step=short_step,
                is_valid=True
            )

        elif op == "/":
            if b == 0:
                return MathSolution(
                    expression=canonical_expr,
                    result=None,
                    result_str="",
                    explanation="Cannot divide by zero. We cannot split items into zero groups.",
                    short_step="Divide by zero",
                    is_valid=False,
                    error_message="Division by zero."
                )

            if isinstance(a, int) and isinstance(b, int) and a % b == 0:
                ans = a // b
                ans_str = str(ans)
                explanation = (
                    f"{a} divided by {b} equals {ans_str}. "
                    f"If you share {a} items equally into {b} groups, each group gets {ans_str}."
                )
                short_step = f"Share {a} in {b} groups = {ans_str}"
                return MathSolution(
                    expression=canonical_expr,
                    result=ans,
                    result_str=ans_str,
                    explanation=explanation,
                    short_step=short_step,
                    is_valid=True
                )
            elif isinstance(a, int) and isinstance(b, int):
                quot = a // b
                rem = a % b
                # Grade 1 DepEd Braille: Whole number division with remainder (no decimals/Nemeth)
                ans = quot
                ans_str = f"{quot} R{rem}"
                explanation = (
                    f"{a} divided by {b} equals {quot} with a remainder of {rem}. "
                    f"Each group gets {quot}, and there are {rem} left over."
                )
                short_step = f"{quot} R{rem}"
                return MathSolution(
                    expression=canonical_expr,
                    result=ans,
                    result_str=ans_str,
                    explanation=explanation,
                    short_step=short_step,
                    is_valid=True
                )
            else:
                ans = round(a / b, 2)
                ans_str = str(ans)
                explanation = f"{a} divided by {b} equals {ans_str}."
                short_step = f"= {ans_str}"
                return MathSolution(
                    expression=canonical_expr,
                    result=ans,
                    result_str=ans_str,
                    explanation=explanation,
                    short_step=short_step,
                    is_valid=True
                )

        return MathSolution(
            expression=original_expr,
            result=None,
            result_str="",
            explanation=f"Unsupported math operator: {op}",
            short_step="Unknown op",
            is_valid=False,
            error_message=f"Operator '{op}' is not supported."
        )

    # ---- Pedagogical Explanation Generators ----

    @classmethod
    def _explain_addition(cls, a: Union[int, float], b: Union[int, float], ans: Union[int, float]) -> Tuple[str, str]:
        """
        Generate Grade 1 'counting on' explanation for addition.
        """
        if not (isinstance(a, int) and isinstance(b, int) and isinstance(ans, int)):
            return (
                f"{a} plus {b} equals {ans}.",
                f"= {ans}"
            )

        # Zero property
        if a == 0 and b == 0:
            return (
                "0 plus 0 equals 0. Zero plus zero is still zero!",
                "= 0"
            )
        if b == 0:
            return (
                f"{a} plus 0 equals {ans}. Adding zero leaves {a} unchanged! The answer is {ans}.",
                f"{a} + 0 = {ans}"
            )
        if a == 0:
            return (
                f"0 plus {b} equals {ans}. Starting at zero and adding {b} gives {ans}.",
                f"0 + {b} = {ans}"
            )

        # Adding 1
        if b == 1:
            return (
                f"{a} plus 1 equals {ans}. Count up 1 more from {a}: {ans}. The answer is {ans}.",
                f"{a} -> {ans}"
            )

        # Adding small quantities (1 to 10) -> Pure Counting On
        if 1 < b <= 10:
            steps = list(range(a + 1, a + b + 1))
            steps_str = ", ".join(str(s) for s in steps)
            return (
                f"{a} plus {b} equals {ans}. Let's count together! "
                f"Start at {a}, and count up {b} more: {steps_str}. The answer is {ans}.",
                f"Start {a} -> {steps_str}"
            )

        # Adding larger 2-digit numbers -> Place Value (Tens and Ones)
        if a < 100 and b < 100:
            a_tens, a_ones = divmod(a, 10)
            b_tens, b_ones = divmod(b, 10)
            ones_sum = a_ones + b_ones
            tens_sum = a_tens + b_tens

            if ones_sum < 10:
                # No regrouping (DepEd Grade 1 Q3/Q4 standard)
                tens_val = tens_sum * 10
                return (
                    f"{a} plus {b} equals {ans}. Let's solve by place value! "
                    f"First add the ones: {a_ones} plus {b_ones} is {ones_sum}. "
                    f"Then add the tens: {a_tens} tens plus {b_tens} tens is {tens_sum} tens, or {tens_val}. "
                    f"{tens_val} plus {ones_sum} is {ans}.",
                    f"Ones: {ones_sum}, Tens: {tens_sum}0 -> {ans}"
                )
            else:
                # Regrouping
                intermediate = a + (b_tens * 10)
                return (
                    f"{a} plus {b} equals {ans}. Start at {a}. "
                    f"Add {b_tens * 10} to get {intermediate}, then add {b_ones} more to get {ans}.",
                    f"{a} + {b_tens*10} = {intermediate} -> {ans}"
                )

        return (
            f"{a} plus {b} equals {ans}. Start at {a} and add {b} to get {ans}.",
            f"{a} + {b} = {ans}"
        )

    @classmethod
    def _explain_subtraction(cls, a: Union[int, float], b: Union[int, float], ans: Union[int, float]) -> Tuple[str, str]:
        """
        Generate Grade 1 'counting back' explanation for subtraction.
        """
        if not (isinstance(a, int) and isinstance(b, int) and isinstance(ans, int)):
            return (
                f"{a} minus {b} equals {ans}.",
                f"= {ans}"
            )

        # Subtracting 0
        if b == 0:
            return (
                f"{a} minus 0 equals {ans}. Taking away zero leaves {a} unchanged! The answer is {ans}.",
                f"{a} - 0 = {ans}"
            )

        # Subtracting same number
        if a == b:
            return (
                f"{a} minus {b} equals 0. Taking away all {b} leaves zero! The answer is 0.",
                f"{a} - {b} = 0"
            )

        # Subtracting 1
        if b == 1:
            return (
                f"{a} minus 1 equals {ans}. Count back 1 from {a}: {ans}. The answer is {ans}.",
                f"{a} -> {ans}"
            )

        # Subtracting small quantities (1 to 10) -> Pure Counting Back
        if 1 < b <= 10:
            steps = list(range(a - 1, a - b - 1, -1))
            steps_str = ", ".join(str(s) for s in steps)
            return (
                f"{a} minus {b} equals {ans}. Let's count back! "
                f"Start at {a}, and count back {b}: {steps_str}. The answer is {ans}.",
                f"Start {a} -> {steps_str}"
            )

        # Subtracting larger 2-digit numbers -> Place Value
        if a < 100 and b < 100:
            a_tens, a_ones = divmod(a, 10)
            b_tens, b_ones = divmod(b, 10)

            if a_ones >= b_ones:
                # No regrouping (DepEd Grade 1 Q3/Q4 standard)
                ones_diff = a_ones - b_ones
                tens_diff = a_tens - b_tens
                tens_word = "ten" if tens_diff == 1 else "tens"
                return (
                    f"{a} minus {b} equals {ans}. First subtract the ones: "
                    f"{a_ones} minus {b_ones} is {ones_diff}. "
                    f"Then subtract the tens: {a_tens} tens minus {b_tens} tens is {tens_diff} {tens_word}. "
                    f"The answer is {ans}.",
                    f"Ones: {ones_diff}, Tens: {tens_diff}0 -> {ans}"
                )
            else:
                intermediate = a - (b_tens * 10)
                return (
                    f"{a} minus {b} equals {ans}. Start at {a}. "
                    f"Subtract {b_tens * 10} to get {intermediate}, then take away {b_ones} more to get {ans}.",
                    f"{a} - {b_tens*10} = {intermediate} -> {ans}"
                )

        return (
            f"{a} minus {b} equals {ans}. Start at {a} and take away {b} to get {ans}.",
            f"{a} - {b} = {ans}"
        )

    @classmethod
    def _explain_multiplication(cls, a: Union[int, float], b: Union[int, float], ans: Union[int, float]) -> Tuple[str, str]:
        """
        Generate Grade 1 'repeated addition / groups of' explanation for multiplication.
        """
        if not (isinstance(a, int) and isinstance(b, int) and isinstance(ans, int)):
            return (
                f"{a} times {b} equals {ans}.",
                f"= {ans}"
            )

        if a == 0 or b == 0:
            return (
                f"{a} times {b} equals 0. Any number multiplied by zero is zero.",
                f"{a} * {b} = 0"
            )

        if b == 1:
            return (
                f"{a} times 1 equals {ans}. 1 group of {a} is {ans}.",
                f"{a} * 1 = {ans}"
            )

        if a == 1:
            return (
                f"1 times {b} equals {ans}. 1 group of {b} is {ans}.",
                f"1 * {b} = {ans}"
            )

        # Repeated addition concept
        if a <= 5:
            groups_str = " plus ".join([str(b)] * a)
            return (
                f"{a} times {b} equals {ans}. That is {a} groups of {b}: "
                f"{groups_str} equals {ans}.",
                f"{a} groups of {b} = {ans}"
            )

        return (
            f"{a} times {b} equals {ans}. That is {a} groups of {b}, which makes {ans}.",
            f"{a} groups of {b} = {ans}"
        )

    @classmethod
    def _solve_chained(cls, tokens: List[str], original_expr: str) -> MathSolution:
        """
        Evaluate chained expressions with correct operator precedence (* and / before + and -).
        """
        try:
            # Check for division by zero upfront
            for idx in range(1, len(tokens), 2):
                if tokens[idx] == "/" and float(tokens[idx + 1]) == 0:
                    return MathSolution(
                        expression=original_expr,
                        result=None,
                        result_str="",
                        explanation="Cannot divide by zero.",
                        short_step="Divide by zero",
                        is_valid=False,
                        error_message="Division by zero."
                    )

            # Check if there are high-precedence operators (* or /) alongside low-precedence (+ or -)
            has_high = any(t in "*/" for t in tokens[1::2])
            has_low = any(t in "+-" for t in tokens[1::2])

            if has_high and has_low:
                # Precedence evaluation: Pass 1 (* and /), Pass 2 (+ and -)
                steps_desc = []
                cur_tokens = list(tokens)

                # Pass 1: Reduce all * and /
                idx = 1
                while idx < len(cur_tokens):
                    op = cur_tokens[idx]
                    if op in "*/":
                        a_val = float(cur_tokens[idx - 1])
                        b_val = float(cur_tokens[idx + 1])
                        a_str = str(int(a_val) if a_val.is_integer() else a_val)
                        b_str = str(int(b_val) if b_val.is_integer() else b_val)
                        if op == "*":
                            res = a_val * b_val
                            r_str = str(int(res) if res.is_integer() else round(res, 2))
                            steps_desc.append(f"multiply {a_str} and {b_str} to get {r_str}")
                        else:
                            res = a_val / b_val
                            r_str = str(int(res) if res.is_integer() else round(res, 2))
                            steps_desc.append(f"divide {a_str} by {b_str} to get {r_str}")

                        cur_tokens[idx - 1:idx + 2] = [r_str]
                    else:
                        idx += 2

                # Pass 2: Reduce all + and -
                idx = 1
                while idx < len(cur_tokens):
                    op = cur_tokens[idx]
                    a_val = float(cur_tokens[idx - 1])
                    b_val = float(cur_tokens[idx + 1])
                    a_str = str(int(a_val) if a_val.is_integer() else a_val)
                    b_str = str(int(b_val) if b_val.is_integer() else b_val)
                    if op == "-":
                        if a_val < b_val:
                            return MathSolution(
                                expression=original_expr,
                                result=None,
                                result_str="",
                                explanation=f"In Grade 1 math, we cannot take away {b_str} from {a_str}.",
                                short_step="Underflow",
                                is_valid=False,
                                error_message="Negative result encountered in chained subtraction."
                            )
                        res = a_val - b_val
                        r_str = str(int(res) if res.is_integer() else round(res, 2))
                        steps_desc.append(f"subtract {b_str} from {a_str} to get {r_str}")
                    else:
                        res = a_val + b_val
                        r_str = str(int(res) if res.is_integer() else round(res, 2))
                        steps_desc.append(f"add {a_str} and {b_str} to get {r_str}")

                    cur_tokens[idx - 1:idx + 2] = [r_str]

                final_val = float(cur_tokens[0])
                ans = int(final_val) if final_val.is_integer() else round(final_val, 2)
                ans_str = str(ans)

                if len(steps_desc) == 1:
                    explanation = f"{' '.join(tokens)} equals {ans_str}. {steps_desc[0].capitalize()}. The answer is {ans_str}."
                else:
                    first_steps = ", then ".join(steps_desc)
                    explanation = f"{' '.join(tokens)} equals {ans_str}. First {first_steps}. The final answer is {ans_str}."

                short_step = f"= {ans_str}"
                return MathSolution(
                    expression=" ".join(tokens),
                    result=ans,
                    result_str=ans_str,
                    explanation=explanation,
                    short_step=short_step,
                    is_valid=True
                )

            else:
                # Left-to-right evaluation for same-precedence operators (e.g. 2 + 3 + 4)
                current_val = float(tokens[0])
                steps_desc = []

                i = 1
                while i < len(tokens):
                    op = tokens[i]
                    next_val = float(tokens[i + 1])
                    prev_val = current_val

                    op_word = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}.get(op, op)

                    if op == "+":
                        current_val += next_val
                    elif op == "-":
                        if prev_val < next_val:
                            return MathSolution(
                                expression=original_expr,
                                result=None,
                                result_str="",
                                explanation=f"In Grade 1 math, we cannot take away {int(next_val)} from {int(prev_val)}.",
                                short_step="Underflow",
                                is_valid=False,
                                error_message="Negative result encountered in chained subtraction."
                            )
                        current_val -= next_val
                    elif op == "*":
                        current_val *= next_val
                    elif op == "/":
                        current_val /= next_val
                    else:
                        return MathSolution(
                            expression=original_expr,
                            result=None,
                            result_str="",
                            explanation=f"Unsupported operator: {op}",
                            short_step="Error",
                            is_valid=False,
                            error_message=f"Operator '{op}' is unsupported."
                        )

                    p_str = str(int(prev_val) if prev_val.is_integer() else prev_val)
                    n_str = str(int(next_val) if next_val.is_integer() else next_val)
                    c_str = str(int(current_val) if current_val.is_integer() else current_val)
                    steps_desc.append(f"{p_str} {op_word} {n_str} is {c_str}")
                    i += 2

                ans = int(current_val) if current_val.is_integer() else round(current_val, 2)
                ans_str = str(ans)
                explanation = (
                    f"{' '.join(tokens)} equals {ans_str}. "
                    + ". ".join(steps_desc)
                    + f". The final answer is {ans_str}."
                )
                short_step = " -> ".join([tokens[0]] + [str(int(current_val) if current_val.is_integer() else current_val)])

                return MathSolution(
                    expression=" ".join(tokens),
                    result=ans,
                    result_str=ans_str,
                    explanation=explanation,
                    short_step=short_step,
                    is_valid=True
                )

        except Exception as exc:
            logger.exception("Error evaluating chained expression: %s", exc)
            return MathSolution(
                expression=original_expr,
                result=None,
                result_str="",
                explanation="Could not calculate this problem.",
                short_step="Error",
                is_valid=False,
                error_message=str(exc)
            )
