import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MasterDownloader import MasterDownloader


class SocialMediaDownloadOptionsTest(unittest.TestCase):
    def setUp(self):
        self.downloader = object.__new__(MasterDownloader)
        self.downloader.base_dir = os.getcwd()
        self.downloader.archive_dir = os.getcwd()
        self.downloader.ig_sleep_range = (1, 2)
        self.downloader.ig_max_posts = 0
        self.downloader.ig = MagicMock()
        self.downloader.ig.context.user_agent = "test-agent"
        self.downloader.get_manual_cookie = MagicMock(return_value=None)
        self.downloader._merge_archive_once = MagicMock()
        ydl = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = ydl
        context.__exit__.return_value = False
        self.downloader._prepare_yt_dlp = MagicMock(return_value=context)

    @patch("MasterDownloader.subprocess.Popen")
    def test_tiktok_photo_uses_gallery_dl_with_photos_enabled(self, popen):
        process = popen.return_value
        process.stdout = iter(())
        process.wait.return_value = 0

        for url in (
            "https://www.tiktok.com/@user/photo/123",
            "https://vm.tiktok.com/abc123/",
        ):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as folder:
                self.downloader.download_tiktok(url, output_folder=folder)
                cmd = popen.call_args.args[0]
                self.assertIn("gallery_dl", cmd)
                self.assertIn("extractor.tiktok.photos=true", cmd)

    @patch("MasterDownloader.subprocess.Popen")
    def test_instagram_enables_audio_downloads(self, popen):
        process = popen.return_value
        process.stdout = iter(())
        process.wait.return_value = 0

        with tempfile.TemporaryDirectory() as folder:
            self.downloader.download_instagram_gallerydl(
                "https://www.instagram.com/p/abc/", output_folder=folder
            )

        cmd = popen.call_args.args[0]
        self.assertIn("extractor.instagram.audio=true", cmd)


if __name__ == "__main__":
    unittest.main()
