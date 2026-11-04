"""
Brailce Tests – SafeArithmetic Engine (Method 1)
=================================================

Comprehensive test suite verifying deterministic arithmetic and
Grade 1 DepEd pedagogical step-by-step counting explanations.
"""

import pytest

from brailce.braille.arithmetic import SafeArithmetic, MathSolution


class TestSafeArithmeticAddition:
    """Tests for addition in Grade 1 DepEd curriculum."""

    def test_single_number(self) -> None:
        sol = SafeArithmetic.solve("5")
        assert sol.is_valid
        assert sol.result == 5
        assert sol.result_str == "5"
        assert sol.explanation == "5 equals 5."

    def test_basic_counting_on(self) -> None:
        sol = SafeArithmetic.solve("5 + 3")
        assert sol.is_valid
        assert sol.result == 8
        assert sol.result_str == "8"
        assert "Start at 5, and count up 3 more: 6, 7, 8" in sol.explanation
        assert "The answer is 8." in sol.explanation
        assert sol.short_step == "Start 5 -> 6, 7, 8"

    def test_addition_no_spaces(self) -> None:
        sol = SafeArithmetic.solve("4+2")
        assert sol.is_valid
        assert sol.result == 6
        assert "Start at 4, and count up 2 more: 5, 6" in sol.explanation

    def test_addition_with_trailing_equals(self) -> None:
        sol = SafeArithmetic.solve("7 + 3 =")
        assert sol.is_valid
        assert sol.result == 10
        assert sol.result_str == "10"
        assert "Start at 7, and count up 3 more: 8, 9, 10" in sol.explanation

    def test_adding_one(self) -> None:
        sol = SafeArithmetic.solve("6 + 1")
        assert sol.is_valid
        assert sol.result == 7
        assert "Count up 1 more from 6: 7" in sol.explanation

    def test_adding_zero(self) -> None:
        sol = SafeArithmetic.solve("9 + 0")
        assert sol.is_valid
        assert sol.result == 9
        assert "Adding zero leaves 9 unchanged!" in sol.explanation

    def test_zero_plus_number(self) -> None:
        sol = SafeArithmetic.solve("0 + 7")
        assert sol.is_valid
        assert sol.result == 7
        assert "Starting at zero and adding 7 gives 7." in sol.explanation

    def test_zero_plus_zero(self) -> None:
        sol = SafeArithmetic.solve("0 + 0")
        assert sol.is_valid
        assert sol.result == 0
        assert "0 plus 0 equals 0" in sol.explanation

    def test_two_digit_addition_no_regrouping(self) -> None:
        # DepEd Grade 1 Q3/Q4 place value standard
        sol = SafeArithmetic.solve("14 + 23")
        assert sol.is_valid
        assert sol.result == 37
        assert "First add the ones: 4 plus 3 is 7" in sol.explanation
        assert "Then add the tens: 1 tens plus 2 tens is 3 tens, or 30" in sol.explanation


class TestSafeArithmeticSubtraction:
    """Tests for subtraction in Grade 1 DepEd curriculum."""

    def test_basic_counting_back(self) -> None:
        sol = SafeArithmetic.solve("9 - 4")
        assert sol.is_valid
        assert sol.result == 5
        assert sol.result_str == "5"
        assert "Start at 9, and count back 4: 8, 7, 6, 5" in sol.explanation
        assert "The answer is 5." in sol.explanation
        assert sol.short_step == "Start 9 -> 8, 7, 6, 5"

    def test_subtracting_one(self) -> None:
        sol = SafeArithmetic.solve("8 - 1")
        assert sol.is_valid
        assert sol.result == 7
        assert "Count back 1 from 8: 7" in sol.explanation

    def test_subtracting_zero(self) -> None:
        sol = SafeArithmetic.solve("7 - 0")
        assert sol.is_valid
        assert sol.result == 7
        assert "Taking away zero leaves 7 unchanged!" in sol.explanation

    def test_subtracting_same_number(self) -> None:
        sol = SafeArithmetic.solve("6 - 6")
        assert sol.is_valid
        assert sol.result == 0
        assert "Taking away all 6 leaves zero!" in sol.explanation

    def test_underflow_grade1_constraint(self) -> None:
        # In Grade 1 DepEd, students learn that a bigger number cannot be taken from a smaller whole number
        sol = SafeArithmetic.solve("3 - 5")
        assert not sol.is_valid
        assert sol.result is None
        assert "In Grade 1 math, we cannot take away 5 from 3 because 5 is bigger than 3." in sol.explanation
        assert sol.error_message is not None

    def test_two_digit_subtraction_no_regrouping(self) -> None:
        sol = SafeArithmetic.solve("28 - 13")
        assert sol.is_valid
        assert sol.result == 15
        assert "First subtract the ones: 8 minus 3 is 5" in sol.explanation
        assert "Then subtract the tens: 2 tens minus 1 tens is 1 ten" in sol.explanation


class TestSafeArithmeticMultiplicationAndDivision:
    """Tests for multiplication and division in SafeArithmetic."""

    def test_multiplication_repeated_addition(self) -> None:
        sol = SafeArithmetic.solve("3 * 2")
        assert sol.is_valid
        assert sol.result == 6
        assert "That is 3 groups of 2: 2 plus 2 plus 2 equals 6." in sol.explanation

    def test_multiplication_by_zero(self) -> None:
        sol = SafeArithmetic.solve("5 * 0")
        assert sol.is_valid
        assert sol.result == 0
        assert "Any number multiplied by zero is zero." in sol.explanation

    def test_multiplication_by_one(self) -> None:
        sol = SafeArithmetic.solve("4 * 1")
        assert sol.is_valid
        assert sol.result == 4
        assert "1 group of 4 is 4." in sol.explanation

    def test_division_equal_sharing(self) -> None:
        sol = SafeArithmetic.solve("6 / 2")
        assert sol.is_valid
        assert sol.result == 3
        assert "If you share 6 items equally into 2 groups, each group gets 3." in sol.explanation

    def test_division_with_remainder(self) -> None:
        sol = SafeArithmetic.solve("7 / 2")
        assert sol.is_valid
        assert "7 divided by 2 equals 3 with a remainder of 1." in sol.explanation

    def test_division_by_zero(self) -> None:
        sol = SafeArithmetic.solve("5 / 0")
        assert not sol.is_valid
        assert "Cannot divide by zero" in sol.explanation


class TestSafeArithmeticChainedAndEdgeCases:
    """Tests for chained expressions and error states."""

    def test_chained_addition(self) -> None:
        sol = SafeArithmetic.solve("2 + 3 + 4")
        assert sol.is_valid
        assert sol.result == 9
        assert "2 plus 3 is 5" in sol.explanation
        assert "5 plus 4 is 9" in sol.explanation

    def test_empty_input(self) -> None:
        sol = SafeArithmetic.solve("")
        assert not sol.is_valid
        assert "Math buffer is empty" in sol.explanation

    def test_invalid_letters(self) -> None:
        sol = SafeArithmetic.solve("5 + A")
        assert not sol.is_valid
        assert "letters or unsupported symbols" in sol.explanation

    def test_incomplete_expression(self) -> None:
        sol = SafeArithmetic.solve("5 +")
        assert not sol.is_valid
        assert "Missing number after +" in sol.error_message

    def test_leading_operator(self) -> None:
        sol = SafeArithmetic.solve("+ 5")
        assert not sol.is_valid
        assert "Expression cannot start with an operator" in sol.error_message
