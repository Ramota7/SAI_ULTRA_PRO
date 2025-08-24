import os
import time
import unittest
import importlib


class TestGateway(unittest.TestCase):
    def setUp(self):
        # asegurar entorno limpio
        self.state_path = os.path.join(os.getcwd(), 'artifacts', 'circuit_breaker.json')
        try:
            if os.path.exists(self.state_path):
                os.remove(self.state_path)
        except Exception:
            pass
        # reload module to ensure defaults
        import sai_ultra_pro.orders.gateway as gateway
        importlib.reload(gateway)
        self.gateway = gateway

    def tearDown(self):
        try:
            if os.path.exists(self.state_path):
                os.remove(self.state_path)
        except Exception:
            pass

    def test_opens_after_threshold_failures(self):
        broker = 'binance'
        symbol = 'TESTSYM'
        thr = getattr(self.gateway, 'THRESHOLD', 3)
        # generate thr failures
        for i in range(thr):
            self.gateway.record_order_result(broker, symbol, success=False)
        status = self.gateway.get_status(broker, symbol)
        self.assertTrue(status['open'], msg=f"Expected open after {thr} failures: {status}")
        self.assertFalse(self.gateway.order_allowed(broker, symbol))

    def test_success_resets_failures_and_closes(self):
        broker = 'binance'
        symbol = 'TESTSYM2'
        thr = getattr(self.gateway, 'THRESHOLD', 3)
        for i in range(thr):
            self.gateway.record_order_result(broker, symbol, success=False)
        # now record success
        self.gateway.record_order_result(broker, symbol, success=True)
        status = self.gateway.get_status(broker, symbol)
        self.assertFalse(status['open'])
        self.assertEqual(status['failures_count'], 0)


if __name__ == '__main__':
    unittest.main()
