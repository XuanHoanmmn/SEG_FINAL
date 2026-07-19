# SEG_FINAL — Vietnamese Recipe Search Engine

Máy tìm kiếm chuyên sâu cho công thức món ăn Việt Nam. Dự án tập trung vào toàn bộ pipeline của một search engine: thu thập dữ liệu, xử lý tiếng Việt, xây dựng inverted index, truy vấn, xếp hạng và đánh giá.

## Trạng thái hiện tại

**Phase 10 — Corpus Scaling and Coverage Audit**

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
- Field-weighted TF-IDF baseline có giải thích matched terms/fields.
- CLI tìm kiếm tương tác, truy vấn một lần và JSON output.
- BM25F có field-length normalization và vẫn giữ TF-IDF để đánh giá đối chứng.
- Exact phrase/proximity boost dùng token positions trong custom index.
- Bộ lọc không phụ thuộc dấu: thời gian, độ khó, category, nguyên liệu và cách nấu.
- Bộ 20 evaluation queries và pooled relevance judging có thể resume.
- Metrics chuẩn IR: P@10, MAP, Recall@20, MRR@10, nDCG@10 và p50/p95 latency.
- Báo cáo so sánh TF-IDF/BM25F dạng JSON và CSV dùng cho Excel.
- Làm sạch có kiểm toán cho nhãn đơn vị và mô tả gợi ý bị lẫn vào công thức.
- Query expansion có trọng số cho khoảng trống từ vựng `hải sản`.
- Kết quả tìm kiếm giải thích rõ các từ được tự động mở rộng.
- Flask Search API v1 nạp index một lần, có health check và lỗi JSON thống nhất.
- Pagination, facets, snippet/highlight an toàn và giải thích điểm theo trường.
- Giao diện responsive gồm trang chủ, trang kết quả và trạng thái tải/lỗi/rỗng.
- Bộ lọc facets, chuyển BM25F/TF-IDF và phân trang được đồng bộ lên URL.
- Result card có ảnh, metadata, highlight an toàn và score explanation mở rộng.
- Frontend HTML/CSS/JavaScript được phục vụ bởi Flask, không phụ thuộc CDN.
- Full-crawl mode đi hết listing công khai, tự dừng khi trang lặp và có hard safety limit.
- Báo cáo corpus thống kê nguồn, danh mục, cách nấu, độ khó và độ đầy đủ từng trường.
- Query probes kiểm chứng trực tiếp món nào có/không có trong index hiện tại.
- Unit test nền tảng.

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
   -> Flask search API + responsive web interface
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

Lệnh trên chỉ tạo một mẫu nhỏ để kiểm tra crawler, không phải corpus dùng cho
demo cuối kỳ. Sau khi kiểm tra file JSONL, crawl toàn bộ listing công khai:

```bash
scrapy crawl mnmn -a max_pages=all -O data/raw/mnmn_recipes.jsonl
```

Crawler mặc định tuân thủ `robots.txt`, chỉ gửi tối đa hai request đồng thời cho một tên miền, có download delay và AutoThrottle. Không tắt các giới hạn này khi thu thập dữ liệu cho đồ án.
`max_pages=all` vẫn dừng khi listing hết dữ liệu hoặc lặp lại, đồng thời có giới
hạn an toàn 100 trang listing để tránh vòng lặp ngoài ý muốn.

## Tiền xử lý và xây dựng inverted index

Sau khi có file raw JSONL, chạy:

```bash
python -m src.indexing.build
```

Kết quả được sinh tại `data/processed/recipes.jsonl`, `artifacts/inverted_index.json.gz` và `artifacts/index_report.json`. Đây là artifact có thể tái tạo nên không được commit lên Git.

## Phạm vi corpus và kiểm tra độ phủ

Đây là vertical search engine: hệ thống chỉ tìm trong các công thức đã crawl và
index, không tìm trên toàn Internet và không tự sinh công thức mới. Phạm vi hiện
tại là các trang công thức công khai từ Món Ngon Mỗi Ngày; số lượng và nhóm món
thực tế phải được đọc từ artifact thay vì tuyên bố bao phủ mọi món ăn.

