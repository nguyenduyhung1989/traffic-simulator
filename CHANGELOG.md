# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Thêm cơ chế tự động kiểm tra và cấu hình môi trường (Python, cài đặt thư viện tự động qua `pip install -r requirements.txt`, cài đặt browser tự động qua `playwright install chromium`) vào `run.bat` để chạy được ở bất kỳ máy Windows nào.

### Fixed
- Sửa lỗi cứng đường dẫn python trong `run.bat` sang `python` toàn cục để tương thích khi di chuyển dự án giữa các máy tính.
