# SEG_FINAL — Vietnamese Recipe Search Engine

Máy tìm kiếm chuyên sâu cho công thức món ăn Việt Nam. Dự án tập trung vào toàn bộ pipeline của một search engine: thu thập dữ liệu, xử lý tiếng Việt, xây dựng inverted index, truy vấn, xếp hạng và đánh giá.

## Trạng thái hiện tại

**Phase 3 — Preprocessing and positional index**

- Cấu trúc backend theo module.
- Mô hình dữ liệu công thức thống nhất.
- Chuẩn hóa Unicode, khoảng trắng, chữ thường và tìm kiếm không dấu.
- Scrapy spider cho nguồn Món Ngon Mỗi Ngày.
- Extractor có semantic-heading parser và JSON-LD fallback.
- Kiểm tra dữ liệu bắt buộc và loại bỏ bản ghi trùng.
- Processed JSONL giữ nguyên dữ liệu gốc và thêm token theo từng trường.
- Tách từ tiếng Việt bằng `underthesea` với deterministic fallback.
- Custom inverted index lưu document ID, field, term frequency và token positions.
- Hai lexicon có dấu/không dấu phục vụ truy vấn tiếng Việt.
- Unit test nền tảng.

Frontend chưa nằm trong phạm vi của phase này.

## Kiến trúc dự kiến

```text
Websites
   -> Crawler
   -> Raw JSONL
   -> Cleaning and Vietnamese normalization
   -> Document store + custom inverted index
   -> TF-IDF baseline
   -> BM25F + phrase/proximity + Vietnamese query handling
   -> Optional semantic retrieval + rank fusion
   -> Flask search API
   -> Evaluation (P@10, MAP, MRR, nDCG, latency)
```

## Cấu trúc thư mục

```text
config/              Cấu hình crawler và ranking
data/                Dữ liệu raw, processed và ground truth
artifacts/           Chỉ mục và embedding được sinh tự động
docs/                Tài liệu kiến trúc
src/crawler/         Thu thập dữ liệu
src/models/          Mô hình dữ liệu dùng chung
src/preprocessing/   Chuẩn hóa và tách từ tiếng Việt
src/indexing/        Inverted index
src/query/           Xử lý truy vấn
src/retrieval/       TF-IDF, BM25F và semantic retrieval
src/ranking/         Boost và hợp nhất thứ hạng
src/evaluation/      Ground truth và metrics
src/api/             Flask API
tests/               Unit tests
```

## Yêu cầu môi trường

- Python 3.11 hoặc 3.12
- Git

## Cài đặt

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### macOS/Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Kiểm thử

```bash
python -m unittest discover -s tests -v
python -m pytest
python -m ruff check .
```

## Chạy crawler

Luôn chạy thử với một số lượng trang nhỏ trước:

```bash
scrapy crawl mnmn -a max_pages=2 -O data/raw/mnmn_recipes.jsonl
```

Sau khi kiểm tra file JSONL, có thể tăng giới hạn:

```bash
scrapy crawl mnmn -a max_pages=20 -O data/raw/mnmn_recipes.jsonl
```

Crawler mặc định tuân thủ `robots.txt`, chỉ gửi tối đa hai request đồng thời cho một tên miền, có download delay và AutoThrottle. Không tắt các giới hạn này khi thu thập dữ liệu cho đồ án.

## Tiền xử lý và xây dựng inverted index

Sau khi có file raw JSONL, chạy:

```bash
python -m src.indexing.build
```

Kết quả được sinh tại `data/processed/recipes.jsonl`, `artifacts/inverted_index.json.gz` và `artifacts/index_report.json`. Đây là artifact có thể tái tạo nên không được commit lên Git.

## Các mốc tiếp theo

1. Triển khai TF-IDF baseline và CLI search.
2. Nâng cấp BM25F, phrase search và xử lý truy vấn tiếng Việt.
3. Xây ground truth và so sánh các cấu hình retrieval.
