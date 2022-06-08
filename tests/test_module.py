import unittest

import stactools.deltares


class TestModule(unittest.TestCase):
    def test_version(self) -> None:
        self.assertIsNotNone(stactools.deltares.__version__)
