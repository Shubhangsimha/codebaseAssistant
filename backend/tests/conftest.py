import pytest


PYTHON_SAMPLE = '''\
"""Module docstring."""
import os
import sys


class MyClass:
    """A class."""

    def method_one(self):
        return 1

    def method_two(self, x):
        return x * 2


def standalone_func(a, b):
    return a + b


def another_func():
    pass
'''

JS_SAMPLE = '''\
const express = require('express');
const router = express.Router();

router.get('/users', (req, res) => {
    res.json([]);
});

function handleAuth(req, res) {
    return res.status(200).send('ok');
}

class UserController {
    getUser(id) {
        return null;
    }
}
'''

LONG_PYTHON_SAMPLE = ("x = 1\n" * 600)
