import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MasterDownloader import MasterDownloader


class VideoFormatTest(unittest.TestCase):
    def test_fallback_requires_video_and_audio(self):
        downloader = object.__new__(MasterDownloader)
        self.assertEqual(
            downloader._video_format(),
            "bestvideo+bestaudio/best[vcodec!=none][acodec!=none]",
        )


if __name__ == "__main__":
    unittest.main()
