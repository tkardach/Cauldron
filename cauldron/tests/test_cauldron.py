from cauldron import ICauldron, CauldronService
import unittest


class MockCauldron(ICauldron):
    def __init__(self):
        self.explosion_called_count = 0

    def cause_explosion(self):
        self.explosion_called_count += 1


class TestCauldron(unittest.TestCase):
    def test_cauldron_service(self):
        cauldron = MockCauldron()
        service = CauldronService(cauldron)

        self.assertEqual(cauldron.explosion_called_count, 0)
        num_calls = 5
        for _ in range(num_calls):
            service.cause_explosion()

        self.assertEqual(cauldron.explosion_called_count, num_calls)


if __name__ == "__main__":
    unittest.main()
