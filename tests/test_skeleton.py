# -*- coding: utf-8 -*-

import pytest
from ct_h2o.skeleton import fib

__author__ = "yode049"
__copyright__ = "yode049"
__license__ = "mit"


def test_fib():
    assert fib(1) == 1
    assert fib(2) == 1
    assert fib(7) == 13
    with pytest.raises(AssertionError):
        fib(-10)
