# Review cấu trúc bộ nhớ và Đề xuất phương án cải thiện

## Đoạn code ban đầu
```python
tag_log = []

def log(tag_id, cnt, timestamp):
    tag_log.append((tag_id, cnt, timestamp))
```

## Vấn đề 
### 1. Vấn đề về hiệu năng và dữ liệu lớn:
- *tag_log* là một list lưu tất cả bản ghi.
- Nếu hệ thống chạy lâu dài, list có thể chứa hàng triệu phần tử → việc lưu trữ toàn bộ dữ liệu trong bộ nhớ có thể gây ra tiêu tốn bộ nhớ và có thể dẫn đến chậm chương trình. Hơn nữa, nếu chương trình chạy lâu dài, danh sách này sẽ tiếp tục tăng và không bao giờ được giải phóng.


### 2. Vấn đề về đồng bộ hóa:
- Biến *tag_log* là global và được chia sẻ giữa các luồng
- Phương thức *append()* không thread-safe trong môi trường đa luồng
- Có thể xảy race condition dẫn đến mất mát dữ liệu hoặc hỏng cấu trúc list

## Cải thiện
- Theo em nghĩ có thể ghi dữ liệu logging ra file và không trực tiếp append từng dữ liệu log. 

### Code cải thiện
```python
import logging
from datetime import datetime
from collections import deque
import threading

class TagLogger:
    def __init__(self, max_size=10000, enable_file_logging=True):
        self.max_size = max_size
        self.tag_log = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.enable_file_logging = enable_file_logging
        
        if enable_file_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(message)s',
                handlers=[
                    logging.FileHandler('tag_changes.log'),
                    logging.StreamHandler()
                ]
            )
    
    def log(self, tag_id, cnt, timestamp):
        with self.lock:
            self.tag_log.append({
                'tag_id': tag_id,
                'cnt': cnt, 
                'timestamp': timestamp,
                'logged_at': datetime.now().isoformat()
            })
        
        if self.enable_file_logging:
            logging.info(f"Tag {tag_id} CNT: {cnt} at {timestamp}")
    
    def get_recent_logs(self, count=100):
        with self.lock:
            return list(self.tag_log)[-count:]

tag_logger = TagLogger(max_size=5000)

def log(tag_id, cnt, timestamp):
    tag_logger.log(tag_id, cnt, timestamp)
```
