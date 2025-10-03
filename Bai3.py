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