import unittest
from unittest.mock import patch, MagicMock
import json
import os

import design_transcript
from design_transcript import is_within_two_weeks


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

    @patch("design_transcript.openai.OpenAI")
    def test_generate_design_transcript(self, mock_chat_completion):
        """
        Test generating the transcript via ChatGPT.
        """
        mock_chat_completion.return_value = {
            "choices": [
                {"message": {"content": "Generated transcript from image."}}
            ]
        }

        #result = design_transcript.generate_design_transcript(b"fake_image", "en")
        #self.assertEqual(result, "Generated transcript from image.")

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
            lastmodifieddate="Mon, 02 Sep 2024 20:45:53 GMT",
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
        self.assertEqual(stored_data["lastmodifieddate"], "Mon, 02 Sep 2024 20:45:53 GMT")
        self.assertEqual(stored_data["transcripts"], [["en", "A newly generated transcript."]])

        # Verify the cache is valid for less than two weeks
        self.assertTrue(is_within_two_weeks("Mon, 02 Sep 2024 20:45:53 GMT", "Mon, 12 Sep 2024 20:45:53 GMT"))
        
class TestWithinTwoWeeks(unittest.TestCase):            
    def test_identical_dates_iso8601(self):
        """Test avec deux dates identiques au format ISO 8601"""
        date1 = "2025-01-10T12:00:00Z"
        date2 = "2025-01-10T12:00:00Z"
        self.assertTrue(is_within_two_weeks(date1, date2), "Les dates identiques devraient retourner True.")

    def test_dates_less_than_two_weeks_iso8601(self):
        """Test avec des dates espacées de 10 jours au format ISO 8601"""
        date1 = "2025-01-10T12:00:00Z"
        date2 = "2025-01-20T12:00:00Z"
        self.assertTrue(is_within_two_weeks(date1, date2), "Les dates espacées de 10 jours devraient retourner True.")

    def test_dates_exactly_two_weeks_iso8601(self):
        """Test avec des dates espacées exactement de 14 jours au format ISO 8601"""
        date1 = "2025-01-10T12:00:00Z"
        date2 = "2025-01-24T12:00:00Z"
        self.assertFalse(is_within_two_weeks(date1, date2), "Les dates espacées exactement de deux semaines devraient retourner False.")

    def test_dates_more_than_two_weeks_iso8601(self):
        """Test avec des dates espacées de plus de deux semaines au format ISO 8601"""
        date1 = "2025-01-10T12:00:00Z"
        date2 = "2025-02-01T12:00:00Z"
        self.assertFalse(is_within_two_weeks(date1, date2), "Les dates espacées de plus de deux semaines devraient retourner False.")

    def test_incorrect_date_format(self):
        """Test avec un format de date incorrect"""
        date1 = "2025-01-10 12:00:00"  # Incorrect, manque le 'T' et le 'Z'
        date2 = "2025-01-20T12:00:00Z"
        self.assertFalse(is_within_two_weeks(date1, date2), "Un format de date incorrect devrait retourner False.")

    def test_mixed_formats_less_than_two_weeks(self):
        """Test avec des formats de date mixtes espacés de moins de deux semaines"""
        date1 = "2025-01-10T12:00:00Z"  # ISO 8601
        date2 = "Sat, 20 Jan 2025 12:00:00 GMT"  # RFC 1123
        self.assertTrue(is_within_two_weeks(date1, date2), "Les formats mixtes espacés de moins de deux semaines devraient retourner True.")

    def test_mixed_formats_more_than_two_weeks(self):
        """Test avec des formats de date mixtes espacés de plus de deux semaines"""
        date1 = "2025-01-10T12:00:00Z"  # ISO 8601
        date2 = "Sat, 01 Feb 2025 12:00:00 GMT"  # RFC 1123
        self.assertFalse(is_within_two_weeks(date1, date2), "Les formats mixtes espacés de plus de deux semaines devraient retourner False.")

    def test_one_correct_one_incorrect_format(self):
        """Test avec un format correct et un format incorrect"""
        date1 = "Sat, 25 Jan 2025 12:00:00 GMT"  # RFC 1123
        date2 = "2025-01-25 12:00:00"  # Incorrect
        self.assertFalse(is_within_two_weeks(date1, date2), "Un format correct et un incorrect devraient retourner False.")

    def test_no_lastmodifieddate(self):
        """Test avec une des dates manquante"""
        date1 = "2025-01-10T12:00:00Z"
        date2 = ""  # Vide
        self.assertFalse(is_within_two_weeks(date1, date2), "Une des dates manquantes devrait retourner False.")

    def test_future_dates_less_than_two_weeks(self):
        """Test avec des dates futures espacées de moins de deux semaines"""
        date1 = "2025-12-01T12:00:00Z"
        date2 = "2025-12-10T12:00:00Z"
        self.assertTrue(is_within_two_weeks(date1, date2), "Les dates futures espacées de moins de deux semaines devraient retourner True.")

    def test_future_dates_more_than_two_weeks(self):
        """Test avec des dates futures espacées de plus de deux semaines"""
        date1 = "2025-12-01T12:00:00Z"
        date2 = "2025-12-20T12:00:00Z"
        self.assertFalse(is_within_two_weeks(date1, date2), "Les dates futures espacées de plus de deux semaines devraient retourner False.")


if __name__ == "__main__":
    unittest.main()