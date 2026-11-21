# 🎬 Video VIP Pro: skill edit video cho Claude Code

Đưa video thô vào và gọi skill. Claude tự nghe lời, bỏ câu hỏng, cắt câu khớp khẩu hình, zoom theo nhịp, gắn chữ 2 tầng và khoảng 100 hiệu ứng VIP, có tiếng hiệu ứng đi kèm, rồi xuất MP4. Muốn sửa chỗ nào thì gõ thêm một câu lệnh, hoặc mở **VIP Editor** để kéo thả tay mà không tốn token.

- **Mọi ngành:** bán hàng, điện thoại, bất động sản, spa/làm đẹp, ăn uống, giáo dục/khoá học, tài chính, gym, du lịch, ô tô, thời trang, tin tức, vlog.
- **Màu chủ đạo theo ý bạn:** có sẵn 12 bộ màu (xanh, cam, đỏ, vàng kim, đen vàng, xanh lá, hồng, tím, ngọc, da trời, nâu, đen), hoặc bất kỳ mã màu nào. Cả video đổi màu theo, kể cả hiệu ứng chuyển động.
- **Chạy trên máy bạn:** không trả phí theo phút. Có card NVIDIA thì chạy nhanh hơn, không có vẫn chạy được.

## Hiệu ứng có sẵn

**Máy quay:**
- zoom thở;
- zoom giật theo câu;
- phóng gấp đôi rồi kéo ra, có nhoè chuyển động;
- mở đầu khung sát rồi bật ra;
- rung;
- speed ramp nhanh – chậm – nhanh cho B-roll (có nhoè chuyển động);
- whip pan (lia nhoè sang cảnh mới);
- cuối video nối vào đầu để lặp mượt;
- dolly zoom (phòng lao tới, người đứng yên);
- chuyển cảnh glitch, loé sáng phim, zoom xuyên cảnh.

**Tách người khỏi nền:**
- chữ khổng lồ nấp sau đầu;
- mờ phông;
- tách lớp (phòng thu nhỏ lại, người vẫn to);
- thay nền bằng video khác;
- người tràn khung bo góc;
- kính lúp;
- vòng chữ quay quanh người;
- dừng hình giới thiệu nhân vật (viền trắng kiểu sticker + thẻ tên);
- đèn sân khấu (phòng tối, người sáng);
- viền neon quanh người;
- nhân bản người;
- khung tròn mặt khi chiếu B-roll;
- khung truyện tranh (impact frame), zoom kịch tính kiểu meme.

**Chữ:**
- phụ đề 2 tầng hiện mờ dần;
- từ khoá theo màu thương hiệu;
- chữ có chân kiểu sang;
- đóng dấu;
- chữ rơi;
- bảng lật sân bay;
- bút dạ quang;
- khoanh tròn;
- đếm số chạy;
- gạch giá cũ, bật giá mới;
- hoá đơn in ra từng dòng;
- bản đồ bay tới địa điểm + ghim rơi;
- chữ giải mã, đồng hồ đếm ngược, sóng âm theo giọng;
- bảng điều tra dây đỏ, ảnh đen trắng tô màu dần, ảnh tĩnh 3D.

**Chữ VIP (26 kiểu):**
- chữ 3D đứng trong phòng (người đi qua che chữ), chữ luồn quanh người, chữ chiếu lên tường, chữ kính mờ;
- chữ vàng / bạc / chrome có vệt sáng, chữ neon bật sáng, chữ viết tay hiện theo nét;
- chữ cắt lát, chữ đậm dần, chữ tan thành bụi, từ khoá phóng to cả màn hình, khối 3D lật, tiêu đề tia sáng, chữ loang mực;
- số lăn kiểu đồng hồ cơ, con dấu tròn xoay, thẻ giá bám theo máy / tay;
- chữ trồi từ sau mặt bàn, chữ phản chiếu trên bàn, chữ chuyển nét kiểu cine;
- dòng địa điểm phim tài liệu, trích dẫn kiểu bài báo, chữ cắt dán từ báo, khung AI trả lời từng chữ, chữ nhún theo nhịp nhạc.

**Studio Look (phòng thường thành phòng quay xịn):**
- tự đồng bộ màu và độ sáng giữa các đoạn;
- đánh đèn giả: 4 kiểu sáng sang, ấm cà phê, cine tối, ánh cửa sổ;
- thêm cây xanh, đèn cây, kệ sách, bình hoa nằm sau lưng người nói.

