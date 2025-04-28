import unittest
from unittest.mock import patch, MagicMock
from selenium.common.exceptions import WebDriverException
from ai_newsletter.selenium_pool.pool import (
    WebDriverPool,
    get_driver,
    initialize_pool,
    close_pool
)

class TestWebDriverPool(unittest.TestCase):
    def setUp(self):
        self.pool = WebDriverPool()
        
    def tearDown(self):
        self.pool.close_all()

    def test_pool_initialization(self):
        """Test that pool initializes with correct settings"""
        self.assertEqual(self.pool.max_size, 3)
        self.assertEqual(len(self.pool._drivers), 0)
        self.assertEqual(len(self.pool._in_use), 0)

    def test_get_driver(self):
        """Test driver acquisition and release"""
        driver = self.pool.get_driver()
        self.assertIsNotNone(driver)
        self.assertEqual(len(self.pool._in_use), 1)
        
        self.pool.release_driver(driver)
        self.assertEqual(len(self.pool._in_use), 0)
        self.assertEqual(len(self.pool._drivers), 1)

    def test_pool_capacity(self):
        """Test pool handles maximum capacity correctly"""
        drivers = []
        for _ in range(self.pool.max_size):
            driver = self.pool.get_driver()
            self.assertIsNotNone(driver)
            drivers.append(driver)
        
        # Pool should be full
        self.assertEqual(len(self.pool._in_use), self.pool.max_size)
        
        # Should raise error when trying to get another driver
        with self.assertRaises(WebDriverException):
            self.pool.get_driver()

    @patch('selenium.webdriver.Chrome')
    def test_driver_creation(self, mock_chrome):
        """Test driver creation with mocked Chrome"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        driver = self.pool.get_driver()
        self.assertIsNotNone(driver)
        mock_chrome.assert_called_once()

    def test_driver_reuse(self):
        """Test that drivers are reused when released"""
        driver1 = self.pool.get_driver()
        self.pool.release_driver(driver1)
        
        driver2 = self.pool.get_driver()
        self.assertEqual(id(driver1), id(driver2))

    def test_pool_cleanup(self):
        """Test pool cleanup on close"""
        driver = self.pool.get_driver()
        self.pool.close_all()
        
        self.assertEqual(len(self.pool._drivers), 0)
        self.assertEqual(len(self.pool._in_use), 0)

if __name__ == '__main__':
    unittest.main()