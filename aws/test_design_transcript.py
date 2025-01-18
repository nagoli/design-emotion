import unittest
from unittest.mock import patch, MagicMock
import json
import os

import design_transcript


class TestLambdaFunctions(unittest.TestCase):

    @patch("design_transcript.redis_client")
    def test_get_cached_design_transcript_no_cache(self, mock_redis):
        """
        If there's no cached data in Redis, it should return None.
        """
        mock_redis.get.return_value = None

        result = design_transcript.get_cached_design_transcript(
            url="http://example.com",
            lang="en",
            etag="123",
            lastmodifieddate="2025-01-01T12:00:00Z"
        )
        self.assertIsNone(result, "Expected None when cache is missing.")

    @patch("design_transcript.redis_client")
    def test_get_cached_design_transcript_with_valid_cache(self, mock_redis):
        """
        If cache is valid and ETag matches, it should return the transcript directly.
        """
        cached_data = {
            "etag": "123",
            "lastmodifieddate": "2025-01-10T12:00:00Z",
            "transcripts": [
                ("en", "This is the cached transcript!")
            ]
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        result = design_transcript.get_cached_design_transcript(
            url="http://example.com",
            lang="en",
            etag="123",
            lastmodifieddate="2025-01-11T12:00:00Z"  # within 2 weeks
        )
        self.assertEqual(result, "This is the cached transcript!", "Should return cached transcript.")

    @patch("design_transcript._init_browser")
    def test_get_screenshot(self, mock_init_browser):
        """
        Test screenshot capturing, ensuring Playwright is called correctly.
        """
        # Mock browser, context, page
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_init_browser.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Simulate page.screenshot returning bytes
        mock_page.screenshot.return_value = b"fake_screenshot_data"

        url = "http://example.com"
        result = design_transcript.get_screen_shot(url)
        self.assertEqual(result, b"fake_screenshot_data", "Should return the screenshot bytes.")

        # Verify the evaluate call (hideModalElements)
        mock_page.evaluate.assert_called_once()

    @patch("design_transcript.openai.ChatCompletion.create")
    def test_generate_design_transcript(self, mock_chat_completion):
        """
        Test generating the transcript via ChatGPT.
        """
        mock_chat_completion.return_value = {
            "choices": [
                {"message": {"content": "Generated transcript from image."}}
            ]
        }

        result = design_transcript.generate_design_transcript(b"fake_image", "en")
        self.assertEqual(result, "Generated transcript from image.")

    @patch("design_transcript.get_cached_design_transcript")
    @patch("design_transcript.get_screen_shot")
    @patch("design_transcript.generate_design_transcript")
    @patch("design_transcript.redis_client")
    def test_get_design_transcript_flow(
        self, mock_redis, mock_generate, mock_screenshot, mock_cache
    ):
        """
        End-to-end test of get_design_transcript.
        """
        # If the cache is missing or invalid, the code should do a screenshot + generation + store in cache
        mock_cache.return_value = None
        mock_screenshot.return_value = b"fake_screenshot_data"
        mock_generate.return_value = "A newly generated transcript."
        mock_redis.set = MagicMock()

        transcript = design_transcript.get_design_transcript(
            url="http://example.com?someparam=123",
            etag="etag_val",
            lastmodifieddate="2025-01-01T00:00:00Z",
            lang="en"
        )

        self.assertEqual(transcript, "A newly generated transcript.")

        # Verify screenshot and transcript generation were called
        mock_screenshot.assert_called_once()
        mock_generate.assert_called_once()

        # Verify something was stored in Redis
        mock_redis.set.assert_called_once()
        cache_key, cache_value = mock_redis.set.call_args[0]
        self.assertIn("transcript_cache:http://example.com", cache_key)

        # Check that the stored data is as expected
        stored_data = json.loads(cache_value)
        self.assertEqual(stored_data["etag"], "etag_val")
        self.assertEqual(stored_data["lastmodifieddate"], "2025-01-01T00:00:00Z")
        self.assertEqual(stored_data["transcripts"], [("en", "A newly generated transcript.")])


if __name__ == "__main__":
    unittest.main()