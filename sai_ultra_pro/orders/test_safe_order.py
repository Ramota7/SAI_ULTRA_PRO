import os
import unittest
import importlib


class TestSafeOrder(unittest.TestCase):
    def setUp(self):
        # ensure imports fresh
        import sai_ultra_pro.orders.safe_order as safe_order
        importlib.reload(safe_order)
        self.safe = safe_order
        # patch main.MODO_OBSERVACION to True for dry-run
        import sai_ultra_pro.main as main_mod
        main_mod.MODO_OBSERVACION = True

    def tearDown(self):
        import sai_ultra_pro.main as main_mod
        main_mod.MODO_OBSERVACION = False

    def test_dry_run_blocks_send(self):
        import sai_ultra_pro.main as main_mod
        main_mod.MODO_OBSERVACION = True
        res = self.safe.send_order('binance', 'buy', 'BTCUSDT', 0.001, api_key='a', api_secret='b')
        self.assertIsNone(res)

    def test_send_calls_real_when_allowed(self):
        # Simulate allowed path by toggling MODO_OBSERVACION False and patching gateway and main send
        import sai_ultra_pro.main as main_mod
        main_mod.MODO_OBSERVACION = False

        # monkeypatch gateway
        import sai_ultra_pro.orders.gateway as gateway
        gateway_state = {}

        def fake_order_allowed(broker, symbol):
            return True

        def fake_record(broker, symbol, success):
            gateway_state['last'] = (broker, symbol, success)

        gateway.order_allowed = fake_order_allowed
        gateway.record_order_result = fake_record

        # monkeypatch enviar_orden_binance
        def fake_send(api_key, api_secret, simbolo, cantidad):
            return {'status': 'FILLED'}

        main_mod.enviar_orden_binance = fake_send

        res = self.safe.send_order('binance', 'buy', 'BTCUSDT', 0.001, api_key='a', api_secret='b')
        self.assertIsNotNone(res)
        self.assertIn('status', res)
        self.assertEqual(gateway_state.get('last'), ('binance', 'BTCUSDT', True))


if __name__ == '__main__':
    unittest.main()