Sau khi build, tạo báo cáo phạm vi và thử các truy vấn đại diện:

```bash
python -m src.evaluation.coverage
python -m src.evaluation.coverage --query "phở" --query "pizza" --query "sushi"
```

Báo cáo được lưu ở `artifacts/corpus_coverage.json`, gồm phân bố nguồn/danh
mục/cách nấu/độ khó, độ đầy đủ của từng trường và kết quả top đầu cho mỗi query
probe. Chi tiết nằm trong `docs/corpus_coverage.md`.

## Tìm kiếm nâng cao

Chạy chế độ tương tác:

```bash
python -m src.query.search
```

Hoặc tìm một lần với truy vấn có dấu/không dấu:

```bash
python -m src.query.search "gà nướng"
python -m src.query.search "ga nuong" --top-k 5
```

BM25F là ranker mặc định. Có thể lọc hoặc quay lại TF-IDF baseline:

```bash
python -m src.query.search "gà" --max-time 15 --difficulty "Dễ"
python -m src.query.search "nướng" --category "Món chay" --ingredient "đậu hũ"
python -m src.query.search "gà nướng" --ranker tfidf
```

## Đánh giá TF-IDF và BM25F

Đầu tiên gán nhãn relevance cho pool kết quả của 20 query:

```bash
python -m src.evaluation.judge
```

Sau khi mở rộng corpus, chạy lại đúng lệnh trên **không kèm `--rejudge`**. Công
cụ giữ nguyên các nhãn cũ có cùng document ID và chỉ hỏi những ứng viên mới xuất
hiện trong pool. Sau khi hoàn tất mới chạy lại evaluation.

Sau khi mỗi query có ít nhất một tài liệu relevant, chạy:

```bash
python -m src.evaluation.run
```

Nếu hai ranker không trả ứng viên cho một khoảng trống từ vựng đã biết như
`hải sản`, công cụ judge dùng các từ hải sản cụ thể để tạo pool chấm thủ công.
Phép evaluation vẫn chạy nguyên truy vấn, nên kết quả không bị làm đẹp giả.

Kết quả được ghi vào `artifacts/evaluation_report.json` và `artifacts/evaluation_results.csv`. Chi tiết quy trình nằm trong `docs/evaluation.md`.

## Chất lượng dữ liệu và mở rộng truy vấn

Chạy lại build để áp dụng cleanup trên dữ liệu raw mà không cần crawl lại:

```bash
python -m src.indexing.build
python -m src.query.search "hải sản"
python -m src.evaluation.run
```

Các bộ đếm cleanup nằm trong `artifacts/index_report.json`. TF-IDF vẫn là
baseline literal; BM25F dùng query expansion có trọng số và công khai các từ mở
rộng trong kết quả. Chi tiết nằm trong `docs/data_quality.md`.

## Search API

Khởi động backend sau khi đã build index:

```bash
python -m src.api
```

Kiểm tra tại `http://127.0.0.1:5000/api/v1/health` và tìm kiếm tại
`/api/v1/search?q=gà+nướng`. API hỗ trợ BM25F/TF-IDF, phân trang, bộ lọc,
facets, snippet, highlight offsets và score explanation. Chi tiết nằm trong
`docs/api.md`; đặc tả OpenAPI nằm tại `docs/openapi.yaml`.

## Giao diện web

Sau khi khởi động server, mở `http://127.0.0.1:5000/`. Trang chủ cung cấp ô tìm
kiếm và các truy vấn gợi ý. Trang kết quả tại `/search?q=gà+nướng` gọi API v1 để
hiển thị result card, highlight, bộ lọc, chuyển ranker và phân trang. Toàn bộ dữ
liệu động được đưa vào DOM bằng text node; frontend không chèn HTML lấy từ dữ
liệu crawler.

## Các mốc tiếp theo

1. Đóng gói production bằng Gunicorn và triển khai dịch vụ web.
2. Thêm spell correction, autocomplete và query suggestions.
3. Cân nhắc nguồn công thức thứ hai hoặc semantic retrieval nếu thời gian cho phép.
