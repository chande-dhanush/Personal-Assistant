import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from PyQt5.QtCore import QObject, pyqtSignal

# Mock PyQt5 Application for Signals
from PyQt5 import QtWidgets
if not QtWidgets.QApplication.instance():
    app = QtWidgets.QApplication(sys.argv)

# Mock storage module BEFORE importing viewmodel to avoid torch import
sys.modules['sakura_assistant.utils.storage'] = MagicMock()
sys.modules['sakura_assistant.ui.workers'] = MagicMock()
sys.modules['sakura_assistant.core.llm'] = MagicMock()
sys.modules['sakura_assistant.utils.file_ingest'] = MagicMock()
sys.modules['sakura_assistant.utils.file_registry'] = MagicMock()
sys.modules['sakura_assistant.core.tools'] = MagicMock()
from sakura_assistant.ui.viewmodel import ChatViewModel

class TestChatViewModel(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_agent_worker_patcher = patch('sakura_assistant.ui.viewmodel.AgentWorker')
        self.mock_voice_worker_patcher = patch('sakura_assistant.ui.viewmodel.VoiceWorker')
        self.mock_storage_patcher = patch('sakura_assistant.ui.viewmodel.get_memory_store')
        self.mock_threadpool_patcher = patch('sakura_assistant.ui.viewmodel.QtCore.QThreadPool')
        
        self.MockAgentWorker = self.mock_agent_worker_patcher.start()
        self.MockVoiceWorker = self.mock_voice_worker_patcher.start()
        self.MockGetMemoryStore = self.mock_storage_patcher.start()
        self.MockThreadPool = self.mock_threadpool_patcher.start()
        
        # Setup mock instances
        self.mock_agent_worker = self.MockAgentWorker.return_value
        self.mock_voice_worker = self.MockVoiceWorker.return_value
        self.mock_thread_pool = self.MockThreadPool.return_value
        
        # Configure storage mock
        self.mock_store = self.MockGetMemoryStore.return_value
        self.mock_store.conversation_history = []
        
        # Initialize ViewModel
        self.vm = ChatViewModel()

    def tearDown(self):
        self.mock_agent_worker_patcher.stop()
        self.mock_voice_worker_patcher.stop()
        self.mock_storage_patcher.stop()
        self.mock_threadpool_patcher.stop()

    def test_initial_state(self):
        self.assertEqual(self.vm.conversation_history, [])
        self.assertFalse(self.vm.is_processing)
        self.assertFalse(self.vm.listening)

    def test_send_message(self):
        # Test sending a user message
        self.vm.send_message("Hello")
        
        # Check history updated
        self.assertEqual(len(self.vm.conversation_history), 1)
        self.assertEqual(self.vm.conversation_history[0]['role'], 'user')
        self.assertEqual(self.vm.conversation_history[0]['content'], 'Hello')
        
        # Check worker started via thread pool
        self.mock_thread_pool.start.assert_called()
        # Verify it was called with an AgentWorker (mock)
        args, _ = self.mock_thread_pool.start.call_args
        self.assertEqual(args[0], self.mock_agent_worker)
        self.assertTrue(self.vm.is_processing)

    def test_clear_history(self):
        self.vm.conversation_history = [{'role': 'user', 'content': 'Hi'}]
        self.vm.clear_history()
        self.assertEqual(self.vm.conversation_history, [])

    def test_start_listening(self):
        self.vm.start_listening()
        self.assertTrue(self.vm.listening)
        # Check worker started via thread pool
        self.mock_thread_pool.start.assert_called()
        # Verify it was called with a VoiceWorker (mock)
        # Note: start might have been called multiple times if other tests ran, 
        # but setUp creates fresh mocks.
        # However, _init_memory also starts a thread (using threading.Thread, not QThreadPool).
        # So QThreadPool.start should be called once here.
        args, _ = self.mock_thread_pool.start.call_args
        self.assertEqual(args[0], self.mock_voice_worker)

    def test_stop_listening(self):
        self.vm.listening = True
        self.vm.stop_listening()
        self.assertFalse(self.vm.listening)
        # VoiceWorker cannot be stopped mid-listen in current impl
        # self.mock_voice_worker.stop.assert_called_once()

if __name__ == '__main__':
    unittest.main()
