# SEG_FINAL — Vietnamese Recipe Search Engine

Máy tìm kiếm chuyên sâu cho công thức món ăn Việt Nam. Dự án tập trung vào toàn bộ pipeline của một search engine: thu thập dữ liệu, xử lý tiếng Việt, xây dựng inverted index, truy vấn, xếp hạng và đánh giá.

## Trạng thái hiện tại

**Phase 1 — Foundation**

- Cấu trúc backend theo module.
- Mô hình dữ liệu công thức thống nhất.
- Chuẩn hóa Unicode, khoảng trắng, chữ thường và tìm kiếm không dấu.
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

## Các mốc tiếp theo

1. Khảo sát cấu trúc HTML và viết crawler có rate limit.
2. Xây dựng processed dataset và báo cáo chất lượng dữ liệu.
3. Xây dựng custom inverted index có term positions.
4. Triển khai TF-IDF baseline và CLI search.
5. Nâng cấp BM25F, phrase search và xử lý truy vấn tiếng Việt.
6. Xây ground truth và so sánh các cấu hình retrieval.
