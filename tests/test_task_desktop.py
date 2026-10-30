"""Integração do botão Parar com a fila da interface; Qt não abre uma janela."""
import importlib.util
import unittest
from unittest.mock import Mock, patch

QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT, "PySide6 não instalado")
class DesktopTaskStopTests(unittest.TestCase):
    def test_new_message_does_not_resume_cancelled_old_operation(self):
        from yuna_desktop import DesktopWorker
        signals = Mock()
        worker = DesktopWorker(signals)
        worker.submit("pedido antigo")
        callbacks = []

        def handle(memory, message, computer, *, progress, cancelled):
            callbacks.append(cancelled)
            if message == "pedido antigo":
                worker.cancel_pending()
                worker.submit("pedido novo")
                self.assertTrue(cancelled())
                return "resposta antiga"
            self.assertFalse(cancelled())
            self.assertTrue(callbacks[0]())
            worker.queue.put(None)
            return "resposta nova"

        with patch("yuna_desktop.Memory") as memory, patch("yuna_desktop.Computer"), \
                patch("yuna_desktop.LIBRARY") as library, patch("yuna_desktop.handle_message", side_effect=handle):
            memory.return_value.db.execute.return_value.fetchall.return_value = []
            library.entries.return_value = []
            worker.run()
        signals.replied.emit.assert_called_once_with("resposta nova", False)
        memory.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