**Giao diện:**
- cuộc gọi đến;
- con trỏ bấm;
- nút kính;
- thanh gõ lệnh;
- thông báo dồn;
- chat;
- bình luận rơi;
- biểu đồ;
- timeline;
- so sánh trước và sau.

**Chuyển cảnh:**
- mực loang;
- xé giấy;
- thổi bay;
- thẻ tiêu đề;
- cổng không gian;
- sóng xung kích;
- kính vỡ.

**Ảnh tĩnh tự cắt từ video:**
- polaroid;
- tường video;
- trang nhất báo;
- xấp thẻ.

**Màu khung hình:**
- phim nhựa;
- VHS;
- đen trắng;
- ấm;
- lạnh;
- cảnh kính mờ;
- cảnh navy kẻ ô;
- chuyển nét.

## Cài đặt (Windows)

**Bước 1: cài 4 thứ** (bỏ qua thứ nào máy đã có):
- [Claude Code](https://claude.com/claude-code)
- Python 3.10+
- Node.js 18+
- FFmpeg bản đầy đủ

Có thể cài nhanh Python, Node.js và FFmpeg bằng PowerShell:

```powershell
winget install Python.Python.3.12 OpenJS.NodeJS.LTS Gyan.FFmpeg
```

**Bước 2: tải skill về và chạy file cài.** Mở lại PowerShell rồi chạy:

```powershell
git clone https://github.com/leminhhieu0707/video-vip-pro "$env:USERPROFILE\.claude\skills\video-vip-pro"
```

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\video-vip-pro\setup.ps1"
```

File cài tự làm 4 việc:
- cài thư viện Python;
- cài bộ hiệu ứng chuyển động;
- cài font Be Vietnam Pro và Playfair Display;
- tạo kho âm thanh hiệu ứng.

Mất khoảng 5–10 phút.

Trên macOS / Linux thì chạy `bash setup.sh`.

## Cách dùng

Mở Claude Code ở bất kỳ thư mục nào rồi gõ:

> dùng skill video-vip-pro edit video `D:\Quay\video1.mp4`, ngành spa, màu hồng

Không ghi ngành hay màu thì Claude tự đoán từ nội dung và logo. Kết quả nằm trong thư mục `edited\` cạnh video gốc.

**Sửa tiếp bằng câu lệnh**, ví dụ:
- "đổi sang màu vàng kim"
- "câu thứ 3 thêm hiệu ứng đóng dấu GIÁ SỐC"
- "bỏ hiệu ứng VHS"
- "chữ to hơn, đặt thấp xuống"
- "zoom ít lại"
- "nói nhanh hơn chút"
- "thêm nút theo dõi cuối video tên trang ABC"

**Sửa tay bằng VIP Editor:** xong mỗi video, Claude mở trình sửa tay trên trình duyệt. Ở đó bạn có thể:
- kéo chữ;
- đổi giờ xuất hiện;
- sửa phụ đề;
- đổi bộ màu bằng một cú bấm;
- xuất lại video.

Sửa tay không tốn token.

## Lưu ý bản quyền

- **Code của skill:** giấy phép MIT, dùng thoải mái kể cả thương mại.
- **Remotion** (bộ vẽ hiệu ứng chuyển động):
  - miễn phí cho cá nhân và công ty có tối đa 3 người;
  - công ty lớn hơn phải mua giấy phép tại [remotion.pro](https://www.remotion.pro/license).
- **Âm thanh hiệu ứng:** do code tự tạo, không dính bản quyền.
- **Nhạc nền:** dùng nhạc của bạn hoặc nhạc miễn phí bản quyền. Đừng dùng nhạc có bản quyền.
- **Font:** Be Vietnam Pro và Playfair Display dùng giấy phép SIL OFL.

Chi tiết xem [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Cấu trúc thư mục

| thư mục | nội dung |
|---|---|
| `SKILL.md` | hướng dẫn cho Claude: quy trình dựng một lần, sửa bằng lệnh |
| `scripts/` | nghe lời (Whisper), cắt câu khớp khẩu hình (`aroll.py`), dựng (`render.py`), tách người (`vipfx.py`), màu (`theme.py`) |
| `motion/` | bộ hiệu ứng chuyển động (Remotion, React) |
| `editor/` | VIP Editor, trình sửa tay |
| `references/` | kiểu dựng, danh sách hiệu ứng, công thức từng ngành |
| `templates/build_vip.py` | khung kịch bản dựng |
